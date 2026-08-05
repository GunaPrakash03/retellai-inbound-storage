"""Print the Post-Call Data Extraction config to paste into Retell.

    python3 -m tools.extraction_config           # markdown table (README)
    python3 -m tools.extraction_config --plain   # one field per block, to copy

Generated from app/intake_fields.py, which is the same spec the database
schema and the webhook handler are built from — so what you paste into Retell
is what the backend stores, without a second list to keep in step by hand.
"""
import sys

from app.intake_fields import ALL_FIELDS, CATEGORIES, CATEGORY_FIELDS, CORE_FIELDS

_RETELL_TYPE = {"text": "Text", "bool": "Boolean"}


def _categories_using(name: str) -> str:
    if any(f.name == name for f in CORE_FIELDS):
        return "all"
    used = [c for c, _ in CATEGORIES if any(f.name == name for f in CATEGORY_FIELDS[c])]
    return ", ".join(used)


def markdown() -> str:
    lines = [
        "| Field | Type | Asked in | Description to paste in Retell |",
        "|---|---|---|---|",
    ]
    for f in ALL_FIELDS:
        lines.append(
            f"| `{f.name}` | {_RETELL_TYPE[f.kind]} | {_categories_using(f.name)} | {f.description} |"
        )
    return "\n".join(lines)


def plain() -> str:
    blocks = []
    for f in ALL_FIELDS:
        blocks.append(
            f"Name: {f.name}\nType: {_RETELL_TYPE[f.kind]}\nDescription: {f.description}\n"
        )
    return "\n".join(blocks)


if __name__ == "__main__":
    print(plain() if "--plain" in sys.argv else markdown())
