#!/usr/bin/env python3
"""Beginner-friendly Chinese launcher for zuvio_rollcall.py."""

from __future__ import annotations

import getpass
import os
import sys

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


def main() -> int:
    print("Zuvio 自動點名助手")
    print("帳號密碼只會在這次執行中使用，不會存成檔案。")
    print()

    email = ask_required("請輸入 Zuvio 帳號/email：")
    password = ask_required("請輸入 Zuvio 密碼（畫面不會顯示）：", hidden=True)

    print()
    print("課程指定方式：")
    print("1. 輸入課程關鍵字，例如：英文（二）")
    print("2. 輸入 course_id，例如：1474194")
    mode = input("請輸入 1 或 2（直接按 Enter 預設 1）：").strip() or "1"

    args = ["zuvio_rollcall.py"]
    if mode == "2":
        course_id = ask_required("請輸入 course_id：")
        args += ["--course-id", course_id]
    else:
        keyword = ask_required("請輸入課程關鍵字：")
        args += ["--course-keyword", keyword]

    print()
    until = input("如果想自動停止，可輸入時間，例如 19:55；直接按 Enter 會一直偵測：").strip()
    interval = input("幾秒檢查一次？直接按 Enter 預設 10 秒：").strip() or "10"
    args += ["--interval", interval, "--auto-submit", "--keep-watching"]
    if until:
        args += ["--until", until]

    use_gps = ask_yes("老師要求 GPS 嗎？輸入 y 才填 GPS，其他留空：")
    if use_gps:
        lat = ask_required("請輸入緯度 lat：")
        lng = ask_required("請輸入經度 lng：")
        args += ["--lat", lat, "--lng", lng]

    os.environ["ZUVIO_EMAIL"] = email
    os.environ["ZUVIO_PASSWORD"] = password

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
        os.environ.pop("ZUVIO_EMAIL", None)
        os.environ.pop("ZUVIO_PASSWORD", None)


if __name__ == "__main__":
    raise SystemExit(main())
