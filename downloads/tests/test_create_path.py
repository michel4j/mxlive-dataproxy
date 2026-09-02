import os
import pytest
from django.test import Client
from downloads.models import SecurePath


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_create_path_valid_absolute_path(client, setup_test_environment):
    """POSTing a valid absolute path inside DOWNLOAD_DIRS creates a SecurePath and returns a 40-char key."""
    valid_dir = str(setup_test_environment["download_dir"] / "valid_dataset")
    os.makedirs(valid_dir, exist_ok=True)

    response = client.post("/download/data/create/", {"path": valid_dir})
    assert response.status_code == 200

    data = response.json()
    assert "key" in data
    key = data["key"]
    assert key is not None
    assert len(key) == 40
    assert SecurePath.objects.filter(key=key, path=valid_dir).exists()


@pytest.mark.django_db
def test_create_path_relative_path_prepending(client, setup_test_environment):
    """POSTing a relative path prepends LDAP_USER_ROOT (/users) before validation."""
    rel_path = "user_dir/dataset"
    expected_full_path = str(setup_test_environment["user_root"] / rel_path)

    response = client.post("/download/data/create/", {"path": rel_path})
    assert response.status_code == 200

    data = response.json()
    key = data["key"]
    assert key is not None
    assert len(key) == 40
    assert SecurePath.objects.filter(key=key, path=expected_full_path).exists()


@pytest.mark.django_db
def test_create_path_unauthorized_path_rejected(client):
    """POSTing a path outside DOWNLOAD_DIRS rejects key creation and returns {'key': None}."""
    unauthorized_dir = "/forbidden/private_data"

    response = client.post("/download/data/create/", {"path": unauthorized_dir})
    assert response.status_code == 200

    data = response.json()
    assert data == {"key": None}
    assert not SecurePath.objects.filter(path=unauthorized_dir).exists()
