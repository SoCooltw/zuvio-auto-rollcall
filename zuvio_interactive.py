#!/usr/bin/env python3
"""Beginner-friendly Chinese launcher for zuvio_rollcall.py."""

from __future__ import annotations

import getpass
import os
import sys
from typing import Any

import zuvio_rollcall


def ask_required(prompt: str, hidden: bool = False) -> str:
    while True:
        if hidden:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)
        value = value.strip()
        if value:
            return value
        print("這一欄必填，請再輸入一次。")


def ask_yes(prompt: str) -> bool:
    value = input(prompt).strip().lower()
    return value == "y"


def clear_credentials() -> None:
    os.environ.pop("ZUVIO_EMAIL", None)
    os.environ.pop("ZUVIO_PASSWORD", None)


def course_title(course: dict[str, Any]) -> str:
    name = str(course.get("course_name") or "(未命名課程)")
    teacher = str(course.get("teacher_name") or "-")
    semester = str(course.get("semester_name") or "").strip()
    if semester:
        return f"{name}｜老師：{teacher}｜學期：{semester}"
    return f"{name}｜老師：{teacher}"


def choose_course(courses: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    if not courses:
        raise zuvio_rollcall.CourseNotFound("目前課程列表是空的")

    visible_courses = courses
    while True:
        print()
        print("請選擇要自動點名的課程：")
        for index, course in enumerate(visible_courses, start=1):
            print(f"{index}. {course_title(course)}")

        value = input("請輸入課程編號；如果太多找不到，也可以輸入課程關鍵字搜尋：").strip()
        if not value:
            print("請輸入編號或關鍵字。")
            continue

        if value.isdigit():
            index = int(value)
            if 1 <= index <= len(visible_courses):
                selected = visible_courses[index - 1]
                course_id = str(selected.get("course_id") or "").strip()
                if course_id:
                    return course_id, selected
                print("這門課缺少課程代碼，請選其他課程。")
                continue
            print("編號超出範圍，請再輸入一次。")
            continue

        keyword = zuvio_rollcall.normalize_text(value)
        matches = [
            course
            for course in courses
            if keyword
            and keyword
            in " ".join(
                zuvio_rollcall.normalize_text(course.get(key))
                for key in ("course_name", "teacher_name", "semester_name")
            )
        ]
        if not matches:
            print("找不到符合的課程，請換個關鍵字。")
            continue
        visible_courses = matches


def main() -> int:
    print("Zuvio 自動點名助手")
    print("帳號密碼只會在這次執行中使用，不會存成檔案。")
    print()

    email = ask_required("請輸入 Zuvio 帳號/email：")
    password = ask_required("請輸入 Zuvio 密碼（畫面不會顯示）：", hidden=True)

    os.environ["ZUVIO_EMAIL"] = email
    os.environ["ZUVIO_PASSWORD"] = password

    if zuvio_rollcall.requests is None:
        print("缺少 Python 套件 requests，請先執行安裝套件。", file=sys.stderr)
        clear_credentials()
        return 70

    try:
        print()
        print("正在登入並讀取課程列表...")
        session = zuvio_rollcall.make_session()
        auth = zuvio_rollcall.login(session)
        courses = zuvio_rollcall.fetch_courses(session, auth)
        course_id, course = choose_course(courses)
        print(f"已選擇：{course_title(course)}")
    except zuvio_rollcall.LoginFailed as exc:
        print(f"登入失敗：{exc}", file=sys.stderr)
        clear_credentials()
        return 10
    except zuvio_rollcall.CourseNotFound as exc:
        print(f"找不到課程：{exc}", file=sys.stderr)
        clear_credentials()
        return 11
    except zuvio_rollcall.requests.RequestException as exc:
        print(f"讀取 Zuvio 失敗：{exc.__class__.__name__}", file=sys.stderr)
        clear_credentials()
        return 12
    except zuvio_rollcall.ZuvioError as exc:
        print(f"讀取課程失敗：{exc}", file=sys.stderr)
        clear_credentials()
        return 13

    args = ["zuvio_rollcall.py", "--course-id", course_id]

    print()
    until = input("如果想自動停止，可輸入時間，例如 19:55；直接按 Enter 會一直偵測：").strip()
    interval = input("幾秒檢查一次？直接按 Enter 預設 10 秒：").strip() or "10"
    args += ["--interval", interval, "--auto-submit", "--keep-watching"]
    if until:
        args += ["--until", until]

    use_debug = ask_yes("要開啟診斷模式嗎？下次測試建議輸入 y：")
    if use_debug:
        args += ["--debug"]

    use_gps = ask_yes("老師要求 GPS 嗎？輸入 y 才填 GPS，其他留空：")
    if use_gps:
        lat = ask_required("請輸入緯度 lat：")
        lng = ask_required("請輸入經度 lng：")
        args += ["--lat", lat, "--lng", lng]

    print()
    print("開始執行。請保持這個視窗開著。")
    print("要停止時，直接關閉視窗或按 Ctrl+C。")
    print()

    old_argv = sys.argv[:]
    try:
        sys.argv = args
        return zuvio_rollcall.main()
    finally:
        sys.argv = old_argv
        clear_credentials()


if __name__ == "__main__":
    raise SystemExit(main())
