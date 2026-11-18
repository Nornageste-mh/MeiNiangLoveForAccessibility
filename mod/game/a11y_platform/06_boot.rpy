# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 06_boot（首次启动默认开启、自检、迟到读屏重探）
#
# 这里解决“像游戏本来就有无障碍”最关键的一步：**默认就是开的，但玩家说了算**。
#   · 第一次装补丁后启动：把引擎自己的 preferences.self_voicing 打开（等于玩家
#     按了一次 V 键，走的是游戏原生设置，会存进游戏的 persistent）；
#   · 玩家之后按 V 关掉：我们记下“玩家自己决定过”，以后再也不动它；
#   · 自动化测试（A11Y_TEST_LOG）：强制打开，保证朗读管线真的被走了一遍。
#
# 挂点说明：Ren'Py 8.5.2 没有 config.start_callbacks，只有
#   · config.display_start_callbacks（core.py:978 显示初始化完成时，早于主菜单）
#   · config.interact_callbacks / config.periodic_callbacks（core.py:3062 每帧）
# 所以用 display_start_callbacks 做一次性初始化，periodic_callbacks 做读屏重探。
#
# 不做的事：不新增设置界面、不弹提示、不显示“补丁已启用”。
# ═══════════════════════════════════════════════════════════════════════════

init 0 python:
    _MNE_PERSIST_KEY = "mne_a11y_seen"
    _MNE_BOOTED = [False]

    def _mne_read_persist(key, default=None):
        try:
            return getattr(renpy.game.persistent, key)
        except Exception:
            return default

    def _mne_write_persist(key, value):
        try:
            setattr(renpy.game.persistent, key, value)
        except Exception:
            _mne_log_exc("persist.write")

    def _mne_probe():
        info = []
        try:
            info.append(u"engine=%s" % (renpy.version_tuple,))
        except Exception:
            pass
        try:
            info.append(u"python=%s" % _mne_u(_mne_sys.version.split()[0]))
        except Exception:
            pass
        info.append(u"basedir=%s" % _mne_basedir())
        try:
            info.append(u"self_voicing=%r" % (renpy.game.preferences.self_voicing,))
        except Exception:
            pass
        try:
            info.append(u"tts_function=%s" % _mne_u(getattr(renpy.config.tts_function, "__name__", "?")))
        except Exception:
            pass
        try:
            info.append(u"tts_voice_channels=%r" % (list(renpy.config.tts_voice_channels),))
        except Exception:
            pass
        try:
            info.append(u"keymap_repeat=%r" % (list(renpy.config.keymap.get("mne_repeat_line", [])),))
        except Exception:
            pass
        _mne_log(u"自检", u" ".join(info))

    def _mne_boot():
        if _MNE_BOOTED[0]:
            return
        _MNE_BOOTED[0] = True

        _mne_probe()

        testing = bool(_mne_env_path("A11Y_TEST_LOG"))
        seen = _mne_read_persist(_MNE_PERSIST_KEY, False)
        try:
            cur = renpy.game.preferences.self_voicing
        except Exception:
            cur = False

        if testing:
            if not cur:
                renpy.game.preferences.self_voicing = True
                _mne_log(u"自语音", u"测试模式：已打开引擎自语音")
        elif not seen:
            # 第一次用补丁：默认开启（等价玩家按一次 V）。
            if not cur:
                renpy.game.preferences.self_voicing = True
                _mne_log(u"自语音", u"首次启动：默认打开引擎自语音（玩家可按 V 关闭）")
            _mne_write_persist(_MNE_PERSIST_KEY, True)
        else:
            _mne_log(u"自语音", u"玩家已有选择：%r（不再自动改动）" % (cur,))

        _mne_log(u"启动", u"补丁 %s 已加载" % _MNE_PATCH_VERSION)

    # 迟到的读屏：玩家先开游戏、后开读屏，5 秒内自动接上（NVDA 优先，其次争渡）。
    #
    # 只升不降：已经在用 NVDA 就不再轮询；在吵架（争渡）的档位上发现 NVDA 起来了
    # 就升级到 NVDA；还在 SAPI/日志档位时，两种读屏谁先起来就用谁。
    _mne_backend_state = {"t": 0.0, "tries": 0}

    # 后端优先级（与 _MneSpeech.start()/cycle() 的选择链一致）。
    _MNE_BACKEND_RANK = {u"日志": 0, u"引擎SAPI": 1, u"争渡读屏": 2, u"NVDA": 3}

    def _mne_backend_rank(backend):
        try:
            return _MNE_BACKEND_RANK.get(getattr(backend, "name", u""), 0)
        except Exception:
            return 0

    def _mne_switch_backend(backend):
        MneSpeech.active = backend
        MneHost.backend_name = backend.name
        _mne_log(u"后端", u"检测到 %s 已启动，自动切换到 %s" % (backend.name, backend.name))
        MneSpeech.speak(u"朗读已切换到 %s" % backend.name, u"系统", dedupe=0)

    def _mne_poll_backends():
        if _mne_env_path("A11Y_TEST_LOG"):
            # 测试模式：整个测试期间保证引擎自语音是开的（有脚本/存档会改偏好）。
            try:
                if not renpy.game.preferences.self_voicing:
                    renpy.game.preferences.self_voicing = True
            except Exception:
                pass
            return
        if not _MNE_BOOTED[0]:
            return
        now = _mne_time.time()
        if now - _mne_backend_state["t"] < 5.0:
            return
        _mne_backend_state["t"] = now
        try:
            cur = _mne_backend_rank(MneSpeech.active)
            if cur >= _MNE_BACKEND_RANK[u"NVDA"]:
                return
            _mne_backend_state["tries"] += 1

            # 1) NVDA：dll 在，但 NVDA 可能刚启动，需要重新 testIfRunning。
            if not MneSpeech.nvda.available():
                MneSpeech.nvda._load()
            if MneSpeech.nvda.available() and _mne_backend_rank(MneSpeech.nvda) > cur:
                _mne_switch_backend(MneSpeech.nvda)
                return

            # 2) 争渡：available() 里会用 2 秒 TTL 重新问 GetSpeakState()，
            #    所以读屏晚启动也能被发现。
            if MneSpeech.zdsr.available() and _mne_backend_rank(MneSpeech.zdsr) > cur:
                _mne_switch_backend(MneSpeech.zdsr)
                return
        except Exception:
            _mne_log_exc("backend.poll")

    try:
        config.display_start_callbacks.append(_mne_boot)
    except Exception:
        _mne_log_exc("boot.display_start")

    try:
        config.periodic_callbacks.append(_mne_poll_backends)
    except Exception:
        _mne_log_exc("boot.periodic")
