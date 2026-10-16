"""Run a deliberate OneBot status check and optional real group-message send.

The script never sends a message unless --send is supplied. It is intended for
the operator's machine after the bridge and OneBot adapter are reachable.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx


def call(client: httpx.Client, base_url: str, token: str, action: str, payload: dict[str, object]) -> dict[str, object]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.post(f"{base_url.rstrip('/')}/{action}", json=payload, headers=headers)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("OneBot returned a non-object JSON response")
    if body.get("status") not in (None, "ok") or body.get("retcode") not in (None, 0):
        raise RuntimeError(f"OneBot application error: {body}")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("ONEBOT_URL"), help="OneBot HTTP base URL")
    parser.add_argument("--token", default=os.getenv("ONEBOT_ACCESS_TOKEN", ""))
    parser.add_argument("--group-id", default=os.getenv("QQ_GROUP_ID"))
    parser.add_argument("--send", action="store_true", help="send the test message after get_status")
    parser.add_argument("--message", default="部落聊天同步联调测试：收到请忽略")
    args = parser.parse_args()
    if not args.url:
        parser.error("--url or ONEBOT_URL is required")
    if args.send and not args.group_id:
        parser.error("--group-id or QQ_GROUP_ID is required when --send is used")

    try:
        with httpx.Client(timeout=10.0) as client:
            status = call(client, args.url, args.token, "get_status", {})
            print(f"get_status OK: {status.get('data', {})}")
            if args.send:
                group_id: object = int(args.group_id) if str(args.group_id).isdigit() else args.group_id
                result = call(
                    client,
                    args.url,
                    args.token,
                    "send_group_msg",
                    {"group_id": group_id, "message": args.message},
                )
                print(f"send_group_msg OK: {result.get('data', {})}")
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        print(f"OneBot smoke test FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
