from pathlib import Path
import pytest
from django.test import Client
import downloads.utils as utils


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_send_frame_cache_hit(client, sample_secure_path, setup_test_environment):
    """When the rendered PNG frame already exists in CACHE_DIR, it is served directly without re-rendering."""
    sp = sample_secure_path("cached_frame_dataset")
    cache_dir = setup_test_environment["cache_dir"]
    cached_png = cache_dir / sp.key / "image01" / "nm.png"
    cached_png.parent.mkdir(parents=True, exist_ok=True)
    cached_png.write_text("cached image binary")

    response = client.get(f"/download/files/frame/{sp.key}/image01.cbf/nm.png")
    assert response.status_code == 200


@pytest.mark.django_db
def test_send_frame_invalid_key_returns_missing_frame_placeholder(client):
    """When an invalid/non-existent key is supplied, SendFrame serves the missing frame placeholder."""
    fake_key = "f" * 40
    response = client.get(f"/download/files/frame/{fake_key}/image01.cbf/nm.png")
    assert response.status_code == 200


@pytest.mark.django_db
def test_send_frame_cache_miss_renders_png(client, sample_secure_path, setup_test_environment, monkeypatch):
    """When valid key and frame file exist but image is not cached, create_png is called and generated file is served."""
    sp = sample_secure_path("frame_dataset")
    frame_file = Path(sp.path) / "frame_001.cbf"
    frame_file.write_text("dummy frame data")

    created_calls = []

    def mock_create_png(filename, output, brightness, resolution=(1024, 1024)):
        created_calls.append((filename, output, brightness))
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("rendered png data")

    monkeypatch.setattr(utils, "create_png", mock_create_png)

    # Test with brightness code 'xl' (0.25)
    response = client.get(f"/download/files/frame/{sp.key}/frame_001.cbf/xl.png")
    assert response.status_code == 200
    assert len(created_calls) == 1
    assert created_calls[0][2] == 0.25


@pytest.mark.django_db
def test_send_frame_missing_source_returns_missing_placeholder(client, sample_secure_path):
    """When key is valid but source frame file does not exist, missing frame placeholder is served."""
    sp = sample_secure_path("empty_dataset")
    response = client.get(f"/download/files/frame/{sp.key}/non_existent.cbf/nm.png")
    assert response.status_code == 200
