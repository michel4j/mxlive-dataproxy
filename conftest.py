import os
import shutil
import pytest
from django.conf import settings
from downloads.models import SecurePath


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch, settings):
    """
    Configure isolated test environments for directories, caching, and database.
    """
    # Create isolated temp directories for downloads, cache, and users
    test_download_dir = tmp_path / "downloads"
    test_download_dir.mkdir(parents=True, exist_ok=True)

    test_cache_dir = tmp_path / "cache"
    test_cache_dir.mkdir(parents=True, exist_ok=True)

    test_user_root = tmp_path / "users"
    test_user_root.mkdir(parents=True, exist_ok=True)

    # Patch settings
    settings.DOWNLOAD_DIRS = [str(test_download_dir), str(test_user_root)]
    settings.DOWNLOAD_CACHE_DIR = str(test_cache_dir)
    settings.LDAP_USER_ROOT = str(test_user_root)
    settings.SUBSTITUTE_DIRS = []
    settings.DOWNLOAD_FRONTEND = 'static'

    # Also patch module-level globals in downloads.views and downloads.utils
    import downloads.views as views
    import downloads.utils as utils

    monkeypatch.setattr(views, 'CACHE_DIR', str(test_cache_dir))
    monkeypatch.setattr(views, 'DOWNLOAD_ROOT', str(test_user_root))
    monkeypatch.setattr(views, 'DOWNLOAD_DIRS', [str(test_download_dir), str(test_user_root)])
    monkeypatch.setattr(views, 'SUBSTITUTE_DIRS', [])
    monkeypatch.setattr(views, 'FRONTEND', 'static')

    monkeypatch.setattr(utils, 'CACHE_DIR', str(test_cache_dir))

    return {
        "download_dir": test_download_dir,
        "cache_dir": test_cache_dir,
        "user_root": test_user_root,
    }


@pytest.fixture
def sample_secure_path(db, setup_test_environment):
    """
    Factory fixture to create a valid SecurePath record.
    """
    def _create(rel_or_abs_path="test_dataset"):
        if rel_or_abs_path.startswith('/'):
            target_path = rel_or_abs_path
        else:
            target_path = str(setup_test_environment["download_dir"] / rel_or_abs_path)
            os.makedirs(target_path, exist_ok=True)

        sp = SecurePath(path=target_path)
        sp.save()
        return sp

    return _create
