# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc10_quit_confirm:
    # 退出确认框：弹出确认、朗读确认项、Esc 退回标题
    advance until screen "main_menu" timeout 30
    python:
        renpy.run(Quit(confirm=True))
    assert screen "confirm" timeout 20
    keysym "K_ESCAPE"
    assert screen "main_menu" timeout 20
