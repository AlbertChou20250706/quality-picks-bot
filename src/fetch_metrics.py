"""Fetch real fundamental/ETF metrics from yfinance for the quality-picks
candidate pools. Never estimates or fabricates a number: any field yfinance
doesn't return for a ticker is stored as null, and screen_and_rank.py treats
a missing field as "no credit on that dimension" rather than guessing.
"""

import json
import pathlib

import yfinance as yf

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_PATH = BASE_DIR / "data" / "latest.json"

STOCK_FIELDS = [
    "returnOnEquity",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "freeCashflow",
    "debtToEquity",
    "currentRatio",
    "dividendYield",
    "payoutRatio",
    "trailingPE",
    "marketCap",
    "longName",
]

# yfinance has used different field names for ETF expense ratio across
# versions/tickers; try each and keep whichever one actually came back.
ETF_EXPENSE_RATIO_FIELDS = ["annualReportExpenseRatio", "netExpenseRatio", "expenseRatio"]
ETF_FIELDS = ["totalAssets", "trailingPE", "longName", "navPrice"]


def display_symbol(symbol: str) -> str:
    # LINE auto-linkifies "NNNN.TW" as if it were a domain name (.TW is a
    # real ccTLD), turning stock codes into broken clickable links.
    return symbol.removesuffix(".TW").removesuffix(".TWO")


def fetch_stock_metrics(symbol: str) -> dict:
    info = yf.Ticker(symbol).info or {}
    return {field: info.get(field) for field in STOCK_FIELDS}


def fetch_etf_metrics(symbol: str) -> dict:
    info = yf.Ticker(symbol).info or {}
    metrics = {field: info.get(field) for field in ETF_FIELDS}
    expense_values = [info.get(field) for field in ETF_EXPENSE_RATIO_FIELDS]
    metrics["expense_ratio"] = next((v for v in expense_values if v is not None), None)
    return metrics


def load_candidates(filename: str) -> list[dict]:
    return json.loads((CONFIG_DIR / filename).read_text(encoding="utf-8"))


def build_category(filename: str, is_etf: bool) -> list[dict]:
    entries = []
    for candidate in load_candidates(filename):
        symbol = candidate["symbol"]
        try:
            metrics = fetch_etf_metrics(symbol) if is_etf else fetch_stock_metrics(symbol)
        except Exception as exc:
            print(f"warning: skipping {symbol}: {exc}")
            continue
        entries.append({
            "symbol": display_symbol(symbol),
            "name": candidate["name"],
            **metrics,
        })
    return entries


def main() -> None:
    result = {
        "tw_stocks": build_category("candidates_tw_stocks.json", is_etf=False),
        "tw_etf": build_category("candidates_tw_etf.json", is_etf=True),
        "us_stocks": build_category("candidates_us_stocks.json", is_etf=False),
        "us_etf": build_category("candidates_us_etf.json", is_etf=True),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
