"""Push the generated quality-picks report to one or more LINE targets (users
or groups). Sends output/flex_message.json as a Flex Message if present,
otherwise falls back to output/report.txt as plain text.
"""

import json
import os
import pathlib

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_REPORT_PATH = OUTPUT_DIR / "report.txt"
FLEX_PATH = OUTPUT_DIR / "flex_message.json"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def push(token: str, target_id: str, message: dict) -> None:
    response = requests.post(
        LINE_PUSH_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": target_id, "messages": [message]},
        timeout=30,
    )
    response.raise_for_status()


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]
    if not target_ids:
        raise RuntimeError("LINE_PUSH_TARGET_IDS is empty")

    if FLEX_PATH.exists():
        message = json.loads(FLEX_PATH.read_text(encoding="utf-8"))
    else:
        message = {"type": "text", "text": DEFAULT_REPORT_PATH.read_text(encoding="utf-8")}

    for target_id in target_ids:
        push(token, target_id, message)
        print(f"sent to {target_id}")


if __name__ == "__main__":
    main()
