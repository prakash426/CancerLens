"""Screenshot upload guard (SEC-03).

Validates PNG / JPEG / WEBP uploads strictly in memory (zero disk writes):
magic bytes, 5 MB cap, 4096x4096 dimension cap parsed from the raw headers in
pure Python, content-type cross-check, and in-memory EXIF/metadata stripping.
Any violation raises ``ValueError`` (mapped to HTTP 422 at the route).
"""

from __future__ import annotations

import struct

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_DIMENSION = 4096

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SOI = b"\xff\xd8"
_PNG_STRIP_CHUNKS = frozenset({b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"})
_WEBP_STRIP_CHUNKS = frozenset({b"EXIF", b"XMP "})

_CONTENT_TYPES = {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}


def _detect_kind(data: bytes) -> str | None:
    if data.startswith(_PNG_SIGNATURE):
        return "png"
    if len(data) >= 3 and data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF:
        return "jpeg"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _check_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("Image has invalid zero dimensions.")
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise ValueError(f"Image dimensions {width}x{height} exceed the {MAX_DIMENSION}x{MAX_DIMENSION} limit.")


# --------------------------------------------------------------------------- PNG


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24:
        raise ValueError("Truncated PNG header.")
    (length,) = struct.unpack(">I", data[8:12])
    if length != 13 or data[12:16] != b"IHDR":
        raise ValueError("Malformed PNG: first chunk is not IHDR.")
    width, height = struct.unpack(">II", data[16:24])
    _check_dimensions(width, height)
    return width, height


def _png_strip(data: bytes) -> bytes:
    """Drop tEXt/zTXt/iTXt/eXIf/tIME chunks; keep every other chunk byte-identical."""
    out = bytearray(_PNG_SIGNATURE)
    pos = 8
    seen_iend = False
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        chunk_type = data[pos + 4 : pos + 8]
        end = pos + 8 + length + 4
        if length < 0 or end > len(data):
            raise ValueError("Truncated PNG chunk.")
        if chunk_type not in _PNG_STRIP_CHUNKS:
            out += data[pos:end]
        if chunk_type == b"IEND":
            seen_iend = True
            pos = end
            break
        pos = end
    if not seen_iend or pos != len(data):
        raise ValueError("Malformed PNG: missing IEND or trailing bytes.")
    return bytes(out)


# --------------------------------------------------------------------------- JPEG


def _jpeg_scan(data: bytes) -> tuple[int, int, bytes]:
    """Return (width, height, sanitized_bytes), stripping APP1 (EXIF/XMP) and COM."""
    if len(data) < 4 or data[0:2] != _JPEG_SOI:
        raise ValueError("Malformed JPEG: missing SOI marker.")
    out = bytearray(data[0:2])
    pos = 2
    width = height = 0
    while pos < len(data):
        if data[pos] != 0xFF:
            raise ValueError("Malformed JPEG: expected marker prefix.")
        while pos < len(data) and data[pos] == 0xFF:  # skip fill bytes
            pos += 1
        if pos >= len(data):
            raise ValueError("Truncated JPEG marker.")
        marker = data[pos]
        marker_at = pos - 1
        pos += 1
        if marker == 0xD9:  # EOI
            out += b"\xff\xd9"
            if pos != len(data):
                raise ValueError("Malformed JPEG: trailing bytes after EOI.")
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:  # TEM / RSTn: standalone
            out += bytes((0xFF, marker))
            continue
        if pos + 2 > len(data):
            raise ValueError("Truncated JPEG segment header.")
        (seg_len,) = struct.unpack(">H", data[pos : pos + 2])
        if seg_len < 2 or marker_at + 2 + seg_len > len(data):
            raise ValueError("Truncated JPEG segment.")
        seg_end = marker_at + 2 + seg_len
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if seg_len < 7:
                raise ValueError("Truncated JPEG frame header.")
            height = struct.unpack(">H", data[pos + 3 : pos + 5])[0]
            width = struct.unpack(">H", data[pos + 5 : pos + 7])[0]
            _check_dimensions(width, height)
        if marker == 0xDA:  # SOS: copy header plus the whole entropy-coded rest verbatim
            out += data[marker_at:seg_end]
            out += data[seg_end:]
            pos = len(data)
            break
        if marker not in (0xE1, 0xFE):  # keep everything except APP1 (EXIF/XMP) and COM
            out += data[marker_at:seg_end]
        pos = seg_end
    if width <= 0 or height <= 0:
        raise ValueError("Malformed JPEG: no frame (SOF) header found.")
    return width, height, bytes(out)


# --------------------------------------------------------------------------- WEBP


def _webp_vp8_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 10 or payload[0] & 0x01:
        raise ValueError("Malformed WEBP: not a VP8 keyframe.")
    if payload[3:6] != b"\x9d\x01\x2a":
        raise ValueError("Malformed WEBP: bad VP8 start code.")
    width = struct.unpack("<H", payload[6:8])[0] & 0x3FFF
    height = struct.unpack("<H", payload[8:10])[0] & 0x3FFF
    _check_dimensions(width, height)
    return width, height


def _webp_vp8l_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 5 or payload[0] != 0x2F:
        raise ValueError("Malformed WEBP: bad VP8L signature.")
    bits = struct.unpack("<I", payload[1:5])[0]
    width = (bits & 0x3FFF) + 1
    height = ((bits >> 14) & 0x3FFF) + 1
    _check_dimensions(width, height)
    return width, height


def _webp_vp8x_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 10:
        raise ValueError("Truncated WEBP VP8X header.")
    width = int.from_bytes(payload[4:7], "little") + 1
    height = int.from_bytes(payload[7:10], "little") + 1
    _check_dimensions(width, height)
    return width, height


def _webp_scan(data: bytes) -> tuple[int, int, bytes]:
    """Return (width, height, sanitized_bytes), stripping EXIF and XMP chunks."""
    (riff_size,) = struct.unpack("<I", data[4:8])
    if 8 + riff_size != len(data):
        raise ValueError("Malformed WEBP: RIFF size mismatch.")
    kept: list[bytes] = []
    width = height = 0
    pos = 12
    while pos + 8 <= len(data):
        fourcc = data[pos : pos + 4]
        (size,) = struct.unpack("<I", data[pos + 4 : pos + 8])
        payload = data[pos + 8 : pos + 8 + size]
        if len(payload) != size:
            raise ValueError("Truncated WEBP chunk.")
        if fourcc == b"VP8 " and width == 0:
            width, height = _webp_vp8_dimensions(payload)
        elif fourcc == b"VP8L" and width == 0:
            width, height = _webp_vp8l_dimensions(payload)
        elif fourcc == b"VP8X" and width == 0:
            width, height = _webp_vp8x_dimensions(payload)
        if fourcc not in _WEBP_STRIP_CHUNKS:
            chunk = data[pos : pos + 8 + size]
            if size % 2:
                pad_at = pos + 8 + size
                if pad_at >= len(data):
                    raise ValueError("Truncated WEBP chunk padding.")
                chunk += data[pad_at : pad_at + 1]
            kept.append(chunk)
        pos += 8 + size + (size % 2)
    if pos != len(data):
        raise ValueError("Malformed WEBP: trailing bytes.")
    if width <= 0 or height <= 0:
        raise ValueError("Malformed WEBP: no VP8/VP8L/VP8X image chunk found.")
    body = b"WEBP" + b"".join(kept)
    return width, height, b"RIFF" + struct.pack("<I", len(body)) + body


# --------------------------------------------------------------------------- entry


def guard_image_upload(data: bytes, content_type: str | None) -> bytes:
    """Validate and sanitize an uploaded screenshot. Returns sanitized bytes.

    Raises ``ValueError`` on empty input, >5 MB payloads, unknown magic bytes,
    content-type mismatches, bad dimensions or truncated structures.
    """
    if not isinstance(data, bytes) or not data:
        raise ValueError("Empty image upload.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image upload exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit.")
    kind = _detect_kind(data)
    if kind is None:
        raise ValueError("Unsupported image type (PNG, JPEG or WEBP magic bytes required).")
    if content_type:
        claimed = content_type.split(";")[0].strip().lower()
        if _CONTENT_TYPES.get(claimed) != kind:
            raise ValueError("Upload content-type does not match the image magic bytes.")
    if kind == "png":
        _png_dimensions(data)
        return _png_strip(data)
    if kind == "jpeg":
        _width, _height, sanitized = _jpeg_scan(data)
        return sanitized
    _width, _height, sanitized = _webp_scan(data)
    return sanitized


__all__ = ["MAX_DIMENSION", "MAX_IMAGE_BYTES", "guard_image_upload"]
