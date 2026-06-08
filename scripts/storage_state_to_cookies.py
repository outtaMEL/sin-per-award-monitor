#!/usr/bin/env python3
"""把 storage_state.json 转成 Cookie 请求头（供 requests 模式使用）。"""

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "storage_state.json"


def cookie_header_from_state(path: Path) -> str:
    data = json.loads(path.read_text())
    cookies = data.get("cookies") or []
    pairs = [f"{c['name']}={c['value']}" for c in cookies if "seats.aero" in c.get("domain", "")]
    return "; ".join(pairs)


def main() -> None:
    if not STATE.exists():
        sys.exit("请先运行: python scripts/export_storage_state.py")

    header = cookie_header_from_state(STATE)
    b64 = base64.b64encode(header.encode()).decode()
    print("GitHub Secret: SEATS_AERO_COOKIES_B64")
    print(b64)


if __name__ == "__main__":
    main()
