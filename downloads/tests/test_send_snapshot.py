from pathlib import Path
import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_send_snapshot_invalid_key_serves_missing_snapshot_placeholder(client):
    """When a key is invalid/missing, send_snapshot falls back to serving snapshot-missing.gif."""
    fake_key = "9" * 40
    response = client.get(f"/download/files/snapshot/{fake_key}/sample_snapshot")
    assert response.status_code == 200


@pytest.mark.django_db
def test_send_snapshot_probing_suffixes(client, sample_secure_path):
    """Probes suffixes .webp, .png, and .gif sequentially and serves the matching file."""
    sp = sample_secure_path("snapshot_dataset")
    dataset_dir = Path(sp.path)

    # Create a .png snapshot file
    png_file = dataset_dir / "preview.png"
    png_file.write_text("png snapshot content")

    # Request without suffix
    response = client.get(f"/download/files/snapshot/{sp.key}/preview")
    assert response.status_code == 200


@pytest.mark.django_db
def test_send_snapshot_missing_snapshot_fallback(client, sample_secure_path):
    """When no matching snapshot (.webp, .png, .gif) exists, falls back to serving snapshot-missing.gif placeholder."""
    sp = sample_secure_path("empty_snapshot_dataset")
    response = client.get(f"/download/files/snapshot/{sp.key}/missing_preview")
    assert response.status_code == 200
