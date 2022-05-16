HTTPy
=====

Simple HTTP server to list and manipulate files.

The objective of this project is to replace the SimpleHTTPServer with a server offering more features:
- SSL encryption (HTTPS)
- Basic Authentication
- Directory listing
- File upload and download
- Files and directories creation
- Files and directories deletion

![alt text](images/cmd.png)

![alt text](images/srv.png)

Installation
------------

Clone the repository, go inside and then:
```bash
$ python3 -m pip install .
```

Run the server
----------------

```bash
 $ httpy -h
usage: httpy [-h] [-a LOGIN PASSWORD] [-b BIND] [-d DIRECTORY] [-p PORT] [--ssl] [--cert CERT]
             [--key KEY] [--debug]

Simple HTTP server to list and manipulate files

options:
  -h, --help            show this help message and exit
  -a LOGIN PASSWORD, --auth LOGIN PASSWORD
                        setup a basic authentication
  -b BIND, --bind BIND  specify alternate bind address [default: all interfaces]
  -d DIRECTORY, --directory DIRECTORY
                        specify alternate working directory [default: current directory]
  -p PORT, --port PORT  specify alternate port [default: 8000]
  --ssl                 enable SSL encryption
  --cert CERT, --ssl-cert CERT
                        specifySSL server certificate
  --key KEY, --ssl-key KEY
                        specifySSL server secret key path
  --debug               enable flask debug mode
```

Generate SSL certificates
-------------------------

```bash
$ openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
$ httpy --ssl --cert cert.pem --key key.pem 
```
