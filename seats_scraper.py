"""Seats.aero KrisFlyer explore page scraper (Playwright + internal API)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import BrowserContext, Page, sync_playwright

SINGAPORE_EXPLORE_URL = "https://seats.aero/singapore"
API_PATH = "/_api/availability_table_modern_ss"

# seats.aero explore API 常用区域，合并查询以尽量覆盖 SIN→PER
ORIGIN_REGIONS = ("Asia", "Southeast Asia", "Oceania", "Anywhere")
DEST_REGIONS = ("Oceania", "Asia", "Southeast Asia", "Anywhere")

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class AwardHit:
    date: str
    origin: str
    destination: str
    business_miles: int
    seats: int | None
    direct: bool | None
    last_seen_hours: int | None
    raw: dict[str, Any]


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        return n if n > 0 else None
    text = re.sub(r"[^\d]", "", str(value))
    return int(text) if text else None


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True"):
        return True
    if value in (0, "0", "false", "False"):
        return False
    return None


def _in_date_range(day: str, start: date, end: date) -> bool:
    try:
        d = datetime.strptime(day[:10], "%Y-%m-%d").date()
    except ValueError:
        return False
    return start <= d <= end


def _row_to_hit(row: dict[str, Any], origin: str, destination: str) -> AwardHit | None:
    row_origin = str(row.get("oa", "")).upper()
    row_dest = str(row.get("da", "")).upper()
    if row_origin != origin or row_dest != destination:
        return None

    business_miles = _parse_int(row.get("jm"))
    if not business_miles:
        return None

    return AwardHit(
        date=str(row.get("dt", ""))[:10],
        origin=row_origin,
        destination=row_dest,
        business_miles=business_miles,
        seats=_parse_int(row.get("js")),
        direct=_parse_bool(row.get("jd")),
        last_seen_hours=_parse_int(row.get("lsh")),
        raw=row,
    )


def _build_api_url(
    *,
    start: int,
    length: int,
    origin_region: str,
    destination_region: str,
    filter_origin: str,
    filter_destination: str,
) -> str:
    params = {
        "draw": "1",
        "start": str(start),
        "length": str(length),
        "source": "singapore",
        "origin_region": origin_region,
        "destination_region": destination_region,
        "filter_origin_airports": filter_origin,
        "filter_destination_airports": filter_destination,
        "filter_cabin": "business",
        "min_seats": "1",
        "direct_only": "false",
        "giga": "false",
        "ex": "false",
    }
    return f"https://seats.aero{API_PATH}?{urlencode(params)}"


def _fetch_api_page(page: Page, url: str) -> dict[str, Any]:
    return page.evaluate(
        """async (apiUrl) => {
            const res = await fetch(apiUrl, { credentials: 'include' });
            if (!res.ok) {
                throw new Error(`API ${res.status}: ${await res.text()}`);
            }
            return await res.json();
        }""",
        url,
    )


def _ensure_cloudflare_cleared(page: Page, timeout_ms: int = 90_000) -> None:
    page.goto(SINGAPORE_EXPLORE_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        title = page.title().lower()
        if "just a moment" in title or "attention required" in title:
            page.wait_for_timeout(2_000)
            continue
        if "explore singapore" in title:
            return
        page.wait_for_timeout(1_000)
    raise RuntimeError("无法通过 Cloudflare 验证，请设 HEADLESS=false 手动完成一次验证")


def _collect_region(
    fetch_json,
    *,
    origin: str,
    destination: str,
    date_start: date,
    date_end: date,
    max_business_miles: int,
    origin_region: str,
    destination_region: str,
) -> list[AwardHit]:
    hits: dict[str, AwardHit] = {}
    page_size = 500
    start = 0

    while True:
        url = _build_api_url(
            start=start,
            length=page_size,
            origin_region=origin_region,
            destination_region=destination_region,
            filter_origin=origin,
            filter_destination=destination,
        )
        payload = fetch_json(url)
        rows = payload.get("data") or []

        for row in rows:
            hit = _row_to_hit(row, origin, destination)
            if not hit:
                continue
            if not _in_date_range(hit.date, date_start, date_end):
                continue
            if hit.business_miles > max_business_miles:
                continue
            hits[f"{hit.date}:{hit.business_miles}"] = hit

        filtered_total = int(payload.get("recordsFiltered") or 0)
        start += page_size
        if start >= filtered_total or not rows:
            break

    return list(hits.values())


def _collect_all_regions(
    fetch_json,
    *,
    origin: str,
    destination: str,
    date_start: date,
    date_end: date,
    max_business_miles: int,
) -> list[AwardHit]:
    all_hits: dict[str, AwardHit] = {}
    for o_region in ORIGIN_REGIONS:
        for d_region in DEST_REGIONS:
            region_hits = _collect_region(
                fetch_json,
                origin=origin.upper(),
                destination=destination.upper(),
                date_start=date_start,
                date_end=date_end,
                max_business_miles=max_business_miles,
                origin_region=o_region,
                destination_region=d_region,
            )
            for hit in region_hits:
                all_hits[f"{hit.date}:{hit.business_miles}"] = hit
    return sorted(all_hits.values(), key=lambda h: h.date)


def fetch_krisflyer_business_saver(
    *,
    origin: str,
    destination: str,
    date_start: date,
    date_end: date,
    max_business_miles: int,
    browser_data_dir: Path,
    headless: bool,
) -> list[AwardHit]:
    """通过 Playwright 会话调用 seats.aero 内部 API，返回 Business Saver 命中。"""
    browser_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context: BrowserContext = p.chromium.launch_persistent_context(
            user_data_dir=str(browser_data_dir),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            user_agent=_USER_AGENT,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            _ensure_cloudflare_cleared(page)
            fetch_json = lambda url: _fetch_api_page(page, url)  # noqa: E731
            return _collect_all_regions(
                fetch_json,
                origin=origin,
                destination=destination,
                date_start=date_start,
                date_end=date_end,
                max_business_miles=max_business_miles,
            )
        finally:
            context.close()


def format_hits(hits: list[AwardHit]) -> str:
    if not hits:
        return "未发现符合条件的 Business Saver 票。"
    lines = ["发现 KrisFlyer Business Saver 余票："]
    for h in hits:
        seats = f"{h.seats} 座" if h.seats else "座位未知"
        direct = "直飞" if h.direct else "含转机" if h.direct is False else "直飞未知"
        seen = f"{h.last_seen_hours}h 前" if h.last_seen_hours is not None else "未知"
        lines.append(
            f"• {h.date} {h.origin}→{h.destination} | "
            f"{h.business_miles:,} 里程 | {seats} | {direct} | 数据 {seen}"
        )
    lines.append("请尽快登录新航官网核实并手动预订。")
    return "\n".join(lines)
