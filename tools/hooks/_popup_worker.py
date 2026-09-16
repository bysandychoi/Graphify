#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notify_stop_popup.py가 분리 실행하는 실제 팝업 표시 프로세스.

MessageBoxW가 사용자가 닫을 때까지 대기하므로, Stop 훅 본체와 분리된
프로세스에서 이 스크립트만 대기하게 한다. sys.argv로 메시지를 받아
커맨드라인에 파이썬 코드를 직접 이어붙이는 방식(따옴표 escape 위험)을
피한다.
"""
import ctypes
import sys

MB_OK_ICONINFORMATION = 0x40


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "Claude 작업 완료!"
    ctypes.windll.user32.MessageBoxW(0, message, "Claude Code", MB_OK_ICONINFORMATION)


if __name__ == "__main__":
    main()
