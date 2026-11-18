# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 00_contract（契约与基础设施）
#
# 这是补丁的地基：版本号、路径、日志、文本清理、状态。没有任何“玩家可见
# 的新东西”，也不注册任何按键——按键只在 05_repeat.rpy 里加两个朗读侧热键。
#
# 设计纪律（Framework/docs/交互形态纪律.md 第 0 条）：
#   · 玩家每一次界面操作都走游戏自己的输入/焦点/事件；
#   · 本补丁只“说话”，不接管输入、不画界面、不另建焦点；
#   · 删掉本目录，游戏行为与画面完全回到原样。
#
# ⚠ 为什么不是 `import os` 而是 `import os as _mne_os`：
#   renpy/common/00keymap.rpy 在 init -1600 里 `import os ... del os`，
#   会把 store 里的 os 名称删掉；我们的代码在运行期再引用 os 就会 NameError。
#   （forge 0.2.x 模板踩过这个坑：每句 SAPI 都静默失败。）
# ═══════════════════════════════════════════════════════════════════════════

init -1850 python:
    import os as _mne_os
    import sys as _mne_sys
    import time as _mne_time
    import traceback as _mne_traceback

    _MNE_PATCH_VERSION = "0.1.1.0"
    _MNE_GAME_NAME = u"男娘恋爱物语"
    _MNE_ENGINE = u"Ren'Py 8.5.2"

    # ── 路径 ────────────────────────────────────────────────────────────────
    def _mne_basedir():
        """游戏根目录（mei.exe 所在目录）。"""
        try:
            return renpy.config.basedir
        except Exception:
            return _mne_os.getcwd()

    def _mne_gamedir():
        """game 目录（.rpy/.rpa 所在目录）。"""
        try:
            return renpy.config.gamedir
        except Exception:
            return _mne_os.path.join(_mne_basedir(), "game")

    def _mne_env_path(name):
        v = _mne_os.environ.get(name)
        if not v:
            return None
        return v

    def _mne_log_path():
        # 自动化测试用 A11Y_TEST_LOG 指定独立文件；玩家默认写在游戏根目录。
        p = _mne_env_path("A11Y_TEST_LOG")
        if p:
            return p
        return _mne_os.path.join(_mne_basedir(), "a11y_speech.log")

    # ── 日志 ────────────────────────────────────────────────────────────────
    _mne_last_error = [u""]

    # 自动化测试要按 kind 统计（dialogue/choice/ui/repeat/system/error），
    # 玩家看的日志保持中文可读；两套 kind 在这里一一对应。
    _MNE_KIND_EN = {
        u"台词": u"dialogue",
        u"配音台词": u"dialogue",
        u"说话人": u"dialogue",
        u"选项": u"choice",
        u"选项组": u"choice",
        u"界面": u"ui",
        u"重读": u"repeat",
        u"朗读": u"speech",
        u"系统": u"system",
        u"接管": u"system",
        u"自检": u"system",
        u"后端": u"system",
        u"按键": u"system",
        u"启动": u"system",
        u"自语音": u"system",
        u"配置": u"system",
        u"错误": u"error",
    }

    def _mne_u(x):
        try:
            if isinstance(x, bytes):
                return x.decode("utf-8", "replace")
            return u"%s" % (x,)
        except Exception:
            return u"<unprintable>"

    def _mne_log(kind, msg):
        """一行一条，永远不抛异常（日志坏了不许影响游戏）。

        两种格式：
          · 玩家模式（默认）：[Mne朗读] +12.345s 台词|你好
          · 测试模式（设了 A11Y_TEST_LOG）：12.345<TAB>dialogue<TAB>你好
            —— 测试台按 TAB 拆列，第 2 列是 kind、第 3 列是文本。
        """
        try:
            text = _mne_u(msg).replace(u"\t", u" ").replace(u"\n", u" ").replace(u"\r", u" ")
            elapsed = _mne_time.time() - _MNE_T0
            if _mne_env_path("A11Y_TEST_LOG"):
                line = u"%.3f\t%s\t%s\n" % (
                    elapsed,
                    _MNE_KIND_EN.get(_mne_u(kind), u"system"),
                    text,
                )
            else:
                line = u"[Mne%s] +%.3fs %s\n" % (
                    _mne_u(kind),
                    elapsed,
                    text,
                )
            path = _mne_log_path()
            d = _mne_os.path.dirname(path)
            if d and not _mne_os.path.isdir(d):
                _mne_os.makedirs(d)
            with _mne_os.fdopen(_mne_os.open(path, _mne_os.O_WRONLY | _mne_os.O_CREAT | _mne_os.O_APPEND, 0o666), "a", encoding="utf-8", errors="replace") as f:
                f.write(line)
        except Exception:
            pass

    def _mne_log_exc(where):
        """把异常写进日志并返回文本（不打断游戏）。"""
        try:
            text = _mne_traceback.format_exc()
        except Exception:
            text = u"<no traceback>"
        _mne_last_error[0] = _mne_u("%s: %s" % (where, text[-400:]))
        _mne_log("错误", u"%s: %s" % (where, text.replace(u"\n", u" | ")[-600:]))
        return text

    _MNE_T0 = _mne_time.time()

    # ── 文本清理 ────────────────────────────────────────────────────────────
    import re as _mne_re

    _MNE_TAG_RE = _mne_re.compile(r"\{\{|\}\}|\{[^{}]*\}")
    _MNE_WS_RE = _mne_re.compile(r"[ \t\u3000]+")

    def _mne_clean(text):
        """把 Ren'Py 富文本标签/换行清成能朗读的一句话。

        只做“读之前清理”，不改游戏里的任何文本。
        """
        try:
            s = _mne_u(text)
        except Exception:
            return u""
        s = _MNE_TAG_RE.sub(u" ", s)
        s = s.replace(u"\r", u" ").replace(u"\n", u" ")
        s = _MNE_WS_RE.sub(u" ", s)
        s = s.replace(u"::", u":").replace(u": :", u":")
        s = s.strip()
        if len(s) > 1200:
            s = s[:1200]
        return s

    # ── 状态 ────────────────────────────────────────────────────────────────
    class _MneState(object):
        def __init__(self):
            self.enabled = True          # 朗读总开关（引擎自语音关闭时本补丁静默）
            self.backend_name = u""
            self.last_raw = u""          # 引擎给来的最后一段原文（去重用）
            self.last_text = u""         # 清理后、真正念出的最后一句（重读用）
            self.last_time = 0.0
            self.history = []            # 最近几句，供 Backspace 重读
            self.spoken_count = 0
            self.errors = []

        def remember(self, text):
            if not text:
                return
            self.last_text = text
            self.last_time = _mne_time.time()
            self.history.append(text)
            if len(self.history) > 30:
                del self.history[:-30]

        def repeat(self):
            if not self.history:
                return None
            return self.history[-1]

    MneHost = _MneState()

    # 旧契约兼容：早期手工试验可能残留 a11y_game 的调用，吞掉避免崩。
    class _MneLegacyBridge(object):
        def __getattr__(self, name):
            def _noop(*a, **kw):
                return None
            return _noop

    A11yHost = _MneLegacyBridge()
