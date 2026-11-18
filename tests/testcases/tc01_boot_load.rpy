# -*- coding: utf-8 -*-

testsuite global:
    teardown:
        exit
testcase tc01_boot_load:
    # 启动与加载：模组已在真实游戏中完成接管
    advance until screen "main_menu" timeout 30
    assert screen "main_menu" timeout 10
    assert eval _MNE_PATCH_VERSION == "0.1.1.0"
    assert eval renpy.game.preferences.self_voicing is True
    assert eval getattr(renpy.config.tts_function, "__name__", "") == "_mne_tts_function"
    assert eval list(renpy.config.tts_voice_channels) == []
    assert eval MneHost.enabled is True
