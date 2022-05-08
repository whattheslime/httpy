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
	"""Directory listing page serve by the flask server
	
	By accessing with a GET request, it return a directory listing from the 
	current directory.
	
	By accessing with a POST request, it execute an action according to
	the "action" get parameter.
	
	Allowed actions are:
	- create a file
	- create a directory
	- upload a file
 	- delete a files or a drectories
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
		return render_template("index.html", files=files, uuid=uuid4())

	if request.method == "POST":
		action = request.args.get("action")
		if action not in actions:
			flash("Invalid action")
			return redirect(request.url)
		
		if action in actions:
			func = globals()[action]
			return func(req_path, request)


def make_file_path(path, file_name):
	"""Create and return secure Path object from requested one
	"""
	secure_file_name = secure_filename(file_name)
	return Path(
		os.path.join(app.config["DIRECTORY"], path, secure_file_name))


def create(path, request):
	"""Create file
	"""
	if "name" not in request.form:
		flash("No file name provided")
	elif "content" not in request.form:
		flash("No content provided")
	else:
		file_path = make_file_path(path, request.form["name"])
		if not os.path.exists(file_path):
			with open(file_path, "w") as file:
				file.write(request.form["content"])
			flash(f"File {request.form['name']} created", "success")	
		else:
			flash(f"File {request.form['name']} already exists", "warning")
		
	return redirect(request.url)


def mkdir(path, request):
	"""Create directory 
	"""
	if "name" not in request.form:
		flash("No directory name provided", "danger")
	else:
		dir_path = make_file_path(path, request.form["name"])
		if not os.path.exists(dir_path):
			os.mkdir(dir_path)
			flash(f"Dirctory {path} created", "success")	
		else:
			flash(f"Directory {path} already exists", "warning")
	return redirect(request.url)


def delete(path, request):
	"""Delete file or folder if exists 
	"""
	files = list(request.form.values())
	if not files:
		flash("No files selected", "danger")
	for file_name in files:
		file_path = make_file_path(path, file_name)
		if file_path.exists():
			if file_path.is_file():
				file_path.unlink()
			if file_path.is_dir():
				rmtree(file_path)
		else:
			flash(f"File {file_name} does not exists", "warning")
	if files:
		flash("Files deleted", "success")
	return redirect(request.url)


def upload(path, request):
	"""Upload file directory 
	"""
	# check if the post request has the file part
	if "file" not in request.files:
		flash("No file part provided", "danger")
		return redirect(request.url)
	file = request.files["file"]
	# If the user does not select a file, the browser submits an
	# empty file without a filename.
	if file.filename == "":
		flash("No file selected", "danger")
		return redirect(request.url)
	
	if file:
		file_path = make_file_path(path, file.filename)
		if file_path.exists():
			flash(f"File {file.filename} will be erased", "warning")
		file.save(file_path)
		flash(f"File {file.filename} uploaded", "success")
		return redirect(request.url)


def get_args():
	"""Parse user arguments
	"""
	parser = ArgumentParser(
		description="Simple HTTP server to list and manipulate files")
	parser.add_argument(
		"-a", "--auth", type=str, nargs=2, metavar=("LOGIN", "PASSWORD"),
		help="setup a basic authentication")
	parser.add_argument(
		"-b", "--bind", type=str, default="0.0.0.0",
		help="specify alternate bind address [default: all interfaces]")
	parser.add_argument(
		"-d", "--directory", type=Path, default=Path(os.path.curdir).absolute(),
		help="specify alternate working directory [default: current directory]")
	parser.add_argument(
		"--debug", action="store_true", help="enable flask debug mode")
	parser.add_argument(
		"-p", "--port", type=int, default=8000,
		help="specify alternate port [default: 8000]")
	parser.add_argument(
		"--ssl", action="store_true", help="enable SSL encryption")
	parser.add_argument(
		"--ssl-cert", type=Path, default=None, help="SSL server certificate")
	parser.add_argument(
		"--ssl-key", type=Path, default=None, help="SSL server secret key path")
	return parser


def run():
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

	# setup SSL configuration
	ssl_context = None
	if args.ssl:
		# need both or no of the two arguments
		if bool(args.ssl_cert) ^ bool(args.ssl_key):
			parser.error(
				"You need to define both of --ssl-cert and --ssl-key")
		# generate self-signed certificate
		if not (args.ssl_cert or args.ssl_key):
			ssl_context = "adhoc"
		# load SSL certificate and key from user arguments
		else:
			ssl_context = (args.ssl_cert, args.ssl_key)

	# run the server
	app.run(
		host=args.bind, port=args.port, debug=args.debug,
		ssl_context=ssl_context)
