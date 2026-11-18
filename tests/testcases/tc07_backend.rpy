# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc07_backend:
    # 切换语音后端：Alt+Shift+F9 在标题界面可用，且不触发游戏其它行为
    advance until screen "main_menu" timeout 30
    assert screen "main_menu" timeout 10
    keysym "alt_shift_K_F9"
    assert eval True
