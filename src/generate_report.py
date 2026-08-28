"""Generate the narrative for the quality-picks report via the Claude API.
The top-10 lists and every number in them are already decided by
screen_and_rank.py — the model only explains, per pick, using the
code-computed numbers, why it qualifies. Falls back to plain text if the
model doesn't follow the delimiter format, so a report still goes out
either way.
"""

import json
import os
import pathlib
import re
from datetime import date

import anthropic

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "top_picks.json"
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
ARCHIVE_DIR = BASE_DIR / "reports"
OUTPUT_DIR = BASE_DIR / "output"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DISCLAIMER = "投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議"

SECTION_RE = re.compile(r"^##([A-Z_]+)##\s*$", re.MULTILINE)
CATEGORY_NOTE_KEYS = {
    "tw_stocks": "TW_STOCKS",
    "tw_etf": "TW_ETF",
    "us_stocks": "US_STOCKS",
    "us_etf": "US_ETF",
}
CATEGORY_LABELS = {
    "tw_stocks": "台股優質個股",
    "tw_etf": "台股優質 ETF",
    "us_stocks": "美股優質個股",
    "us_etf": "美股優質 ETF",
}


def build_user_content(top_picks: dict) -> str:
    return (
        "以下是本次程式篩選好的優質標的清單（JSON，已依量化公式排序，不可更動排名），"
        "請依照系統提示的格式撰寫報告：\n\n" + json.dumps(top_picks, ensure_ascii=False, indent=2)
    )


def parse_sections(text: str) -> dict | None:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return None

    raw = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw[name] = text[start:end].strip()

    if "SUMMARY" not in raw:
        return None

    return {
        "summary": raw.get("SUMMARY", "").strip(),
        "outlook": raw.get("OUTLOOK", "").strip(),
        "notes_by_category": {name: raw.get(name, "") for name in CATEGORY_NOTE_KEYS.values()},
    }


def parse_pick_notes(block_text: str) -> dict:
    """Parse "代號 一句話理由" lines into {symbol: note}. A line that doesn't
    start with a recognizable symbol token is skipped rather than guessed at."""
    notes = {}
    for line in block_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            symbol, note = parts
            notes[symbol] = note.strip()
    return notes


def attach_notes(top_picks: dict, parsed: dict) -> dict:
    """Return a deep-ish copy of top_picks with each pick's model-written
    note attached by symbol match. A pick the model didn't cover just gets
    no note rather than an invented one."""
    categorized = {}
    for key, section_name in CATEGORY_NOTE_KEYS.items():
        notes_by_symbol = parse_pick_notes(parsed["notes_by_category"].get(section_name, ""))
        picks = []
        for entry in top_picks[key]:
            enriched = dict(entry)
            enriched["note"] = notes_by_symbol.get(entry["symbol"], "")
            picks.append(enriched)
        categorized[key] = picks
    return categorized


def render_markdown(parsed: dict, categorized_picks: dict, today: str) -> str:
    lines = [f"優質標的推薦（{today}）", "", parsed["summary"], ""]
    for key in CATEGORY_NOTE_KEYS:
        lines.append(f"【{CATEGORY_LABELS[key]}】")
        for rank, entry in enumerate(categorized_picks[key], start=1):
            lines.append(f"{rank}. {entry['symbol']} {entry['name']}（評分 {entry['score']}）")
            if entry["note"]:
                lines.append(f"　{entry['note']}")
        lines.append("")
    lines += ["【後續觀察】", parsed["outlook"], ""]
    lines += [DISCLAIMER]
    return "\n".join(lines)


def main() -> None:
    top_picks = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=24000,
        output_config={"effort": "medium"},
        system=system_prompt,
        messages=[{"role": "user", "content": build_user_content(top_picks)}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    archive_path = ARCHIVE_DIR / f"{today}.md"

    parsed = parse_sections(raw_text)
    if parsed is None:
        print("warning: could not parse structured sections, falling back to plain text")
        report_text = raw_text if DISCLAIMER in raw_text else raw_text.rstrip() + "\n\n" + DISCLAIMER
        archive_path.write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / "report.txt").write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / "report_data.json").write_text(json.dumps({"mode": "plain_text"}), encoding="utf-8")
        print(f"wrote {archive_path} (plain text fallback)")
        return

    categorized_picks = attach_notes(top_picks, parsed)

    archive_text = render_markdown(parsed, categorized_picks, today)
    archive_path.write_text(archive_text, encoding="utf-8")
    (OUTPUT_DIR / "report.txt").write_text(archive_text, encoding="utf-8")

    report_data = {
        "title": "優質標的推薦",
        "date": today,
        "summary": parsed["summary"],
        "outlook": parsed["outlook"],
        "disclaimer": DISCLAIMER,
        "categories": [
            {"key": key, "label": CATEGORY_LABELS[key], "picks": categorized_picks[key]}
            for key in CATEGORY_NOTE_KEYS
        ],
        "mode": "structured",
    }
    (OUTPUT_DIR / "report_data.json").write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"wrote {archive_path} and output/report_data.json")


if __name__ == "__main__":
    main()
