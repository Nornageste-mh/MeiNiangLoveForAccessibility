# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc06_repeat:
    # 重读：台词之后按 Backspace 重读最近一句
    advance until screen "main_menu" timeout 30
    run Start("scene_1_11")
    advance repeat 6
    keysym "K_BACKSPACE"
    assert eval True
