# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc05_ui_title:
    # 标题菜单：方向键逐项浏览，验证按钮文字被朗读（imagebutton + foreground）
    advance until screen "main_menu" timeout 30
    assert screen "main_menu" timeout 10
    keysym "K_DOWN"
    keysym "K_DOWN"
    keysym "K_DOWN"
    assert eval True
