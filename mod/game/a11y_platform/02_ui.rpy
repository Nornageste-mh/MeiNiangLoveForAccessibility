# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 02_ui（补上引擎“读不到”的焦点控件）
#
# 问题：本作的按钮大量是 imagebutton，标题字既不是按钮的子节点、也没写 alt：
#   · my_button（选项/确认/设置…）把文字放在 `foreground=Text(...)` 里；
#   · title_button（标题菜单）把文字放在与 button 平级的 text 里；
#   · ImageButton.visit() 只遍历图片和 child，Button._tts_all 只念子节点，
#     所以引擎自语音对这些按钮是**静默**的（behavior.py:1263 / :1199）。
#
# 做法：包一层引擎自己的焦点朗读出口 `renpy.display.tts.displayable()`：
#   1) 先让引擎照常念（它念得出来就什么都不做）；
#   2) 只有“焦点确实变了、引擎却没念出任何新东西”时，才从**当前焦点控件**
#      上取游戏自己的文字（foreground Text / 子 Text / 同级 Text）念出来。
#
# 这仍然是“引擎焦点事件驱动 + 读游戏自己的文本”：
#   · 不扫屏（X4）、不自维护焦点表（X2）、不拦按键、不画任何东西（X5）；
#   · 焦点在哪念哪，焦点由游戏自己设（set_focused → displayable）。
# ═══════════════════════════════════════════════════════════════════════════

