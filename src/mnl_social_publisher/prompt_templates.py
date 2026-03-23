from __future__ import annotations

from importlib.resources import files
import os
from pathlib import Path


PROMPT_PACKAGE = "mnl_social_publisher.prompts"


class _SafePromptValues(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _normalize_context_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item) for item in value if str(item).strip())
    return str(value)


def prompt_path(template_name: str):
    override_root = _override_root()
    if override_root is not None:
        override_path = override_root / template_name
        if override_path.exists():
            return override_path
    parts = [part for part in template_name.replace("\\", "/").split("/") if part]
    return files(PROMPT_PACKAGE).joinpath(*parts)


def load_prompt_template(template_name: str) -> str:
    return prompt_path(template_name).read_text(encoding="utf-8")


def render_prompt_template(template_name: str, **context: object) -> str:
    template = load_prompt_template(template_name)
    rendered = template.format_map(
        _SafePromptValues({key: _normalize_context_value(value) for key, value in context.items()})
    )
    lines = [line.rstrip() for line in rendered.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _override_root() -> Path | None:
    raw = (os.getenv("MNL_SOCIAL_TEMPLATE_ROOT") or "").strip()
    if not raw:
        return None
    return Path(raw)
