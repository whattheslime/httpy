# HTTPY 🚀

Simple yet powerful HTTP server to list and manipulate files, built with Flask and Waitress.

The objective of this project is to replace Python's default `http.server` with a more feature-rich, secure, and production-ready solution.

## ✨ Features

- **Production-Ready**: Uses [Waitress](https://docs.pylonsproject.org/projects/waitress/) as the default WSGI server for robustness.
- **Modern Directory Listing**: Enhanced UI with human-readable file sizes and intuitive navigation.
- **File Manipulation**: Creation, upload, download (including zipping), and deletion of files and directories (requires `--edit`).
- **Security First**: 
  - Robust **Path Traversal protection** using resolved path validation.
  - Basic Authentication support.
  - SSL encryption (HTTPS) ready.
- **Detailed Logging**: Every action (create, upload, delete, etc.) is logged with timestamp, level, and user IP.
- **Human-Readable Sizes**: File sizes automatically formatted (B, KB, MB, GB, TB).
- **Graceful Error Handling**: Descriptive error messages (e.g., "Disk Full", "Permission Denied") instead of generic 500 errors.
- **Developer Mode**: Easily switch to Flask's debug mode with the `--dev` flag.

---

## 📦 Install

Clone the repository and install the package:

```bash
git clone https://github.com/WhatTheSlime/httpy.git
cd httpy
python3 -m pip install .
```

---

## 🚀 Usage

### 1. Start the server

Basic usage (Read-only, production mode):
```bash
httpy
```

Enable editing and SSL (Self-signed certificate):
```bash
httpy --edit --ssl
```

Enable development mode (Flask debugger):
```bash
httpy --dev
```

### 2. Command Line Arguments

| Argument | Short | Description |
| :--- | :--- | :--- |
| `--directory` | `-d` | Target directory to serve (default: current) |
| `--edit` | `-e` | Enable file/directory manipulation |
| `--dev` | | Use Flask development server with debug mode |
| `--auth` | `-a` | Setup Basic Auth (`USER PASSWORD`) |
| `--bind` | `-b` | Bind address (default: `0.0.0.0`) |
| `--port` | `-p` | Port number (default: `8000`) |
| `--ssl` | `-s` | Enable SSL encryption |

---

## 🛠️ Advanced: Interacting with HTTPY

You can perform all actions using `curl` (Server must be started with `--edit`):

```bash
# Download a file
curl -O http://127.0.0.1:8000/README.md

# Upload files
curl -F "file=@/path/to/local_file.txt" "http://localhost:8000/?action=upload"

# Create a new file
curl -d "name=notes.txt&content=Hello+HTPPY" "http://localhost:8000/?action=create"

# Create a directory
curl -d "name=projects" "http://localhost:8000/?action=mkdir"

# Delete files
curl -d "file0=notes.txt" "http://localhost:8000/?action=delete"

# Download directory as ZIP
curl -o backup.zip "http://localhost:8000/?action=archive"
```

---

## 🧪 Testing

The project includes a comprehensive test suite using `pytest`.

```bash
# Run all tests
PYTHONPATH=src pytest tests/
```

---

## 🔒 Security & SSL

To use your own SSL certificates:
```bash
httpy --ssl --cert cert.pem --key key.pem
```

To generate a self-signed certificate for local testing:
```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

---

*Made with ❤️ for simple file sharing.*
