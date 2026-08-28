from pathlib import Path
import pytest
from django.test import Client
from downloads.models import SecurePath


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_send_file_invalid_key_returns_404(client):
    """Requesting a file with a non-existent key returns 404 Not Found."""
    fake_key = "a" * 40
    response = client.get(f"/download/files/raw/{fake_key}/sample.txt")
    assert response.status_code == 404


@pytest.mark.django_db
def test_send_file_non_existent_file_returns_404(client, sample_secure_path):
    """Valid key but non-existent file path returns 404 Not Found."""
    sp = sample_secure_path("valid_dataset")
    response = client.get(f"/download/files/raw/{sp.key}/non_existent_file.txt")
    assert response.status_code == 404


@pytest.mark.django_db
def test_send_file_frontend_header_modes(client, sample_secure_path, monkeypatch):
    """Verify frontend header generation for xsendfile, xaccelredirect, and static mode."""
    sp = sample_secure_path("dataset_headers")
    test_file = Path(sp.path) / "data.txt"
    test_file.write_text("sample content")

    import downloads.views as views

    # Mode 1: static mode (default frontend)
    monkeypatch.setattr(views, "FRONTEND", "static")
    response_static = client.get(f"/download/files/raw/{sp.key}/data.txt")
    assert response_static.status_code == 200

    # Mode 2: xsendfile
    monkeypatch.setattr(views, "FRONTEND", "xsendfile")
    response_xsendfile = client.get(f"/download/files/raw/{sp.key}/data.txt")
    assert response_xsendfile.status_code == 200
    assert response_xsendfile.get("X-Sendfile") == str(test_file)

    # Mode 3: xaccelredirect
    monkeypatch.setattr(views, "FRONTEND", "xaccelredirect")
    response_xaccel = client.get(f"/download/files/raw/{sp.key}/data.txt")
    assert response_xaccel.status_code == 200
    assert response_xaccel.get("X-Accel-Redirect") == str(test_file)


@pytest.mark.django_db
def test_send_file_substitute_dirs_resolution(client, setup_test_environment, monkeypatch):
    """Verify file resolution when primary path does not exist but substitute dir path exists."""
    dir_a = setup_test_environment["download_dir"] / "dir_a"
    dir_b = setup_test_environment["download_dir"] / "dir_b"
    dir_a.mkdir(parents=True, exist_ok=True)
    dir_b.mkdir(parents=True, exist_ok=True)

    sp = SecurePath(path=str(dir_a))
    sp.save()

    file_in_b = dir_b / "sub_file.txt"
    file_in_b.write_text("substitute file content")

    import downloads.views as views
    monkeypatch.setattr(views, "SUBSTITUTE_DIRS", [str(dir_a), str(dir_b)])

    response = client.get(f"/download/files/raw/{sp.key}/sub_file.txt")
    assert response.status_code == 200


@pytest.mark.django_db
def test_send_file_gzip_decompression_fallback(client, sample_secure_path, monkeypatch):
    """Verify that a missing uncompressed file falls back to gunzip on <file>.gz."""
    sp = sample_secure_path("gzip_dataset")
    gz_file = Path(sp.path) / "archive.data.gz"
    gz_file.write_bytes(b"dummy compressed content")

    import downloads.views as views

    called_cmds = []

    def mock_check_call(cmd):
        called_cmds.append(cmd)
        # Simulate gunzip creating the target output file
        target_file = Path(cmd[2])
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("decompressed content")
        return 0

    monkeypatch.setattr("subprocess.check_call", mock_check_call)

    response = client.get(f"/download/files/raw/{sp.key}/archive.data")
    assert response.status_code == 200
    assert len(called_cmds) == 1
