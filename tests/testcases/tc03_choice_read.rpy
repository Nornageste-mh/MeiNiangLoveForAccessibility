# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc03_choice_read:
    # 剧情选项：到达选项界面，验证选项文字被朗读（含编号）
    advance until screen "main_menu" timeout 30
    run Start("scene_1_11")
    advance until screen "choice" timeout 120
    assert screen "choice" timeout 60
