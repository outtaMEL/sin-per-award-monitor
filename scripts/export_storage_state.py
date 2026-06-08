#!/usr/bin/env python3
"""从本机 .browser_data 导出 Playwright 登录态，供 GitHub Actions 使用。"""

from pathlib import Path
import base64
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BROWSER_DIR = ROOT / ".browser_data"
OUT = ROOT / "storage_state.json"


def main() -> None:
    if not BROWSER_DIR.exists():
        sys.exit("请先在本机运行过一次 monitor.py，生成 .browser_data 目录。")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://seats.aero/singapore", wait_until="domcontentloaded")
            page.wait_for_timeout(3_000)
            context.storage_state(path=str(OUT))
        finally:
            context.close()

    b64 = base64.b64encode(OUT.read_bytes()).decode()
    print(f"已导出: {OUT}")
    print()
    print("把下面整段复制到 GitHub → Settings → Secrets → PLAYWRIGHT_STORAGE_STATE")
    print("-" * 60)
    print(b64)
    print("-" * 60)


if __name__ == "__main__":
    main()
