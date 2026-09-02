import pytest
from django.conf import settings
from downloads.models import SecurePath


@pytest.mark.django_db
def test_harness_smoke(sample_secure_path):
    """Smoke test to verify pytest, pytest-django, settings, and fixtures work."""
    sp = sample_secure_path("smoke_dataset")
    assert sp.key is not None
    assert len(sp.key) == 40
    assert sp.path.endswith("smoke_dataset")
    assert SecurePath.objects.filter(key=sp.key).exists()
