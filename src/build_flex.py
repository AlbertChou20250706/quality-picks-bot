"""Build a LINE Flex Message (card layout) from output/report_data.json.
Falls back to nothing if generate_report.py had to fall back to plain text
(send_line.py handles that case directly). No chart/hero image — this report
is a ranked list with per-pick rationale, not a price/trend report.
"""

import json
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_PATH = OUTPUT_DIR / "report_data.json"

HEADER_BG = "#1A2942"
MUTED = "#666666"
INK = "#222222"
ACCENT = "#1A2942"

CURRENCY_BY_CATEGORY = {"tw_etf": "NT$", "us_etf": "US$"}


def text(content: str, **kwargs) -> dict:
    return {"type": "text", "text": content, "wrap": True, **kwargs}


def separator() -> dict:
    return {"type": "separator", "margin": "lg"}


def section_title(label: str) -> dict:
    return text(label, weight="bold", size="md", margin="lg", color=INK)


def stock_metrics_line(e: dict) -> str:
    parts = []
    if e.get("returnOnEquity") is not None:
        parts.append(f"ROE {e['returnOnEquity'] * 100:.1f}%")
    margin = e.get("operatingMargins") if e.get("operatingMargins") is not None else e.get("grossMargins")
    if margin is not None:
        parts.append(f"營益率 {margin * 100:.1f}%")
    if e.get("freeCashflow") is not None:
        parts.append("FCF為正" if e["freeCashflow"] > 0 else "FCF為負")
    if e.get("dividendYield") is not None:
        parts.append(f"殖利率 {e['dividendYield'] * 100:.2f}%")
    return " ｜ ".join(parts) if parts else "（部分資料不足）"


def etf_metrics_line(e: dict, currency: str) -> str:
    parts = []
    if e.get("expense_ratio") is not None:
        parts.append(f"費用率 {e['expense_ratio'] * 100:.2f}%")
    if e.get("totalAssets") is not None:
        parts.append(f"規模 {currency}{e['totalAssets'] / 1e8:,.1f}億")
    return " ｜ ".join(parts) if parts else "（部分資料不足）"


def pick_row(rank: int, entry: dict, is_etf: bool, currency: str) -> dict:
    metrics_line = etf_metrics_line(entry, currency) if is_etf else stock_metrics_line(entry)
    return {
        "type": "box",
        "layout": "vertical",
        "margin": "sm",
        "paddingBottom": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    text(f"{rank}. {entry['symbol']} {entry['name']}", size="sm", weight="bold", color=INK, flex=4),
                ],
            },
            text(metrics_line, size="xxs", color=MUTED, margin="xs"),
        ],
    }


def category_block(category: dict) -> list:
    is_etf = category["key"].endswith("_etf")
    currency = CURRENCY_BY_CATEGORY.get(category["key"], "")
    blocks = [separator(), section_title(category["label"])]
    blocks += [pick_row(i + 1, entry, is_etf, currency) for i, entry in enumerate(category["picks"])]
    if category["note"]:
        blocks.append(text(category["note"], size="xs", color=INK, margin="sm"))
    return blocks


def build_bubble(data: dict) -> dict:
    body_contents = [
        text(data["summary"], size="sm", color=INK, wrap=True),
    ]
    for category in data["categories"]:
        body_contents += category_block(category)

    body_contents += [
        separator(),
        section_title("後續觀察"),
        text(data["outlook"], size="sm", color=INK, margin="sm"),
    ]

    body_contents += [
        {
            "type": "box",
            "layout": "vertical",
            "margin": "lg",
            "paddingAll": "10px",
            "backgroundColor": "#FFF4E5",
            "cornerRadius": "8px",
            "contents": [text(f"⚠️ {data['disclaimer']}", size="xxs", color="#92400E", wrap=True)],
        }
    ]

    return {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": HEADER_BG,
            "paddingAll": "16px",
            "contents": [
                text(data["title"], color="#FFFFFF", size="xl", weight="bold"),
                text(data["date"], color="#A8B8D0", size="xs", margin="xs"),
            ],
        },
        "body": {"type": "box", "layout": "vertical", "contents": body_contents},
    }


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("mode") != "structured":
        print("report_data.json is not in structured mode, skipping flex build")
        return

    flex_message = {
        "type": "flex",
        "altText": f"{data['title']}（{data['date']}）",
        "contents": build_bubble(data),
    }

    out_path = OUTPUT_DIR / "flex_message.json"
    out_path.write_text(json.dumps(flex_message, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
