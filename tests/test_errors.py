import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
from httpy.server import app

@pytest.fixture
def client():
    temp_dir = tempfile.mkdtemp()
    app.config["DIRECTORY"] = Path(temp_dir).resolve()
    app.config["BASIC_AUTH"] = None
    app.config["EDIT"] = True
    app.config["TESTING"] = True
    app.secret_key = "test_secret"
    
    with app.test_client() as client:
        yield client
        
    shutil.rmtree(temp_dir)

def test_permission_denied(client):
    """Test handling of PermissionError."""
    # Mock 'open' to raise PermissionError
    with patch("httpy.server.open", side_effect=PermissionError):
        response = client.post("/?action=create", data={"name": "test.txt", "content": "test"})
        assert response.status_code == 302
        with client.session_transaction() as sess:
            # Check flash messages - in flask it's usually in '_flashes'
            # But the better way is to follow the redirect and check rendered data
            pass
        
    # Follow redirect
    response = client.get("/", follow_redirects=True)
    assert b"Permission denied" in response.data

def test_disk_full(client):
    """Test handling of Disk full (ENOSPC)."""
    err = OSError()
    err.errno = 28 # ENOSPC
    with patch("httpy.server.open", side_effect=err):
        response = client.post("/?action=create", data={"name": "test.txt", "content": "test"}, follow_redirects=True)
        assert b"Disk is full" in response.data

def test_unexpected_error(client):
    """Test handling of unexpected exceptions."""
    with patch("httpy.server.open", side_effect=Exception("Boom")):
        response = client.post("/?action=create", data={"name": "test.txt", "content": "test"}, follow_redirects=True)
        assert b"Unexpected error: Boom" in response.data
