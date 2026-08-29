import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import imager


def test_resolve_image_from_path(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"fake png")
    result = imager.resolve_image(image_path=str(img), out_dir=tmp_path)
    assert result.exists()
