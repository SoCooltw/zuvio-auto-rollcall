#!/usr/bin/env python3
"""
Watch a Zuvio course rollcall page and optionally submit attendance.

Credentials are read from environment variables:
  ZUVIO_EMAIL
  ZUVIO_PASSWORD
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - depends on the user's local Python environment
    requests = None  # type: ignore[assignment]


BASE_URL = "https://irs.zuvio.com.tw"
LOGIN_URL = f"{BASE_URL}/irs/submitLogin"
HOME_URL = f"{BASE_URL}/"
COURSE_LIST_URL = f"{BASE_URL}/course/listStudentCurrentCourses"
MAKE_ROLLCALL_URL = f"{BASE_URL}/app_v2/makeRollcall"
DEBUG_DIR = Path(__file__).resolve().with_name("debug_logs")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class ZuvioError(Exception):
    """Base exception for expected Zuvio workflow failures."""


class LoginFailed(ZuvioError):
    """Raised when login succeeds at HTTP level but credentials are not accepted."""


class CourseNotFound(ZuvioError):
    """Raised when a course keyword does not match current courses."""


@dataclass
class AuthContext:
    user_id: str
    access_token: str


@dataclass
class PollResult:
    status: str
    rollcall_id: str | None = None
    message: str | None = None


@dataclass
class RollcallPage:
    rollcall_id: str | None
    status_code: int
    url: str
    html: str


def fixed_text(resp: requests.Response) -> str:
    """Decode Zuvio pages defensively when the response charset is wrong."""
    try:
        return resp.text.encode("latin1", "ignore").decode("utf-8", "ignore")
    except UnicodeError:
        return resp.text


def now_label() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise LoginFailed(f"Missing required environment variable: {name}")
    return value


def parse_until_today(until: str) -> dt.datetime:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", until.strip())
    if not match:
        raise ValueError("--until must use HH:MM format, for example 19:55")

    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("--until must be a valid 24-hour time")

    now = dt.datetime.now()
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    return session


def extract_auth(html: str) -> AuthContext:
    user_match = re.search(r"var\s+user_id\s*=\s*['\"]?([^'\";\s]+)", html)
    token_match = re.search(r"var\s+accessToken\s*=\s*['\"]([^'\"]+)['\"]", html)

    if not user_match or not token_match:
        raise LoginFailed("Login failed: could not find user_id/accessToken in Zuvio page")

    return AuthContext(user_id=user_match.group(1), access_token=token_match.group(1))


def login(session: requests.Session) -> AuthContext:
    email = require_env("ZUVIO_EMAIL")
    password = require_env("ZUVIO_PASSWORD")
    encoded_password = base64.b64encode(password.encode("utf-8")).decode("ascii")

    session.get(HOME_URL, timeout=20)
    resp = session.post(
        LOGIN_URL,
        data={
            "email": email,
            "password": password,
            "encoded_password": encoded_password,
            "current_language": "zh-TW",
            "back_url": "",
        },
        headers={
            "Referer": HOME_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=20,
    )
    resp.raise_for_status()

    html = fixed_text(resp)
    try:
        return extract_auth(html)
    except LoginFailed:
        home = session.get(HOME_URL, timeout=20)
        home.raise_for_status()
        return extract_auth(fixed_text(home))


def normalize_text(value: Any) -> str:
    return str(value or "").casefold().strip()


def fetch_courses(session: requests.Session, auth: AuthContext) -> list[dict[str, Any]]:
    resp = session.get(
        COURSE_LIST_URL,
        params={"user_id": auth.user_id, "accessToken": auth.access_token},
        headers={"Accept": "application/json, text/plain, */*"},
        timeout=20,
    )
    resp.raise_for_status()

    try:
        payload = resp.json()
    except ValueError as exc:
        raise ZuvioError("Could not parse course list response as JSON") from exc

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("courses", "data", "list", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if all(k in payload for k in ("course_id", "course_name")):
            return [payload]

    raise ZuvioError("Unexpected course list response format")


def find_course_id(courses: list[dict[str, Any]], keyword: str) -> tuple[str, dict[str, Any]]:
    needle = normalize_text(keyword)
    matches: list[dict[str, Any]] = []

    for course in courses:
        searchable = " ".join(
            normalize_text(course.get(key))
            for key in ("course_name", "teacher_name", "semester_name", "course_id")
        )
        if needle in searchable:
            matches.append(course)

    if not matches:
        raise CourseNotFound(f'No current course matched keyword "{keyword}"')

    if len(matches) > 1:
        print("找到多個可能課程，將使用第一個最先匹配的課程：")
        for course in matches[:5]:
            print(
                "  - "
                f'{course.get("course_name", "(未命名)")} '
                f'| 老師: {course.get("teacher_name", "-")} '
                f'| course_id: {course.get("course_id", "-")}'
            )

    selected = matches[0]
    course_id = str(selected.get("course_id") or "").strip()
    if not course_id:
        raise CourseNotFound("Matched course has no course_id")

    return course_id, selected


def extract_rollcall_id(html: str) -> str | None:
    match = re.search(
        r"var\s+rollcall_id\s*=\s*(?:['\"]([^'\"]*)['\"]|([^;\s]+))",
        html,
    )
    if not match:
        return None

    rollcall_id = (match.group(1) or match.group(2) or "").strip()
    if rollcall_id.lower() in {"null", "undefined"}:
        return None
    return rollcall_id or None


def fetch_rollcall_page(session: requests.Session, course_id: str) -> RollcallPage:
    url = f"{BASE_URL}/student5/irs/rollcall/{course_id}"
    resp = session.get(url, headers={"Referer": HOME_URL}, timeout=20)
    resp.raise_for_status()
    html = fixed_text(resp)
    return RollcallPage(
        rollcall_id=extract_rollcall_id(html),
        status_code=resp.status_code,
        url=resp.url,
        html=html,
    )


def fetch_rollcall_id(session: requests.Session, course_id: str) -> str | None:
    return fetch_rollcall_page(session, course_id).rollcall_id


def page_fingerprint(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8", "ignore")).hexdigest()


def redact_debug_html(html: str) -> str:
    redacted = re.sub(
        r"(accessToken\s*=\s*['\"])[^'\"]+",
        r"\1[redacted]",
        html,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"([?&]accessToken=)[^&\"'<>]+",
        r"\1[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"(user_id\s*=\s*['\"]?)[^'\";\s]+",
        r"\1[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted


def page_text_summary(html: str, max_length: int = 320) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length] or "(頁面沒有可讀文字)"


def save_debug_snapshot(course_id: str, page: RollcallPage) -> Path:
    DEBUG_DIR.mkdir(exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_course_id = re.sub(r"[^0-9A-Za-z_-]+", "_", course_id)[:80] or "unknown"
    path = DEBUG_DIR / f"rollcall_{safe_course_id}_{timestamp}.html"
    header = (
        "<!--\n"
        f"debug_time: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"status_code: {page.status_code}\n"
        f"url: {page.url}\n"
        "-->\n"
    )
    path.write_text(header + redact_debug_html(page.html), encoding="utf-8")
    return path


def validate_gps(lat: str | None, lng: str | None) -> tuple[str, str]:
    if not lat and not lng:
        return "", ""
    if not lat or not lng:
        raise ValueError("GPS requires both --lat and --lng")

    lat_num = float(lat)
    lng_num = float(lng)
    if not (-90 <= lat_num <= 90):
        raise ValueError("--lat must be between -90 and 90")
    if not (-180 <= lng_num <= 180):
        raise ValueError("--lng must be between -180 and 180")

    return str(lat_num), str(lng_num)


def submit_rollcall(
    session: requests.Session,
    auth: AuthContext,
    rollcall_id: str,
    lat: str,
    lng: str,
) -> PollResult:
    resp = session.post(
        MAKE_ROLLCALL_URL,
        data={
            "user_id": auth.user_id,
            "accessToken": auth.access_token,
            "rollcall_id": rollcall_id,
            "device": "WEB",
            "lat": lat,
            "lng": lng,
        },
        headers={
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{BASE_URL}/student5/irs/rollcall/",
        },
        timeout=20,
    )
    resp.raise_for_status()

    try:
        payload = resp.json()
    except ValueError:
        payload = {}

    status = payload.get("status")
    msg = str(payload.get("msg") or payload.get("message") or "").strip()
    msg_upper = msg.upper()

    if status is True or str(status).lower() == "true":
        return PollResult("success", rollcall_id, msg or "status=true")
    if msg_upper == "ROLLCALL IS ANSWERED":
        return PollResult("answered", rollcall_id, msg)
    if msg_upper == "LOSE THE GPS LOCATION":
        return PollResult("gps_required", rollcall_id, msg)
    if msg_upper == "ROLLCALL IS NOT ONAIR":
        return PollResult("not_onair", rollcall_id, msg)

    return PollResult("unknown_submit_response", rollcall_id, msg or str(payload)[:200])


def print_final(result: PollResult, course_id: str) -> int:
    if result.status == "success":
        print("結果：成功")
        return 0
    if result.status == "answered":
        print("結果：已簽到")
        return 0
    if result.status == "gps_required":
        print("結果：GPS 失敗，需手動使用手機完成")
        return 2
    if result.status == "not_open_until_deadline":
        print("結果：未開放直到截止")
        return 3
    if result.status == "found_without_submit":
        print("結果：偵測到點名開放，尚未自動送出")
        print(f"點名頁：{BASE_URL}/student5/irs/rollcall/{course_id}")
        return 0
    if result.status == "not_onair":
        print("結果：點名未開放或已關閉")
        return 4
    if result.status == "stopped":
        print("結果：已停止偵測")
        return 0

    print(f"結果：未知狀態 - {result.message or result.status}")
    return 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor a Zuvio rollcall page and optionally submit attendance."
    )
    course_group = parser.add_mutually_exclusive_group(required=True)
    course_group.add_argument("--course-id", help="Zuvio course_id, for example 1474194")
    course_group.add_argument("--course-keyword", help="Keyword to match current course name")
    parser.add_argument(
        "--until",
        help="Optional deadline today in HH:MM. If omitted, keep watching until the window is closed.",
    )
    parser.add_argument("--interval", type=int, default=10, help="Polling interval seconds, default 10")
    parser.add_argument(
        "--auto-submit",
        action="store_true",
        help="Submit attendance immediately when rollcall_id is found",
    )
    parser.add_argument(
        "--keep-watching",
        action="store_true",
        help="After handling one rollcall, keep watching for later rollcalls.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print diagnostics and save rollcall page snapshots when no rollcall_id is found.",
    )
    parser.add_argument("--lat", help="Optional latitude, only send when both lat/lng are valid")
    parser.add_argument("--lng", help="Optional longitude, only send when both lat/lng are valid")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if requests is None:
        print("缺少 Python 套件 requests，請先執行：pip install requests", file=sys.stderr)
        return 70

    if args.interval < 1:
        parser.error("--interval must be at least 1 second")

    try:
        deadline = parse_until_today(args.until) if args.until else None
        lat, lng = validate_gps(args.lat, args.lng)
    except ValueError as exc:
        print(f"參數錯誤：{exc}", file=sys.stderr)
        return 64

    session = make_session()

    try:
        print("正在登入 Zuvio...")
        auth = login(session)
        print("登入成功")

        if args.course_id:
            course_id = str(args.course_id).strip()
        else:
            print("正在查詢目前課程...")
            courses = fetch_courses(session, auth)
            course_id, course = find_course_id(courses, args.course_keyword)
            print(
                "已選擇課程："
                f'{course.get("course_name", "(未命名)")} '
                f'| 老師: {course.get("teacher_name", "-")} '
                f"| course_id: {course_id}"
            )

        if deadline and deadline < dt.datetime.now():
            print(f"提醒：截止時間 {args.until} 已早於現在，仍會檢查一次後結束。")

        rollcall_url = f"{BASE_URL}/student5/irs/rollcall/{course_id}"
        if deadline:
            print(
                f"開始監看 course_id={course_id}，截止 {deadline.strftime('%H:%M')}，"
                f"每 {args.interval} 秒檢查一次。"
            )
        else:
            print(
                f"開始監看 course_id={course_id}，每 {args.interval} 秒檢查一次。"
                "要停止時直接關閉這個視窗，或按 Ctrl+C。"
            )

        last_status = "尚未檢查"
        last_debug_fingerprint: str | None = None
        handled_rollcall_ids: set[str] = set()
        while True:
            try:
                page = fetch_rollcall_page(session, course_id)
                rollcall_id = page.rollcall_id
            except requests.RequestException as exc:
                last_status = f"讀取失敗：{exc.__class__.__name__}"
                print(f"[{now_label()}] {last_status}")
            else:
                if not rollcall_id:
                    last_status = "未開放"
                    print(f"[{now_label()}] 未開放")
                    if args.debug:
                        fingerprint = page_fingerprint(page.html)
                        print(f"debug: HTTP {page.status_code} | {page.url}")
                        if fingerprint != last_debug_fingerprint:
                            snapshot_path = save_debug_snapshot(course_id, page)
                            print(f"debug: 已保存頁面快照 {snapshot_path}")
                            print(f"debug: 頁面文字摘要：{page_text_summary(page.html)}")
                            last_debug_fingerprint = fingerprint
                elif rollcall_id in handled_rollcall_ids:
                    last_status = f"已處理過這次點名，繼續等待下一次"
                    print(f"[{now_label()}] 已處理過，等待下一次點名")
                elif not args.auto_submit:
                    print(f"[{now_label()}] 已開放，rollcall_id={rollcall_id}")
                    print("未加 --auto-submit，因此不會自動送出。")
                    print(f"點名頁：{rollcall_url}")
                    return print_final(PollResult("found_without_submit", rollcall_id), course_id)
                else:
                    print(f"[{now_label()}] 已開放，正在送出簽到...")
                    result = submit_rollcall(session, auth, rollcall_id, lat, lng)
                    if result.message:
                        print(f"Zuvio 回應：{result.message}")
                    handled_rollcall_ids.add(rollcall_id)

                    if not args.keep_watching or result.status == "gps_required":
                        return print_final(result, course_id)

                    if result.status in {"success", "answered"}:
                        print("這次點名已處理，繼續偵測下一次點名。")
                    elif result.status == "not_onair":
                        print("這次點名目前不可送出，繼續偵測下一次狀態。")
                    else:
                        print("已收到回應，繼續偵測下一次點名。")

            if deadline and dt.datetime.now() >= deadline:
                print(f"最後狀態：{last_status}")
                return print_final(PollResult("not_open_until_deadline", message=last_status), course_id)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n已停止偵測")
        return 0
    except LoginFailed as exc:
        print(f"結果：登入失敗 - {exc}", file=sys.stderr)
        return 10
    except CourseNotFound as exc:
        print(f"結果：找不到課程 - {exc}", file=sys.stderr)
        return 11
    except requests.RequestException as exc:
        print(f"網路或伺服器錯誤：{exc.__class__.__name__}", file=sys.stderr)
        return 12
    except ZuvioError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 13


if __name__ == "__main__":
    raise SystemExit(main())
