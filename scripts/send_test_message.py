"""Send a test payload to a locally running bridge.

Usage:
  python scripts/send_test_message.py --token replace-with-a-long-random-token
"""

from __future__ import annotations

import argparse
import json
import urllib.request


parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
parser.add_argument("--token", required=True)
args = parser.parse_args()

payload = {
    "clan_id": "demo-clan",
    "sender": "测试成员",
    "content": "这是一条链路测试消息",
    "source": "manual_test",
    "source_message_id": "manual-test-1",
}
request = urllib.request.Request(
    f"{args.url.rstrip('/')}/api/v1/messages",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "X-Collector-Token": args.token,
    },
    method="POST",
)
with urllib.request.urlopen(request) as response:
    print(response.status, response.read().decode("utf-8"))

