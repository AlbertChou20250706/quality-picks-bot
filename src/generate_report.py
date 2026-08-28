"""Generate the narrative for the quality-picks report via the Claude API.
The top-3 lists and every number in them are already decided by
screen_and_rank.py — the model only explains, using the code-computed
numbers, why each pick qualifies. Falls back to plain text if the model
doesn't follow the delimiter format, so a report still goes out either way.
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
CATEGORY_KEYS = {
    "TW_STOCKS": "tw_stocks",
    "TW_ETF": "tw_etf",
    "US_STOCKS": "us_stocks",
    "US_ETF": "us_etf",
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
        "tw_stocks_note": raw.get("TW_STOCKS", "").strip(),
        "tw_etf_note": raw.get("TW_ETF", "").strip(),
        "us_stocks_note": raw.get("US_STOCKS", "").strip(),
        "us_etf_note": raw.get("US_ETF", "").strip(),
        "outlook": raw.get("OUTLOOK", "").strip(),
    }


def render_markdown(parsed: dict, top_picks: dict, today: str) -> str:
    lines = [f"優質標的推薦（{today}）", "", parsed["summary"], ""]
    for key, note_key in [
        ("tw_stocks", "tw_stocks_note"),
        ("tw_etf", "tw_etf_note"),
        ("us_stocks", "us_stocks_note"),
        ("us_etf", "us_etf_note"),
    ]:
        lines.append(f"【{CATEGORY_LABELS[key]}】")
        for entry in top_picks[key]:
            lines.append(f"{entry['symbol']} {entry['name']}（評分 {entry['score']}）")
        lines.append("")
        lines.append(parsed[note_key])
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
        max_tokens=16000,
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

    archive_text = render_markdown(parsed, top_picks, today)
    archive_path.write_text(archive_text, encoding="utf-8")
    (OUTPUT_DIR / "report.txt").write_text(archive_text, encoding="utf-8")

    report_data = {
        "title": "優質標的推薦",
        "date": today,
        "summary": parsed["summary"],
        "outlook": parsed["outlook"],
        "disclaimer": DISCLAIMER,
        "categories": [
            {"key": key, "label": CATEGORY_LABELS[key], "note": parsed[note_key], "picks": top_picks[key]}
            for key, note_key in [
                ("tw_stocks", "tw_stocks_note"),
                ("tw_etf", "tw_etf_note"),
                ("us_stocks", "us_stocks_note"),
                ("us_etf", "us_etf_note"),
            ]
        ],
        "mode": "structured",
    }
    (OUTPUT_DIR / "report_data.json").write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"wrote {archive_path} and output/report_data.json")


if __name__ == "__main__":
    main()
