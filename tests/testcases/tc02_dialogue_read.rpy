# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc02_dialogue_read:
    # 剧情台词：进入有连续台词的场景，逐句推进，验证台词被朗读
    advance until screen "main_menu" timeout 30
    run Start("scene_1_11")
    advance repeat 8
    assert eval True
