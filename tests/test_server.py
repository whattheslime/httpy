import os
import shutil
import tempfile
import pytest
from pathlib import Path
from httpy.server import app

@pytest.fixture
def client():
    # Setup temporary directory
    temp_dir = tempfile.mkdtemp()
    app.config["DIRECTORY"] = Path(temp_dir).resolve()
    app.config["BASIC_AUTH"] = None # Disable auth for tests
    app.config["EDIT"] = True
    app.config["TESTING"] = True
    app.secret_key = "test_secret"
    
    with app.test_client() as client:
        yield client
        
    # Cleanup
    shutil.rmtree(temp_dir)

def test_index_listing(client):
    """Test directory listing."""
    root = app.config["DIRECTORY"]
    (root / "file1.txt").touch()
    (root / "dir1").mkdir()
    
    response = client.get("/")
    assert response.status_code == 200
    assert b"file1.txt" in response.data
    assert b"dir1/" in response.data

def test_path_traversal_protection(client):
    """Test protection against path traversal."""
    # Attempt simple traversal in URL
    response = client.get("/../")
    assert response.status_code == 403
    
    # Attempt traversal to system files
    response = client.get("/../../etc/passwd")
    assert response.status_code == 403

def test_action_create_file(client):
    """Test file creation action."""
    response = client.post("/?action=create", data={"name": "newfile.txt", "content": "hello world"})
    assert response.status_code == 302 # Redirect after success
    
    file_path = app.config["DIRECTORY"] / "newfile.txt"
    assert file_path.exists()
    assert file_path.read_text() == "hello world"

def test_action_mkdir(client):
    """Test directory creation action."""
    response = client.post("/?action=mkdir", data={"name": "newdir"})
    assert response.status_code == 302
    
    dir_path = app.config["DIRECTORY"] / "newdir"
    assert dir_path.exists()
    assert dir_path.is_dir()

def test_action_upload(client):
    """Test file upload action."""
    from io import BytesIO
    data = {
        "file": (BytesIO(b"content"), "uploaded.txt")
    }
    response = client.post("/?action=upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 302
    
    file_path = app.config["DIRECTORY"] / "uploaded.txt"
    assert file_path.exists()
    assert file_path.read_text() == "content"

def test_action_delete(client):
    """Test file deletion action."""
    root = app.config["DIRECTORY"]
    (root / "to_delete.txt").touch()
    
    response = client.post("/?action=delete", data={"file0": "to_delete.txt"})
    assert response.status_code == 302 # Redirect after success
    assert not (root / "to_delete.txt").exists()

def test_human_readable_sizes_in_listing(client):
    """Test that sizes are displayed in human readable format."""
    root = app.config["DIRECTORY"]
    with open(root / "large.txt", "wb") as f:
        f.write(b"A" * 1500)
    
    response = client.get("/")
    assert b"1.46 KB" in response.data
