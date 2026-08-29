import mimetypes
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests


def _load_paths():
    from pipeline import paths
    return paths


def _validate_image(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        raise ValueError(f"Unsupported image format: {path.suffix}")


def _download_image(url: str, out_dir: Path) -> Path:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    parsed = urlparse(url)
    name = Path(parsed.path).name or "image"
    if not name or "." not in name:
        content_type = response.headers.get("Content-Type", "")
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".png"
        name = f"downloaded_image{ext}"
    dest = out_dir / name
    dest.write_bytes(response.content)
    _validate_image(dest)
    return dest


def _generate_image(prompt: str, out_dir: Path, model: str | None = None) -> Path:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    model_name = model or os.getenv("OPENAI_IMAGE_MODEL") or "dall-e-3"
    response = client.images.generate(prompt=prompt, model=model_name, n=1, size="1024x1024")
    image_url = response.data[0].url
    return _download_image(image_url, out_dir)


def resolve_image(
    image_path: str | None = None,
    image_url: str | None = None,
    image_prompt: str | None = None,
    out_dir: Path | None = None,
) -> Path:
    paths = _load_paths()
    if out_dir is None:
        out_dir = paths.images_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    if image_path:
        src = Path(image_path)
        _validate_image(src)
        dest = out_dir / src.name
        if src.resolve() == dest.resolve():
            return src
        shutil.copy2(src, dest)
        return dest

    if image_url:
        return _download_image(image_url, out_dir)

    if image_prompt:
        return _generate_image(image_prompt, out_dir)

    raise ValueError("One of image_path, image_url, or image_prompt is required")
