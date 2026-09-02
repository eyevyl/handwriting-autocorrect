"""Extract a schema-24 Goodnotes page and render its native ink as SVG."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from handwriting.goodnotes.extraction import extract_goodnotes
from handwriting.visualization.render import render_page_svg


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("source", type=Path); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args()
    document = extract_goodnotes(args.source); args.output_dir.mkdir(parents=True, exist_ok=True)
    for number, page in enumerate(document.pages, 1): render_page_svg(page, args.output_dir / f"page-{number}.svg")
    report = document.report
    payload = {"source": str(report.source), "schema_version": report.schema_version, "pages_seen": report.pages_seen, "pages_extracted": report.pages_extracted, "stroke_records_seen": report.stroke_records_seen, "strokes_extracted": report.strokes_extracted, "skipped_records": report.skipped_records}
    (args.output_dir / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__": main()
