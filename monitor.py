#!/usr/bin/env python3
"""监控 SIN→PER KrisFlyer Business Saver（seats.aero 免费页）。"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import os

from notifier import NotifyConfig, send_alert
from seats_scraper import fetch_krisflyer_business_saver, format_hits


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _notify_config() -> NotifyConfig:
    return NotifyConfig(
        pushplus_token=_env("PUSHPLUS_TOKEN") or None,
        serverchan_sendkey=_env("SERVERCHAN_SENDKEY") or None,
        wework_webhook=_env("WEWORK_WEBHOOK") or None,
        smtp_host=_env("SMTP_HOST") or None,
        smtp_port=int(_env("SMTP_PORT", "587")),
        smtp_user=_env("SMTP_USER") or None,
        smtp_password=_env("SMTP_PASSWORD") or None,
        email_from=_env("EMAIL_FROM") or None,
        email_to=_env("EMAIL_TO") or None,
        bot_token=_env("TELEGRAM_BOT_TOKEN") or None,
        chat_id=_env("TELEGRAM_CHAT_ID") or None,
    )


def _parse_date(value: str, name: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"{name} 格式应为 YYYY-MM-DD，当前: {value}") from exc


def run_once(state_file: Path) -> int:
    origin = _env("ORIGIN", "SIN").upper()
    destination = _env("DESTINATION", "PER").upper()
    date_start = _parse_date(_env("DATE_START", "2026-06-28"), "DATE_START")
    date_end = _parse_date(_env("DATE_END", "2026-07-06"), "DATE_END")
    max_miles = int(_env("MAX_BUSINESS_MILES", "70000"))
    browser_dir = Path(_env("BROWSER_DATA_DIR", ".browser_data"))
    headless = _env("HEADLESS", "false").lower() in {"1", "true", "yes"}

    notify = _notify_config()
    if not any(
        (
            notify.serverchan_sendkey,
            notify.pushplus_token,
            notify.wework_webhook,
            notify.smtp_host and notify.email_to,
            notify.bot_token,
        )
    ):
        print("警告：未配置任何通知渠道，仅打印到日志。")

    print(
        f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 查询 "
        f"{origin}→{destination} | {date_start} ~ {date_end} | "
        f"Business ≤ {max_miles:,} 里程"
    )

    hits = fetch_krisflyer_business_saver(
        origin=origin,
        destination=destination,
        date_start=date_start,
        date_end=date_end,
        max_business_miles=max_miles,
        browser_data_dir=browser_dir,
        headless=headless,
    )

    message = format_hits(hits)
    print(message)

    known: set[str] = set()
    if state_file.exists():
        try:
            known = set(json.loads(state_file.read_text()))
        except json.JSONDecodeError:
            known = set()

    current_keys = {f"{h.date}:{h.business_miles}" for h in hits}
    new_keys = current_keys - known

    if new_keys:
        new_hits = [h for h in hits if f"{h.date}:{h.business_miles}" in new_keys]
        alert = "新票提醒\n\n" + format_hits(new_hits)
        send_alert(alert, config=notify)
        state_file.write_text(json.dumps(sorted(current_keys), indent=2))
        return 1

    if not hits:
        print("（暂无票，继续监控）")

    return 0


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Seats.aero SIN-PER Business Saver 监控")
    parser.add_argument("--once", action="store_true", help="只运行一次")
    parser.add_argument("--state-file", default=".monitor_state.json", help="已通知记录")
    args = parser.parse_args()

    state_file = Path(args.state_file)
    poll_min = int(_env("POLL_INTERVAL_MIN", "3600"))
    poll_max = int(_env("POLL_INTERVAL_MAX", "5400"))

    if args.once:
        sys.exit(run_once(state_file))

    print("后台监控已启动。Ctrl+C 停止。")
    while True:
        try:
            run_once(state_file)
        except Exception as exc:  # noqa: BLE001
            err = f"监控出错: {exc}"
            print(err)
            if _env("NOTIFY_ON_ERROR", "true").lower() in {"1", "true", "yes"}:
                send_alert(err, config=_notify_config(), subject="积分票监控出错")

        wait = random.randint(poll_min, poll_max)
        print(f"下次检查约 {wait // 60} 分钟后…")
        time.sleep(wait)


if __name__ == "__main__":
    main()
