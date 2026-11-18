# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc09_load_screen:
    # 读档界面：标题 -> 读取游戏，方向键浏览槽位
    advance until screen "main_menu" timeout 30
    python:
        renpy.run(ShowMenu("load"))
    assert screen "load" timeout 20
    keysym "K_DOWN"
    keysym "K_RIGHT"
    assert eval True
