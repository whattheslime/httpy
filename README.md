# HTTPy

Simple HTTP server to list and manipulate files.

The objective of this project is to replace the [http.server](https://docs.python.org/3/library/http.server.html) python module with a server offering more features:
- Basic Authentication
- Directory listing
- File upload and download
- Files and directories creation
- Files and directories deletion
- SSL encryption (HTTPS)

![alt text](images/cmd.png)

![alt text](images/srv.png)

## Install

Clone the repository, go inside and then:
```bash
git clone https://github.com/WhatTheSlime/httpy.git
cd httpy
python3 -m pip install .
```

## Usage

```bash
 $ httpy -h
usage: httpy [-h] [-d DIRECTORY] [-e] [--debug] [-b ADDR] [-p PORT] [-a LOGIN PASSWORD] [-s] [-c CERT] [-k KEY]

Simple HTTP server to list and manipulate files

options:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
                        specify alternate working directory [default: current directory]
  -e, --edit            enable creation, deletion and upload of files and directories
  --debug               enable flask debug mode

network:
  -b ADDR, --bind ADDR  specify alternate bind address [default: all interfaces]
  -p PORT, --port PORT  specify alternate port [default: 8000]

security:
  -a LOGIN PASSWORD, --auth LOGIN PASSWORD
                        setup a basic authentication
  -s, --ssl             enable SSL encryption
  -c CERT, --cert CERT, --ssl-cert CERT
                        specify SSL server certificate
  -k KEY, --key KEY, --ssl-key KEY
                        specify SSL server secret key path
```

## Use features with curl

*Need `--edit` flag set on the server.* 

### Create a file
```bash
curl -ski http://127.0.0.1:8000/?action=create -d name=$filename&content=$filecontent
```

### Create a directory
```bash
curl -ski http://127.0.0.1:8000/?action=mkdir -d name=$dirname
```

### Upload a file
```bash
curl -ski http://127.0.0.1:8000/?action=upload -F file=@$filepath
```

### Delete files
```bash
curl -ski http://127.0.0.1:8000/?action=delete -d file1=$filename1&file2=$filename2&file3=$filename3
```

## Generate SSL certificates

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
httpy --ssl --cert cert.pem --key key.pem 
```
