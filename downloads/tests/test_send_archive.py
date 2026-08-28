import io
from pathlib import Path
import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_send_archive_invalid_key_returns_404(client):
    """When a non-existent key is used, send_archive returns 404 Not Found."""
    fake_key = "0" * 40
    response = client.get(f"/download/files/archive/{fake_key}/backup.tar.gz")
    assert response.status_code == 404


@pytest.mark.django_db
def test_send_archive_missing_directory_returns_404(client, sample_secure_path):
    """When key exists but directory does not exist on disk, returns 404 Not Found."""
    sp = sample_secure_path("non_existent_folder")
    # Delete the directory created by the sample_secure_path helper
    import shutil
    shutil.rmtree(sp.path, ignore_errors=True)

    response = client.get(f"/download/files/archive/{sp.key}/backup.tar.gz")
    assert response.status_code == 404


@pytest.mark.django_db
def test_send_archive_streaming_response(client, sample_secure_path, monkeypatch):
    """When key and directory are valid, send_archive streams a tar.gz archive with Content-Disposition header."""
    sp = sample_secure_path("archive_folder")
    test_dir = Path(sp.path)
    (test_dir / "file1.txt").write_text("hello archive")

    called_popen = []

    class MockPopen:
        def __init__(self, cmd, cwd=None, stdout=None):
            called_popen.append((cmd, cwd))
            self.stdout = io.BytesIO(b"fake-gzip-archive-stream")

    monkeypatch.setattr("subprocess.Popen", MockPopen)

    response = client.get(f"/download/files/archive/{sp.key}/export.tar.gz")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/x-gzip"
    assert response["Content-Disposition"] == "attachment; filename=export.tar.gz"
    assert len(called_popen) == 1
    assert called_popen[0][0] == ["tar", "-czf", "-", test_dir.name]
    assert called_popen[0][1] == test_dir.parent
    assert b"".join(response.streaming_content) == b"fake-gzip-archive-stream"
