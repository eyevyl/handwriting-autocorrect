"""Read native visible ink from Goodnotes 6 schema-24 archives.

Only validated ZIP/protobuf/LZ4 pen records are decoded. Other record types
are retained in an audit count instead of being silently interpreted as ink.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import struct
import zipfile


class GoodnotesFormatError(ValueError):
    """A required Goodnotes binary structure was malformed or unsupported."""


@dataclass(frozen=True)
class StrokePoint:
    x: float
    y: float
    width: float


@dataclass(frozen=True)
class Stroke:
    points: tuple[StrokePoint, ...]
    color_rgba: tuple[float, float, float, float]
    tool: str
    source_id: str | None = None


@dataclass(frozen=True)
class Page:
    id: str
    width: float
    height: float
    strokes: tuple[Stroke, ...]


@dataclass(frozen=True)
class ExtractionReport:
    source: Path
    schema_version: int | None
    pages_seen: int
    pages_extracted: int
    stroke_records_seen: int
    strokes_extracted: int
    skipped_records: dict[str, int]


@dataclass(frozen=True)
class GoodnotesDocument:
    pages: tuple[Page, ...]
    report: ExtractionReport


@dataclass(frozen=True)
class _Field:
    number: int
    wire_type: int
    value: int | float | bytes


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if pos >= len(data):
            raise GoodnotesFormatError("varint extends past end")
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, pos
        shift += 7
        if shift > 63:
            raise GoodnotesFormatError("varint exceeds 64 bits")


def _fields(data: bytes) -> dict[int, list[_Field]]:
    pos, result = 0, {}
    while pos < len(data):
        key, pos = _varint(data, pos)
        number, kind = key >> 3, key & 7
        if number == 0:
            raise GoodnotesFormatError("protobuf field 0")
        if kind == 0:
            value, pos = _varint(data, pos)
        elif kind == 1:
            if pos + 8 > len(data): raise GoodnotesFormatError("truncated fixed64")
            value = struct.unpack_from("<d", data, pos)[0]; pos += 8
        elif kind == 2:
            size, pos = _varint(data, pos)
            if pos + size > len(data): raise GoodnotesFormatError("truncated bytes")
            value = data[pos:pos + size]; pos += size
        elif kind == 5:
            if pos + 4 > len(data): raise GoodnotesFormatError("truncated fixed32")
            value = struct.unpack_from("<f", data, pos)[0]; pos += 4
        else:
            raise GoodnotesFormatError(f"unsupported protobuf wire type {kind}")
        result.setdefault(number, []).append(_Field(number, kind, value))
    return result


def _records(data: bytes) -> list[bytes]:
    pos, result = 0, []
    while pos < len(data):
        size, pos = _varint(data, pos)
        if pos + size > len(data): raise GoodnotesFormatError("record stream truncated")
        result.append(data[pos:pos + size]); pos += size
    return result


def _lz4_block(data: bytes, expected: int) -> bytes:
    output, pos = bytearray(), 0
    while pos < len(data):
        token = data[pos]; pos += 1
        literal = token >> 4
        if literal == 15:
            while True:
                byte = data[pos]; pos += 1; literal += byte
                if byte != 255: break
        output.extend(data[pos:pos + literal]); pos += literal
        if pos >= len(data): break
        if pos + 2 > len(data): raise GoodnotesFormatError("truncated LZ4 offset")
        offset = struct.unpack_from("<H", data, pos)[0]; pos += 2
        if not offset or offset > len(output): raise GoodnotesFormatError("invalid LZ4 offset")
        length = (token & 15) + 4
        if (token & 15) == 15:
            while True:
                byte = data[pos]; pos += 1; length += byte
                if byte != 255: break
        start = len(output) - offset
        for index in range(length): output.append(output[start + index])
    if len(output) != expected: raise GoodnotesFormatError("unexpected LZ4 output length")
    return bytes(output)


def _geometry(data: bytes) -> bytes:
    output, pos = bytearray(), 0
    while pos < len(data):
        marker = data[pos:pos + 4]
        if marker == b"bv4$": return bytes(output)
        if marker == b"bv41":
            if pos + 12 > len(data): raise GoodnotesFormatError("truncated LZ4 frame")
            decoded, encoded = struct.unpack_from("<II", data, pos + 4); end = pos + 12 + encoded
            if end > len(data): raise GoodnotesFormatError("compressed LZ4 frame truncated")
            output.extend(_lz4_block(data[pos + 12:end], decoded)); pos = end
        elif marker == b"bv4-":
            if pos + 8 > len(data): raise GoodnotesFormatError("truncated raw LZ4 frame")
            size = struct.unpack_from("<I", data, pos + 4)[0]; end = pos + 8 + size
            if end > len(data): raise GoodnotesFormatError("raw LZ4 frame truncated")
            output.extend(data[pos + 8:end]); pos = end
        else: raise GoodnotesFormatError(f"unknown Apple LZ4 marker {marker!r}")
    raise GoodnotesFormatError("Apple LZ4 stream has no terminator")


def _tokens(signature: str) -> list[tuple[str, str]]:
    pos, result = 0, []
    while pos < len(signature):
        if signature.startswith("A(S(", pos):
            end = signature.find(")", pos + 4)
            if end < 0 or signature[end:end + 2] != "))": raise GoodnotesFormatError("bad tpl struct signature")
            result.append(("struct", signature[pos + 4:end])); pos = end + 2
        elif signature.startswith("A(", pos) and pos + 3 < len(signature) and signature[pos + 3] == ")":
            result.append(("array", signature[pos + 2])); pos += 4
        elif signature[pos] in "uvf": result.append(("scalar", signature[pos])); pos += 1
        else: raise GoodnotesFormatError(f"unknown tpl token: {signature!r}")
    return result


def _sections(data: bytes) -> list[tuple[str, str, list]]:
    if data[:4] != b"tpl\0" or len(data) < 9: raise GoodnotesFormatError("missing tpl header")
    if struct.unpack_from("<I", data, 4)[0] != len(data): raise GoodnotesFormatError("invalid tpl length")
    end = data.find(0, 8)
    if end < 0: raise GoodnotesFormatError("unterminated tpl signature")
    pos, result = end + 1, []
    formats = {"u": ("f", 4), "v": ("H", 2), "f": ("f", 4)}
    for kind, spec in _tokens(data[8:end].decode("ascii")):
        if kind == "scalar":
            code, unit = formats[spec]
            if pos + unit > len(data): raise GoodnotesFormatError("truncated tpl scalar")
            values = [struct.unpack_from("<" + code, data, pos)[0]]; pos += unit
        else:
            if pos + 4 > len(data): raise GoodnotesFormatError("truncated tpl count")
            count = struct.unpack_from("<I", data, pos)[0]; pos += 4
            if kind == "array":
                code, unit = formats[spec]
                size = count * unit
                if pos + size > len(data): raise GoodnotesFormatError("truncated tpl array")
                values = list(struct.unpack_from(f"<{count}{code}", data, pos)); pos += size
            else:
                if set(spec) != {"u"}: raise GoodnotesFormatError("unsupported tpl struct type")
                size = count * len(spec) * 4
                if pos + size > len(data): raise GoodnotesFormatError("truncated tpl struct")
                flat = struct.unpack_from(f"<{count * len(spec)}f", data, pos)
                values = [tuple(flat[i:i + len(spec)]) for i in range(0, len(flat), len(spec))]; pos += size
        result.append((kind, spec, values))
    if pos != len(data): raise GoodnotesFormatError("trailing tpl bytes")
    return result


def _point_ok(point: StrokePoint) -> bool:
    return 0 <= point.x <= 2000 and 0 <= point.y <= 2000 and .01 < point.width <= 60


def _points(data: bytes) -> list[StrokePoint]:
    sections = _sections(data)
    flags = next((set(values) for kind, spec, values in sections if kind == "array" and spec == "v"), set())
    tilt = any(flag & 4 for flag in flags)
    for kind, spec, values in sections:
        if kind != "array" or spec != "u": continue
        values = [float(value) for value in values]
        if tilt and len(values) % 9 == 0:
            points = [StrokePoint(*values[i:i + 3]) for i in range(0, len(values), 3) if i % 9 in (0, 3)]
        elif not tilt and len(values) % 3 == 0:
            points = [StrokePoint(*values[i:i + 3]) for i in range(0, len(values), 3)]
        else: continue
        if len(points) >= 2 and all(_point_ok(point) for point in points): return points
    width = next((float(values[0]) for kind, spec, values in sections if kind == "scalar" and spec == "u"), 1.)
    arrays = sorted(((spec, values) for kind, spec, values in sections if kind == "struct" and values), key=lambda item: (-len(item[1]), -len(item[0])))
    for spec, values in arrays:
        for begin, final in (((0, 1), (2, 3)), ((1, 2), (6, 7))):
            if max(final) >= len(spec): continue
            pairs = [(row[begin[0]], row[begin[1]]) for row in values] + [(values[-1][final[0]], values[-1][final[1]])]
            if all(0 <= x <= 2000 and 0 <= y <= 2000 for x, y in pairs): return [StrokePoint(x, y, width) for x, y in pairs]
    return []


def _style(fields: dict[int, list[_Field]]) -> str:
    if fields.get(5, [_Field(5, 0, 0)])[0].value == 1: return "highlighter"
    value = fields.get(3, [_Field(3, 0, 0)])[0].value
    if value == 5: return "pencil"
    if value == 1: return "marker" if fields.get(20, [_Field(20, 2, b"")])[0].value else "pressure_pen"
    return "ballpoint"


def _color(fields: dict[int, list[_Field]]) -> tuple[float, float, float, float]:
    rgba = [0., 0., 0., 1.]
    if 4 in fields and isinstance(fields[4][0].value, bytes):
        for field in _fields(fields[4][0].value).values():
            item = field[0]
            if 1 <= item.number <= 4 and isinstance(item.value, float): rgba[item.number - 1] = item.value
    return tuple(rgba)  # type: ignore[return-value]


def _translation(fields: dict[int, list[_Field]]) -> tuple[float, float]:
    """Return the optional schema-24 stroke offset stored in field 6."""
    entries = fields.get(6)
    if not entries or not isinstance(entries[0].value, bytes) or not entries[0].value:
        return 0.0, 0.0
    offset = _fields(entries[0].value)
    x = offset.get(1, [_Field(1, 5, 0.0)])[0].value
    y = offset.get(2, [_Field(2, 5, 0.0)])[0].value
    if not isinstance(x, float) or not isinstance(y, float):
        raise GoodnotesFormatError("stroke translation must contain float x/y values")
    return x, y


def _translate_points(points: list[StrokePoint], translation: tuple[float, float]) -> list[StrokePoint]:
    """Map stroke-local geometry into page space using its record translation."""
    x_offset, y_offset = translation
    return [StrokePoint(point.x + x_offset, point.y + y_offset, point.width) for point in points]


def extract_goodnotes(path: str | Path) -> GoodnotesDocument:
    """Extract schema-24 Goodnotes pen strokes in original page coordinates."""
    source = Path(path)
    if not zipfile.is_zipfile(source): raise GoodnotesFormatError(f"not a ZIP archive: {source}")
    skipped: Counter[str] = Counter(); pages: list[Page] = []; seen = extracted = 0
    with zipfile.ZipFile(source) as archive:
        schema = _fields(archive.read("schema.pb"))
        version = schema.get(1, [_Field(1, 0, None)])[0].value
        if version != 24: raise GoodnotesFormatError(f"unsupported schema {version!r}; expected 24")
        ids = [name.removeprefix("notes/") for name in archive.namelist() if name.startswith("notes/")]
        try:
            ordered = [f[1][0].value.decode("ascii") for f in (_fields(record) for record in _records(archive.read("index.notes.pb"))) if 1 in f and isinstance(f[1][0].value, bytes) and f[1][0].value.decode("ascii") in ids]
            if ordered: ids = ordered + [page_id for page_id in ids if page_id not in ordered]
        except (GoodnotesFormatError, UnicodeDecodeError): pass
        for page_id in ids:
            strokes: list[Stroke] = []
            try: records = _records(archive.read(f"notes/{page_id}"))
            except GoodnotesFormatError: skipped["malformed_page_stream"] += 1; continue
            for record in records:
                try:
                    top = _fields(record)
                    if 7 not in top or not isinstance(top[7][0].value, bytes): skipped["non_stroke_record"] += 1; continue
                    seen += 1; fields = _fields(top[7][0].value)
                    if 2 not in fields or not isinstance(fields[2][0].value, bytes): skipped["stroke_without_geometry"] += 1; continue
                    points = _points(_geometry(fields[2][0].value))
                    if not points: skipped["stroke_without_usable_points"] += 1; continue
                    points = _translate_points(points, _translation(fields))
                    source_id = fields[1][0].value.decode("ascii", "replace") if 1 in fields and isinstance(fields[1][0].value, bytes) else None
                    strokes.append(Stroke(tuple(points), _color(fields), _style(fields), source_id)); extracted += 1
                except (GoodnotesFormatError, IndexError, struct.error): skipped["undecodable_stroke_record"] += 1
            max_x = max((point.x for stroke in strokes for point in stroke.points), default=595.28)
            max_y = max((point.y for stroke in strokes for point in stroke.points), default=841.89)
            pages.append(Page(page_id, max(595.28, max_x + 12), max(841.89, max_y + 12), tuple(strokes)))
    return GoodnotesDocument(tuple(pages), ExtractionReport(source, 24, len(ids), len(pages), seen, extracted, dict(skipped)))
