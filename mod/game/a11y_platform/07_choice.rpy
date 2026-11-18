# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 07_choice（剧情选项按数字键直接选）
#
# Framework/docs/操作逻辑公约.md 的语义动作表：**1–9 只要选项完整播报且编号**，
# 玩家按数字键就选中对应选项。这是玩家本来就会的操作，不是“补丁专属模式键”。
#
# 实现方式（激活三级里的第 1 级：直接调用游戏自己的动作）：
#   · 从游戏自己的 choice 界面里取 items（就是 screen choice 的 items 参数）；
#   · 按数字键调用该项自己的 action —— 与玩家用方向键聚焦后按回车走的是
#     同一个 action（Return），不伪造输入、不抢焦点；
#   · 没有 choice 界面时处理函数返回 None，事件原样放行（不影响游戏与输入框）。
#
# 挂载时机同 05_repeat：init -1000（引擎 init -1100 赋完 config.underlay 之后）。
# ═══════════════════════════════════════════════════════════════════════════

init -1400 python:
    _MNE_CHOICE_NUMS = []
    for _mne_n in range(1, 10):
        _mne_name = "mne_choice_%d" % _mne_n
        if _mne_name not in config.keymap:
            config.keymap[_mne_name] = [
                "K_%d" % _mne_n,
                "K_KP%d" % _mne_n,
            ]
        _MNE_CHOICE_NUMS.append(_mne_n)

    def _mne_do_pick(n):
        if not _mne_speech_on():
            return None
        try:
            entries = _mne_choice_entries()
        except Exception:
            entries = []
        if not entries or n > len(entries):
            return None        # 不是选项界面 / 没有第 n 项：放行给游戏
        cap, act = entries[n - 1]
        if act is None:
            return None
        if cap:
            MneSpeech.speak(u"%d、%s" % (n, cap), u"选项", dedupe=0.0, interrupt=True)
        try:
            return renpy.run(act)
        except Exception:
            _mne_log_exc("choice.pick")
            return None

init -1000 python:
    try:
        _mne_choice_keymap = renpy.Keymap(
            **dict(
                ("mne_choice_%d" % _n, (lambda n: (lambda: _mne_do_pick(n)))(_n))
                for _n in _MNE_CHOICE_NUMS
            )
        )
        config.underlay.append(_mne_choice_keymap)
        _mne_log(u"按键", u"已绑定数字键 1–9=直接选择剧情选项（仅选项界面生效）")
    except Exception:
        _mne_log_exc("choice.keymap")