init -1700 python:
    try:
        from renpy.display.text import Text as _MneTextType
    except Exception:
        _MneTextType = None

    try:
        from renpy.display.behavior import Button as _MneButtonType
    except Exception:
        _MneButtonType = None

    _mne_orig_displayable = renpy.display.tts.displayable
    _mne_ui_state = {"widget": None, "time": 0.0}

    def _mne_is_text(d):
        if d is None or _MneTextType is None:
            return False
        try:
            return isinstance(d, _MneTextType)
        except Exception:
            return False

    def _mne_is_button(d):
        if d is None or _MneButtonType is None:
            return False
        try:
            return isinstance(d, _MneButtonType)
        except Exception:
            return False

    def _mne_disp_text(d):
        """只从 Text 控件取字；其它控件一律返回空（避免把按钮的子图片当文字）。"""
        if not _mne_is_text(d):
            return u""
        try:
            s = d._tts_all(raw=False)
        except Exception:
            try:
                s = d._tts(raw=False)
            except Exception:
                return u""
        return _mne_clean(s)

    def _mne_label_of(d, depth=0):
        """当前焦点控件上“玩家看得见的字”。只读游戏自己的文本控件。"""
        if d is None or depth > 3:
            return u""
        s = _mne_disp_text(d)
        if s:
            return s
        # my_button 模式：caption 在 style.foreground 的 Text 里
        for prop in (u"foreground", u"background", u"child"):
            try:
                v = getattr(d.style, prop)
            except Exception:
                v = None
            s = _mne_disp_text(v)
            if s:
                return s
        # 子控件里的 Text
        try:
            kids = list(d.visit())
        except Exception:
            kids = []
        for k in kids:
            s = _mne_disp_text(k)
            if s:
                return s
        # 最后：同级兄弟里的 Text（title_button 的高亮按钮与文字平级）
        try:
            parent = getattr(d, "parent", None)
            if parent is not None and depth < 2:
                for sib in getattr(parent, "children", []) or []:
                    if sib is d:
                        continue
                    s = _mne_disp_text(sib)
                    if s:
                        return s
        except Exception:
            pass
        # 再兜底：沿引擎显示树向上找最近容器，读它自己的可见文本
        try:
            s = _mne_container_text(d)
            if s:
                return s
        except Exception:
            pass
        return u""

    def _mne_find_parent(node, target, depth=0):
        """在引擎自己的显示树里找“含 target 的最近容器”（只走 visit()，不做几何猜测）。"""
        if depth > 14 or node is None:
            return None
        try:
            kids = list(node.visit())
        except Exception:
            return None
        for ch in kids:
            if ch is target:
                return node
            r = _mne_find_parent(ch, target, depth + 1)
            if r is not None:
                return r
        return None

    def _mne_container_text(d):
        """title_button 式布局：按钮自己没字，字在与它平级的 Text 里。
        向上取最近容器的可见文本（仍是游戏屏幕上的 Text）。"""
        try:
            root = renpy.display.tts.root
        except Exception:
            return u""
        if root is None or d is root:
            return u""
        try:
            parent = _mne_find_parent(root, d)
        except Exception:
            return u""
        for _i in range(2):
            if parent is None:
                return u""
            try:
                txt = _mne_clean(parent._tts_all(raw=False))
            except Exception:
                txt = u""
            if txt:
                return txt
            try:
                parent = _mne_find_parent(root, parent)
            except Exception:
                return u""
        return u""

    def _mne_choice_entries():
        """当前 choice 界面的选项（游戏自己的 caption / action）。"""
        out = []
        try:
            sc = renpy.get_screen("choice")
            if sc is None:
                return out
            items = (sc.scope or {}).get("items") or []
            for it in items:
                cap = getattr(it, "caption", None)
                if cap is None:
                    cap = getattr(it, "kwargs", {}).get("caption", u"")
                out.append((_mne_clean(cap), getattr(it, "action", None)))
        except Exception:
            _mne_log_exc("ui.choice_entries")
        return out

    def _mne_choice_index(text):
        """把焦点控件的文字对回选项序号（读的时候带编号，1–9 才好按）。"""
        try:
            for i, (cap, _act) in enumerate(_mne_choice_entries()):
                if cap and cap == text:
                    return i + 1
        except Exception:
            pass
        return 0

    def _mne_ui_supplement(d):
        """引擎这次没念出新东西时，补念当前焦点控件。"""
        if not MneHost.enabled:
            return
        try:
            mode = renpy.game.preferences.self_voicing
        except Exception:
            return
        if not (mode is True or mode == 1):
            return          # 玩家关掉自语音 / 用剪贴板/调试模式：补丁闭嘴
        try:
            if renpy.config.skipping:
                return
        except Exception:
            pass

        try:
            focused = renpy.display.focus.get_focused()
        except Exception:
            focused = None
        if not _mne_is_button(focused):
            return          # 只管按钮：say/drag/input 等由引擎自己负责

        # 同一个焦点控件连续补念会刷屏；但玩家离开后再回来必须能再听到。
        key = id(focused)
        now = _mne_time.time()
        if _mne_ui_state["widget"] == key and (now - _mne_ui_state["time"]) < 2.0:
            return

        text = _mne_label_of(focused)
        _mne_ui_state["widget"] = key
        _mne_ui_state["time"] = now
        if not text:
            return

        idx = _mne_choice_index(text)
        if idx:
            text = u"%d、%s" % (idx, text)
        MneSpeech.speak(text, _mne_kind(), dedupe=0.4)

    def _mne_ui_displayable(d):
        """引擎的焦点朗读出口包装（TTSRoot 异常必须原样上抛）。"""
        before = getattr(renpy.display.tts, "last", None)

        rv = _mne_orig_displayable(d)
        try:
            after = getattr(renpy.display.tts, "last", None)
            # 引擎念出空串（imagebutton 的典型情况）也算“没念”，要补。
            if (not after) or (after == before):
                _mne_ui_supplement(d)
        except Exception:
            _mne_log_exc("ui.wrap")
        return rv

    try:
        renpy.display.tts.displayable = _mne_ui_displayable
        _mne_log(u"接管", u"焦点朗读出口 → 补丁补充（只补引擎没念到的按钮文字）")
    except Exception:
        _mne_log_exc("ui.takeover")

    # ── 台词精确朗读 ─────────────────────────────────────────────────────────
    # 引擎对 SayBehavior 的处理是抛 TTSRoot，让 tts 改读“场景根”，于是 say 界面
    # 上的装饰文本（本作每句前有一行日期 Text，快进时还有“快进中 ▸”）会被一起
    # 念出来（实测：'2023年: 我叫李飞…'）。这里改成读 SayBehavior 自己持有的
    # 台词 Text 本体 + say 屏幕的 who —— 仍然是游戏自己维护的可见文本，
    # 不碰输入、不改屏幕、不新增元素。
    try:
        _mne_orig_say_tts = renpy.display.behavior.SayBehavior._tts_all

        def _mne_say_tts(self, raw):
            try:
                parts = []
                for t in (getattr(self, "text_tuple", None) or ()):
                    s = _mne_disp_text(t)
                    if s:
                        parts.append(s)
                what = u" ".join(parts)
                if what:
                    who = u""
                    try:
                        sc = renpy.get_screen("say")
                        if sc is not None:
                            w = (sc.scope or {}).get("who")
                            if isinstance(w, str):
                                who = _mne_clean(w)
                    except Exception:
                        who = u""
                    if who:

                        return who + u": " + what
                    return what
            except Exception:
                pass
            return _mne_orig_say_tts(self, raw)

        renpy.display.behavior.SayBehavior._tts_all = _mne_say_tts
        _mne_log(u"接管", u"台词朗读出口 → 只读台词本体（不念 say 界面装饰文本）")
    except Exception:
        _mne_log_exc("ui.say_tts")

    # ── 按钮文字朗读 ─────────────────────────────────────────────────────────
    # 本作的按钮几乎都是 imagebutton + foreground=Text（设置单选项、标题菜单、
    # 存读档槽……）。引擎的 Button._tts_all 只遍历子节点，读不到 foreground 的
    # 文字，只能拿到动作的 alt（实测读到 "display 已选中" 这种）。这里把按钮
    # 自己画出来的文字接上，再保留引擎的“已选中/激活”状态词。
    try:
        _mne_orig_btn_tts = renpy.display.behavior.Button._tts_all
        _MNE_STATE_WORDS = (
            "selected", "activate", "deactivate", "increase", "decrease",
        )

        def _mne_btn_tts(self, raw):
            rv = u""
            try:
                rv = _mne_orig_btn_tts(self, raw) or u""
            except Exception:
                rv = u""
            label = u""
            try:
                label = _mne_label_of(self)
            except Exception:
                label = u""
            if not label:
                return rv
            if label in rv:
                return rv
            # 引擎已经念了“状态词”就保留，别丢“已选中”这类反馈。
            suf = u""
            for w in _MNE_STATE_WORDS:
                if rv.endswith(w) or ((u" " + w) in rv):
                    suf = u" " + w
                    break
            out = (label + suf).strip()
            return out or rv

        renpy.display.behavior.Button._tts_all = _mne_btn_tts
        _mne_log(u"接管", u"按钮朗读出口 → 补上 imagebutton 画出来的文字")
    except Exception:
        _mne_log_exc("ui.btn_tts")

