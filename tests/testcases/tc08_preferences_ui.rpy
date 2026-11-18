# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit

testcase tc08_preferences_ui:
    # 设置界面：标题 -> 设置，方向键浏览设置项，Esc 回标题
    advance until screen "main_menu" timeout 30
    python:
        renpy.run(ShowMenu("preferences"))
    assert screen "preferences" timeout 20
    keysym "K_DOWN"
    keysym "K_DOWN"
    keysym "K_ESCAPE"
    assert screen "main_menu" timeout 20
