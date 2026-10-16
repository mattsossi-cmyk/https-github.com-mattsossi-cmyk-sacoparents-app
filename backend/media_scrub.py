"""Remove hidden metadata (EXIF/GPS, XMP, text chunks, PDF info) from uploads before they are stored.

level: "none" (keep as is), "location" (structured: EXIF incl. GPS, XMP and text removed; colour profile kept)
or "all" (restricted: everything removed, colour profile too). Unknown file types can't be cleaned, so they are refused.
"""
from io import BytesIO

from PIL import Image, ImageOps

_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


class UnsupportedFile(ValueError):
    pass


def _scrub_image(data: bytes, level: str) -> bytes:
    with Image.open(BytesIO(data)) as img:
        fmt = img.format
        if fmt not in _IMAGE_FORMATS:
            raise UnsupportedFile("This image type can't be cleaned.")
        icc = img.info.get("icc_profile") if level == "location" else None
        img = ImageOps.exif_transpose(img)
        if img.mode == "P":
            img = img.convert("RGBA")
        clean = Image.frombytes(img.mode, img.size, img.tobytes())
    out = BytesIO()
    kwargs = {"icc_profile": icc} if icc else {}
    if fmt == "JPEG":
        clean.convert("RGB").save(out, format="JPEG", quality=92, **kwargs)
    else:
        clean.save(out, format=fmt, **kwargs)
    return out.getvalue()


def _scrub_pdf(data: bytes) -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(BytesIO(data))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Producer": "", "/Creator": ""})
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def scrub_upload(data: bytes, level: str) -> bytes:
    if level == "none":
        return data
    if data[:5] == b"%PDF-":
        return _scrub_pdf(data)
    try:
        return _scrub_image(data, level)
    except UnsupportedFile:
        raise
    except Exception as exc:
        raise UnsupportedFile("This file type can't be cleaned.") from exc
