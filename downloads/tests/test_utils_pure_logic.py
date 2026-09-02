from pathlib import Path
import numpy as np
import pytest
from downloads.utils import downsample
from downloads.views import clean_path, make_alternates


class DummySize:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class DummyFrame:
    def __init__(self, data, x, y):
        self.data = data
        self.size = DummySize(x, y)


def test_downsample_math_and_dimensions():
    """Verify numpy matrix downsampling, block reduction, and output cropping."""
    # Create 100x100 matrix of ones
    data = np.ones((100, 100), dtype=float)
    frame = DummyFrame(data, x=100, y=100)

    # Downsample to target size 10 (factor = 100 // 10 = 10)
    result = downsample(frame, size=10, func=np.max)
    assert result.shape == (10, 10)
    assert np.all(result == 1.0)


def test_clean_path_normalization():
    """Verify leading slash stripping and path string normalization."""
    assert clean_path("/users/dataset/frame.cbf") == "users/dataset/frame.cbf"
    assert clean_path("users/dataset/frame.cbf") == "users/dataset/frame.cbf"


def test_make_alternates_without_substitutes(monkeypatch):
    """When SUBSTITUTE_DIRS is empty, make_alternates returns only the original path."""
    import downloads.views as views
    monkeypatch.setattr(views, "SUBSTITUTE_DIRS", [])

    path = Path("/data/folder1/file.txt")
    alternates = make_alternates(path)
    assert len(alternates) == 1
    assert alternates[0] == path


def test_make_alternates_with_substitutes(monkeypatch):
    """When path matches a prefix in SUBSTITUTE_DIRS, returns original path plus replaced alternate paths."""
    import downloads.views as views
    monkeypatch.setattr(views, "SUBSTITUTE_DIRS", ["/data/folder1", "/data/folder2"])

    path = Path("/data/folder1/dataset/file.txt")
    alternates = make_alternates(path)
    assert len(alternates) == 2
    assert Path("/data/folder1/dataset/file.txt") in alternates
    assert Path("/data/folder2/dataset/file.txt") in alternates
