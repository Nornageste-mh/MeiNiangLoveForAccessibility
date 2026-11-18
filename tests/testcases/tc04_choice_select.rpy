# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit

testcase tc04_choice_select:
    # 剧情选项：数字键 1 直接选择第一项；选择后选项界面消失、剧情继续
    advance until screen "main_menu" timeout 30
    run Start("scene_1_11")
    advance until screen "choice" timeout 120
    assert screen "choice" timeout 60
    keysym "K_DOWN"
    keysym "K_1"
    assert eval (renpy.get_screen("choice") is None) timeout 30
    advance repeat 4
    assert eval True
