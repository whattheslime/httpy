#!/usr/bin/env python3
import os
import logging
import secrets
import string
import sys
import errno

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from shutil import rmtree, make_archive
from time import ctime
from tempfile import TemporaryDirectory
from uuid import uuid4

from flask import (
    abort, Flask, flash, redirect, request,	render_template, 
    send_from_directory, send_file)
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename


app = Flask(__name__.split(".")[0], static_folder=None)
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    return not app.config["BASIC_AUTH"] or (
        username == app.config["BASIC_AUTH"][0] and 
        sha256(password.encode()).hexdigest() == app.config["BASIC_AUTH"][1])


def safe_join(base_dir, *paths):
    """Safely join paths and ensure the result is within base_dir.
    
    Returns the resolved Path object or raises PermissionError if traversal is detected.
    """
    base_path = Path(base_dir).resolve()
    # Use joinpath and then resolve to get the absolute path
    resolved_path = base_path.joinpath(*paths).resolve()
    
    # Check if resolved_path starts with base_path
    if not str(resolved_path).startswith(str(base_path)):
        logging.warning(
            f"Path traversal attempt by {request.remote_addr}: "
            f"tried to access {resolved_path}")
        raise PermissionError("Path traversal detected")
    return resolved_path


def human_readable_size(size, decimal_places=2):
    """Convert bytes to human readable format.
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def handle_fs_errors(func):
    """Decorator to handle common filesystem errors and flash messages.
    """
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionError:
            logging.error(f"Permission denied for {func.__name__} by {request.remote_addr}")
            flash("Permission denied", "red")
        except FileNotFoundError:
            logging.error(f"File not found during {func.__name__} by {request.remote_addr}")
            flash("File or directory not found", "red")
        except IsADirectoryError:
            logging.error(f"Directory error for {func.__name__} by {request.remote_addr}")
            flash("Target is a directory, not a file", "red")
        except OSError as e:
            if e.errno == 28: # ENOSPC
                logging.error(f"Disk full error for {func.__name__} by {request.remote_addr}")
                flash("Disk is full", "red")
            else:
                logging.error(f"System error during {func.__name__}: {e.strerror}")
                flash(f"System error: {e.strerror}", "red")
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {str(e)}")
            flash(f"Unexpected error: {str(e)}", "red")
        return redirect(request.path)
    return wrapper


@app.route("/", methods=["GET", "POST"], defaults={"req_path": ""})
@app.route("/<path:req_path>", methods=["GET", "POST"])
@auth.login_required
def index(req_path):
    """Directory listing page served by the flask server.
    
    By accessing with a GET request, it return a directory listing from the 
    current directory.
    
    By accessing with a POST request, it execute an action according to
    the "action" get parameter.
    
    Allowed actions are:
    - archive: download an archive of current directory
    - create:  create a file
    - delete:  delete a files or a drectories
    - mkdir:   create a directory
    - upload:  upload a file
    """
    actions = ["mkdir", "create", "delete", "upload", "archive"]
    
    if request.method in ["GET", "HEAD"]:
        # Joining the base and the requested path safely.
        try:
            abs_path = safe_join(app.config["DIRECTORY"], req_path)
        except (PermissionError, ValueError):
            return abort(403)

        # Return 404 if path doesn't exist.
        if not abs_path.exists():
            return abort(404)
        # Check if path is a file and serve.
        if abs_path.is_file():
            return send_from_directory(app.config["DIRECTORY"], req_path)
        # Show directory contents.
        files = []
        for file_path in sorted(abs_path.iterdir()):
            str_path = file_path.name
            file_stats = file_path.stat()
            if file_path.is_dir():
                str_path += "/"
                size = "-"
            else:
                size = human_readable_size(file_stats.st_size)
            
            files.append(
                (str_path, ctime(file_stats.st_mtime), size))

        return render_template(
            "index.html", edit=app.config["EDIT"], files=files, uuid=uuid4())

    elif request.method == "POST":
        # Get the action.
        action = request.args.get("action")
        
        # Check if action is valid.
        if action not in actions:
            flash("Invalid action")
            return redirect(request.url)
        # Execute action.
        if action in actions:
            func = globals()[action]
            try:
                return func(req_path, request)
            except (PermissionError, ValueError):
                return abort(403)
    
    return abort(405)


def make_file_path(path, file_name):
    """Action that create and return secure Path object from requested one.
    """
    secure_file_name = secure_filename(file_name)
    return safe_join(app.config["DIRECTORY"], path, secure_file_name)


@handle_fs_errors
def create(path, request):
    """Action that create file.
    """
    if app.config["EDIT"]:
        if "name" not in request.form:
            flash("No file name provided", "red")
        elif "content" not in request.form:
            flash("No content provided", "red")
        else:
            file_path = make_file_path(path, request.form["name"])
            if not os.path.exists(file_path):
                with open(file_path, "w") as file:
                    file.write(request.form["content"])
                logging.info(f"File {request.form['name']} created by {request.remote_addr}")
                flash(f"File {request.form['name']} created", "green")	
            else:
                flash(f"File {request.form['name']} already exists", "yellow")
            
        return redirect(request.path)


@handle_fs_errors
def mkdir(path, request):
    """Action that create directory.
    """
    if app.config["EDIT"]:
        if "name" not in request.form:
            flash("No directory name provided", "red")
        else:
            dir_path = make_file_path(path, request.form["name"])
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)
                logging.info(f"Directory {request.form['name']} created by {request.remote_addr}")
                flash(f"Directory {request.form['name']} created", "green")	
            else:
                flash(f"Directory {request.form['name']} already exists", "yellow")
        return redirect(request.path)


@handle_fs_errors
def archive(path, request):
    """Action that create an archive of files and directories and download it.
    """
    with TemporaryDirectory() as tmpdir_name:
        archive_tmp = Path(tmpdir_name) / str(uuid4())
        current_dir = make_file_path(path, "")

        archive_path = Path(
            make_archive(archive_tmp, "zip", current_dir))

        if archive_path.exists():
            logging.info(f"Archive {archive_path.name} created for {request.remote_addr}")
            flash(f"Archive {archive_path.name} created", "green")
            file_sended = send_file(archive_path)
            archive_path.unlink()
            return file_sended
        else:
            flash("Archive not created", "red")
    return redirect(request.path)


@handle_fs_errors
def delete(path, request):
    """Action that delete file or directory if exists
    """
    files = list(request.form.values())
    if not files:
        flash("No files selected", "red")

    # Delete files.
    for file_name in files:
        file_path = make_file_path(path, file_name)
        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
            if file_path.is_dir():
                rmtree(file_path)
        else:
            flash(f"File {file_name} does not exists", "yellow")
    if files:
        logging.info(f"Files {files} deleted by {request.remote_addr}")
        flash("Files deleted", "green")
    return redirect(request.path)


@handle_fs_errors
def upload(path, request):
    """Action that upload file
    """
    if app.config["EDIT"]:
        # Check if the post request has the file part.
        if not request.files:
            flash("No file part provided", "red")
            return redirect(request.path)
        
        for file in request.files.getlist("file"):
            # if the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == "":
                flash("No file selected", "red")
                return redirect(request.path)
            
            if file:
                file_path = make_file_path(path, file.filename)
                if file_path.exists():
                    flash(f"File {file.filename} will be erased", "yellow")
                file.save(file_path)
                logging.info(f"File {file.filename} uploaded by {request.remote_addr}")
                flash(f"File {file.filename} uploaded", "green")
        return redirect(request.path)


def get_args():
    """Parse user arguments
    """
    parser = ArgumentParser(
        description="Simple HTTP server to list and manipulate files")
    parser.add_argument(
        "-d", "--directory", type=Path, default=Path(os.path.curdir).absolute(),
        help="specify alternate working directory [default: current directory]")
    parser.add_argument(
        "-e", "--edit", action="store_true",
        help="enable creation, deletion and upload of files and directories")
    parser.add_argument(
        "--dev", action="store_true",
        help="run the server using flask development server with debug mode")
    parser.add_argument(
        "--debug", action="store_true", help="enable flask debug mode")
    
    network_parser = parser.add_argument_group("network")
    
    network_parser.add_argument(
        "-b", "--bind", metavar="ADDR", type=str, default="0.0.0.0",
        help="specify alternate bind address [default: all interfaces]")
    network_parser.add_argument(
        "-p", "--port", type=int, default=8000,
        help="specify alternate port [default: 8000]")

    security_parser = parser.add_argument_group("security")
    
    security_parser.add_argument(
        "-a", "--auth", type=str, nargs=2, metavar=("LOGIN", "PASSWORD"),
        help="setup a basic authentication")
    security_parser.add_argument(
        "-s", "--ssl", action="store_true", help="enable SSL encryption")
    security_parser.add_argument(
        "-c", "--cert", "--ssl-cert", type=Path, default=None, 
        help="specify SSL server certificate")
    security_parser.add_argument(
        "-k", "--key", "--ssl-key", type=Path, default=None, 
        help="specify SSL server secret key path")
    
    return parser


def run():
    """Main function
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    # generate app secret
    app.secret_key = "".join(
        secrets.choice(string.printable) for _ in range(20))

    # parse user arguments
    parser = get_args()
    args = parser.parse_args()	

    # set basic authentication
    app.config["BASIC_AUTH"] = ""
    if args.auth:
        login, password = args.auth
        app.config["BASIC_AUTH"] = (
            login, sha256(password.encode()).hexdigest())

    # set working directory
    app.config["DIRECTORY"] = args.directory
    if not os.path.exists(args.directory):
        print(f" * WARNING: Directory '{args.directory}' does not exist.")
    
    # enable files edition
    app.config["EDIT"] = args.edit
    
    # setup SSL configuration
    ssl_context = None
    if args.ssl:
        # need both or no of the two arguments
        if bool(args.cert) ^ bool(args.key):
            parser.error(
                "You need to define both of --cert and --key")
        # generate self-signed certificate
        if not (args.cert or args.key):
            ssl_context = "adhoc"
        # load SSL certificate and key from user arguments
        else:
            ssl_context = (args.cert, args.key)

    # run the server
    try:
        if args.dev or args.ssl:
            if args.ssl and not args.dev:
                print(" * WARNING: Waitress does not support SSL. Falling back to Flask development server.")
            
            app.run(
                host=args.bind, port=args.port, debug=args.debug or args.dev,
                ssl_context=ssl_context)
        else:
            from waitress import serve
            print(f" * Serving httpy in production mode on http://{args.bind}:{args.port}")
            serve(app, host=args.bind, port=args.port, url_scheme="https" if args.ssl else "http")
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"Error: Port {args.port} is already in use on {args.bind}.")
            print("Please choose a different port with --port or stop the conflicting service.")
        elif e.errno == errno.EACCES:
            print(f"Error: Permission denied. You might need elevated privileges to bind to port {args.port}.")
        else:
            print(f"Error: Could not start server: {e.strerror}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: An unexpected error occurred during startup: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run()
