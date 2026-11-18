# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 05_repeat（朗读侧热键）
#
# 第 0 条纪律的 A 类路线只允许两种补丁热键：**重读最近一句**、**切换语音后端**。
# 这里都按引擎自己的做法实现：config.keymap 加事件名 + config.underlay 加
# renpy.Keymap —— 与引擎绑定 V / Shift+A 的方式完全一样（00keymap.rpy:436-466）。
#
#   Backspace        重读：台词→重读上一句；选项界面→把整组选项连编号念一遍
#   Alt+Shift+F9     切换朗读后端（NVDA / 引擎 SAPI / 日志）
#
# ⚠ 挂载时机：00keymap.rpy 在 **init -1100** 里 `config.underlay = [_default_keymap]`
#   是整体赋值，任何更早的 append 都会被覆盖。所以本文件拆成两段：
#   init -1400 只定义键名与处理函数；init -1000 才真正把 Keymap 挂进去。
#
# 不新增：任何“进入/退出无障碍模式”的键、Tab、F1–F12、Enter/Space/方向键。
# ═══════════════════════════════════════════════════════════════════════════

init -1400 python:
    # 只加我们自己的 keymap 事件，不覆盖引擎任何键位。
    if "mne_repeat_line" not in config.keymap:
        config.keymap["mne_repeat_line"] = [ "K_BACKSPACE" ]
    if "mne_cycle_backend" not in config.keymap:
        config.keymap["mne_cycle_backend"] = [ "alt_shift_K_F9" ]

    def _mne_speech_on():
        """玩家用 V 键关掉引擎自语音时，补丁也闭嘴（可摘除）。"""
        try:
            mode = renpy.game.preferences.self_voicing
            return bool(mode) and mode not in ("clipboard", "debug")
        except Exception:
            return False

    def _mne_choice_captions():
        try:
            return [cap for (cap, _act) in _mne_choice_entries() if cap]
        except Exception:
            return []

    def _mne_do_repeat():
        if not _mne_speech_on():
            return None
        # 输入框里 Backspace 是“删除字符”，必须让位给游戏自己的输入处理。
        try:
            if isinstance(renpy.display.focus.get_focused(),
                          renpy.display.behavior.Input):
                return None
        except Exception:
            pass
        try:
            caps = _mne_choice_captions()
            if caps:
                parts = [u"%d、%s" % (i + 1, t) for i, t in enumerate(caps[:9])]
                MneSpeech.speak(
                    u"选项：%s" % u"；".join(parts), u"选项组", dedupe=0.0
                )
            else:
                MneSpeech.repeat()
        except Exception:
            _mne_log_exc("repeat")
        return None

    def _mne_do_cycle():
        if not _mne_speech_on():
            return None
        try:
            MneSpeech.cycle()
        except Exception:
            _mne_log_exc("cycle")
        return None

init -1000 python:
    # 引擎在 init -1100 已把 config.underlay 赋值为 [_default_keymap]，这里追加。
    _mne_keymap = renpy.Keymap(
        mne_repeat_line=_mne_do_repeat,
        mne_cycle_backend=_mne_do_cycle,
    )
    try:
        config.underlay.append(_mne_keymap)
        _mne_log(u"按键", u"已绑定 Backspace=重读 / Alt+Shift+F9=切换后端（朗读侧热键）")
    except Exception:
        _mne_log_exc("keymap.install")
