"""Tests for safe low-level Goodnotes decoding primitives."""

import struct

import pytest

from handwriting.goodnotes.extraction import GoodnotesFormatError, StrokePoint, _fields, _geometry, _sections, _translation, _translate_points


def test_decodes_raw_apple_lz4_frame() -> None:
    assert _geometry(b"bv4-\x03\x00\x00\x00abc" + b"bv4$") == b"abc"


def test_rejects_unterminated_apple_lz4_frame() -> None:
    with pytest.raises(GoodnotesFormatError, match="no terminator"):
        _geometry(b"bv4-\x03\x00\x00\x00abc")


def test_decodes_constant_width_tpl_sections() -> None:
    signature = b"uA(S(uu))\x00"
    payload = struct.pack("<fI4f", 2.0, 2, 1.0, 2.0, 3.0, 4.0)
    blob = b"tpl\x00" + struct.pack("<I", 8 + len(signature) + len(payload)) + signature + payload
    sections = _sections(blob)
    assert sections[0] == ("scalar", "u", [2.0])
    assert sections[1] == ("struct", "uu", [(1.0, 2.0), (3.0, 4.0)])


def test_applies_field_6_stroke_translation() -> None:
    translation_message = b"\r" + struct.pack("<f", 12.5) + b"\x15" + struct.pack("<f", -3.25)
    fields = _fields(b"2" + bytes([len(translation_message)]) + translation_message)

    assert _translation(fields) == (12.5, -3.25)
    assert _translate_points([StrokePoint(1.0, 2.0, 3.0)], _translation(fields)) == [StrokePoint(13.5, -1.25, 3.0)]
