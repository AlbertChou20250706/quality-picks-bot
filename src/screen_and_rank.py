"""Rank each candidate pool by real, code-computed metrics (never model-
guessed) and keep the top 3 per category. A candidate missing a metric gets
no credit on that dimension rather than an assumed/average value — the
screen should never reward missing data.

Stock score = 0.35*ROE + 0.25*margin + 0.20*positive-FCF + 0.20*dividend
quality. ETF score = 0.5*AUM + 0.5*(1 - expense ratio). Weights reflect the
user's stated priorities (profitability/moat first, cost/scale for ETFs)
without pretending to reproduce a full institutional model.
"""

import json
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "latest.json"
OUTPUT_PATH = BASE_DIR / "data" / "top_picks.json"

TOP_N = 3


def normalize(values: list) -> list:
    present = [v for v in values if v is not None]
    if not present:
        return [None] * len(values)
    lo, hi = min(present), max(present)
    if hi == lo:
        return [0.5 if v is not None else None for v in values]
    return [(v - lo) / (hi - lo) if v is not None else None for v in values]


def weighted_score(components: list) -> list:
    """components: list of (normalized_values, weight) pairs, all same length.
    A None in normalized_values contributes 0 (no credit), not an estimate."""
    n = len(components[0][0])
    scores = [0.0] * n
    for values, weight in components:
        for i, v in enumerate(values):
            scores[i] += (v or 0.0) * weight
    return scores


def score_stocks(entries: list[dict]) -> list[dict]:
    roe = normalize([e.get("returnOnEquity") for e in entries])
    margin = normalize([e.get("operatingMargins") or e.get("grossMargins") for e in entries])
    fcf_positive_only = [v if (v is not None and v > 0) else None for v in
                          (e.get("freeCashflow") for e in entries)]
    fcf = normalize(fcf_positive_only)

    div_quality = []
    for e in entries:
        yld, payout = e.get("dividendYield"), e.get("payoutRatio")
        if yld and payout is not None and 0 < payout < 0.9:
            div_quality.append(1.0)
        elif yld:
            div_quality.append(0.5)
        else:
            div_quality.append(0.0)

    scores = weighted_score([
        (roe, 0.35),
        (margin, 0.25),
        (fcf, 0.20),
        (div_quality, 0.20),
    ])
    for e, s in zip(entries, scores):
        e["score"] = round(s, 4)
    return sorted(entries, key=lambda e: e["score"], reverse=True)


def score_etfs(entries: list[dict]) -> list[dict]:
    aum = normalize([e.get("totalAssets") for e in entries])
    expense = normalize([e.get("expense_ratio") for e in entries])
    expense_inverted = [(1 - v) if v is not None else None for v in expense]

    scores = weighted_score([
        (aum, 0.5),
        (expense_inverted, 0.5),
    ])
    for e, s in zip(entries, scores):
        e["score"] = round(s, 4)
    return sorted(entries, key=lambda e: e["score"], reverse=True)


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    result = {
        "tw_stocks": score_stocks(data["tw_stocks"])[:TOP_N],
        "tw_etf": score_etfs(data["tw_etf"])[:TOP_N],
        "us_stocks": score_stocks(data["us_stocks"])[:TOP_N],
        "us_etf": score_etfs(data["us_etf"])[:TOP_N],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
