from __future__ import annotations

import json
from pathlib import Path


def read_review_draft(path: str | Path) -> dict:
    draft_path = Path(path)
    with draft_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict, pretty: bool) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        rendered = json.dumps(payload, ensure_ascii=False)
    output_path.write_text(rendered + "\n", encoding="utf-8")
