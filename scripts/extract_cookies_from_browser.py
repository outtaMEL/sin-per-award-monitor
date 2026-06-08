#!/usr/bin/env python3
"""从本机 .browser_data 提取 seats.aero Cookie，供 GitHub Actions 使用。"""

from __future__ import annotations

import base64
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COOKIES_DB = ROOT / ".browser_data" / "Default" / "Cookies"


def main() -> None:
    if not COOKIES_DB.exists():
        sys.exit("未找到 .browser_data，请先运行: python monitor.py --once")

    conn = sqlite3.connect(f"file:{COOKIES_DB}?mode=ro", uri=True)
    rows = conn.execute(
        """
        SELECT name, value
        FROM cookies
        WHERE host_key LIKE '%seats.aero%'
        """
    ).fetchall()
    conn.close()

    if not rows:
        sys.exit("未找到 seats.aero Cookie，请用浏览器打开 seats.aero/singapore 后再试。")

    cookie_header = "; ".join(f"{name}={value}" for name, value in rows)
    print(f"已提取 {len(rows)} 个 Cookie")
    print()
    print("把下面整段复制到 GitHub Secret: SEATS_AERO_COOKIES")
    print("-" * 60)
    print(cookie_header)
    print("-" * 60)
    print()
    b64 = base64.b64encode(cookie_header.encode()).decode()
    print("或复制 Base64 到 Secret: SEATS_AERO_COOKIES_B64")
    print(b64[:80] + "...")


if __name__ == "__main__":
    main()
