"""One-off utility: push an arbitrary text message to every configured LINE
target (reuses the same LINE_CHANNEL_ACCESS_TOKEN / LINE_PUSH_TARGET_IDS
secrets as the monthly quality-picks report). Message text comes from the
MESSAGE_TEXT environment variable, not a template-interpolated shell string,
so arbitrary/untrusted characters in it can't break out into the shell.
"""

import os

import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]
    if not target_ids:
        raise RuntimeError("LINE_PUSH_TARGET_IDS is empty")

    text = os.environ["MESSAGE_TEXT"]
    if not text.strip():
        raise RuntimeError("MESSAGE_TEXT is empty")

    for target_id in target_ids:
        response = requests.post(
            LINE_PUSH_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": target_id, "messages": [{"type": "text", "text": text}]},
            timeout=30,
        )
        response.raise_for_status()
        print(f"sent to {target_id}")


if __name__ == "__main__":
    main()
