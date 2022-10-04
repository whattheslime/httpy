#!/usr/bin/env python3
import os
import secrets
import string

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from time import ctime
from uuid import uuid4

from flask import (
    abort, Flask, flash, redirect, request,	render_template, 
    send_from_directory)
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename


app = Flask(__name__.split(".")[0], static_folder=None)
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    return not app.config["BASIC_AUTH"] or (
        username == app.config["BASIC_AUTH"][0] and 
        sha256(password.encode()).hexdigest() == app.config["BASIC_AUTH"][1])


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
    - create: create a file
    - mkdir: create a directory
    - upload: upload a file
     - delete: delete a files or a drectories
    """
    actions = ["mkdir", "create", "delete", "upload"]
    
    if request.method == "GET":
        # joining the base and the requested path
        abs_path = Path(os.path.join(app.config["DIRECTORY"], req_path))

        # return 404 if path doesn't exist
        if not abs_path.exists():
            return abort(404)
        # check if path is a file and serve
        if abs_path.is_file():
            return send_from_directory(app.config["DIRECTORY"], req_path)
        # show directory contents
        files = []
        for file_path in sorted(abs_path.iterdir()):
            str_path = file_path.name
            file_stats = file_path.stat()
            if file_path.is_dir():
                str_path += "/"
            files.append(
                (str_path, ctime(file_stats.st_mtime), file_stats.st_size))
        return render_template(
            "index.html", edit=app.config["EDIT"], files=files, uuid=uuid4())

    if request.method == "POST":
        # get the action
        action = request.args.get("action")
        # check if action is valid
        if action not in actions:
            flash("Invalid action")
            return redirect(request.url)
        # execute action
        if action in actions:
            func = globals()[action]
            return func(req_path, request)


def make_file_path(path, file_name):
    """Action that create and return secure Path object from requested one
    """
    secure_file_name = secure_filename(file_name)
    return Path(
        os.path.join(app.config["DIRECTORY"], path, secure_file_name))


def create(path, request):
    """Action that create file
    """
    if app.config["EDIT"]:
        if "name" not in request.form:
            flash("No file name provided")
        elif "content" not in request.form:
            flash("No content provided")
        else:
            file_path = make_file_path(path, request.form["name"])
            if not os.path.exists(file_path):
                with open(file_path, "w") as file:
                    file.write(request.form["content"])
                flash(f"File {request.form['name']} created", "green")	
            else:
                flash(f"File {request.form['name']} already exists", "yellow")
            
        return redirect(request.url)


def mkdir(path, request):
    """Action that create directory 
    """
    if app.config["EDIT"]:
        if "name" not in request.form:
            flash("No directory name provided", "red")
        else:
            dir_path = make_file_path(path, request.form["name"])
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)
                flash(f"Dirctory {path} created", "green")	
            else:
                flash(f"Directory {path} already exists", "yellow")
        return redirect(request.url)


def delete(path, request):
    """Action that delete file or directory if exists
    """
    if app.config["EDIT"]:
        files = list(request.form.values())
        if not files:
            flash("No files selected", "red")
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
            flash("Files deleted", "green")
        return redirect(request.url)


def upload(path, request):
    """Action that upload file
    """
    if app.config["EDIT"]:
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part provided", "red")
            return redirect(request.url)
        file = request.files["file"]
        # if the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            flash("No file selected", "red")
            return redirect(request.url)
        
        if file:
            file_path = make_file_path(path, file.filename)
            if file_path.exists():
                flash(f"File {file.filename} will be erased", "yellow")
            file.save(file_path)
            flash(f"File {file.filename} uploaded", "green")
            return redirect(request.url)


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
    app.run(
        host=args.bind, port=args.port, debug=args.debug,
        ssl_context=ssl_context)

