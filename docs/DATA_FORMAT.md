# Goodnotes Data Format Validation

## Validated sample

`Co250 Cheatsheet.goodnotes` was copied unchanged from the supplied location to
the ignored `data/raw/` directory for this local validation run. Its SHA-256 is
`3FCD8AA6E13B64D4B64E555F2C630AD004763B4EFA5228102EDF7CB89745D522`.

The archive is a ZIP container with schema version 24 (`schema.pb = 08 18`).
It has one `notes/<page UUID>` member, an `index.notes.pb` page index, a
thumbnail, and one embedded PDF attachment.

## Recovered representation

`handwriting.goodnotes.extraction.extract_goodnotes()` produces a stable,
format-independent page-space representation:

```text
GoodnotesDocument
  Page(id, width, height)
    Stroke(points=[StrokePoint(x, y, width), ...], color_rgba, tool)
```

- Coordinates are PDF points at 72 dpi, top-left origin, with y increasing
  downward. Geometry points are translated into page space using the optional
  per-stroke field-6 `(x, y)` offset.
- Stroke boundaries are preserved; the output contains only paths with two or
  more decoded points.
- `width` is Goodnotes' rendered per-point width. It is not raw stylus pressure
  and must not be converted back into pressure.
- RGBA color and tool family are recovered for ballpoint, pressure pen,
  pencil, marker, and highlighter records.

## Validation outcome

The supplied page yielded 1,784 usable strokes containing 37,424 points. The
reader encountered 305 geometry records that did not produce a usable path;
these are recorded as `stroke_without_usable_points` rather than silently
discarded. A native-ink SVG reconstruction is written to the ignored
`outputs/goodnotes-validation/page-1.svg` by the inspection command.

Run the workflow with:

```powershell
python scripts/inspect_goodnotes.py data/raw/<notebook>.goodnotes --output-dir outputs/goodnotes-validation
```

## Known limitations

- The current reader intentionally supports schema version 24 only.
- It does not yet recover paper templates, PDF attachment placement, text,
  images, shapes, or eraser-edit history.
- Page dimensions currently grow from ink extents with an A4 minimum; the next
  increment should decode paper dimensions from `index.events.pb`.
- The SVG reconstruction uses round line segments. It validates coordinates,
  stroke order, color, and width, but is not expected to exactly reproduce the
  proprietary Goodnotes brush renderer.
