# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 01_speech（把引擎自己的朗读出口接到 NVDA）
#
# 路线：**用引擎自己的 self-voicing 通道**。
#   Ren'Py 本来就有无障碍朗读：焦点变化时 displayable() 把控件文本丢进
#   tts 队列，每帧 tick() 交给 config.tts_function 出声；say 台词则通过
#   SayBehavior 抛 TTSRoot 改读场景根（所以“谁+台词”也会进队列）。
#   也就是说：朗读的触发、去重、队列、与配音/快进的配合全是官方的。
#   我们只做一件游戏自己没做的事：**把最后那个“出声”换成一个认识 NVDA 的**。
#
# 为什么不是“补丁自己找台词”：
#   · 自己读屏＝第 0 条纪律 X4（每帧扫界面猜台词）与 X2（自维护焦点表）；
#   · 自己拦截 say 会绕过游戏的快进/自动/回滚/回看逻辑，玩家会感知到“外挂感”。
#
# 兜底链：
#   1) NVDA（nvdaControllerClient64.dll，玩家开着 NVDA 时最自然）；
#   2) 争渡读屏（ZDSRAPI_x64.dll，中文读屏用户量最大的一支，判据已验证、出声未验证）；
#   3) 引擎自带 SAPI（config.tts_function 的原始实现，走 say.vbs）；
#   4) 只写日志（无声环境/自动化测试，A11Y_TEST_LOG 时强制走这条）。
# ═══════════════════════════════════════════════════════════════════════════

init -1800 python:
    import ctypes as _mne_ctypes
    import subprocess as _mne_subprocess
    import re as _mne_re

    _MNE_TTS_PREF = _mne_os.environ.get("A11Y_TTS_PREF", u"auto").strip().lower()
    _MNE_TEST_LOG = _mne_env_path("A11Y_TEST_LOG")

    # 引擎自带的出声实现（默认 wscript say.vbs → SAPI）。先存下来做兜底。
    _mne_engine_tts = getattr(renpy.config, "tts_function", None)

    # ── 引擎的“配音守卫”必须让开 ────────────────────────────────────────────
    # tts.py:419-421 的规则是：config.tts_voice_channels 里任一频道正在响，
    # displayable() 就直接 return（整段不朗读）。本作 283 句台词全有配音，而且
    # preferences.voice_sustain 默认 True 会让上一句配音“挂着”，所以只开自语音
    # 根本念不出东西。
    #
    # 我们清空它，改成在 _mne_tts_function 里逐句判断“这一句到底有没有配音”：
    #   · 有配音 → 只放游戏配音（不再叠读台词，也不再单独念角色名）；
    #   · 没配音 → 正常朗读台词。
    # 这样既没有“双读”，也没有“越用越哑”。
    _mne_orig_voice_channels = list(getattr(renpy.config, "tts_voice_channels", []) or [])
    try:
        renpy.config.tts_voice_channels = []
        _mne_log(
            u"自语音",
            u"已关闭引擎配音守卫 tts_voice_channels（原 %r → []），改按句判断配音"
            % (_mne_orig_voice_channels,),
        )
    except Exception:
        _mne_log_exc("tts.voice_channels")

    # ── 引擎内建的英文词换成中文 ─────────────────────────────────────────────
    # Ren'Py 在按钮/滑条上会自己补 "selected"、"activate"、"bar" 等英文单词
    # （behavior.py:2546/2563/2568/2611，_tts_all 里还有 " selected"），
    # 中文界面里读出来很突兀。
    #
    # 注意：引擎的 config.tts_substitutions 是 **[(正则或字符串, 替换), ...] 列表**，
    # 而且只在 tts.init()（启动早期）编译一次；我们的 init 晚于它，改配置不会再
    # 生效。所以这里不碰引擎的替换表，只在我们自己的出声口做一次替换——反正
    # 所有要念的文本最后都经过 _mne_tts_function。
    _MNE_SUBS = {
        u"selected": u"已选中",
        u"bar": u"滑块",
        u"activate": u"激活",
        u"deactivate": u"取消选中",
        u"increase": u"增加",
        u"decrease": u"减少",
    }
    _MNE_SUBS_RE = []
    for _k, _v in _MNE_SUBS.items():
        try:
            _MNE_SUBS_RE.append((_mne_re.compile(r"\b" + _mne_re.escape(_k) + r"\b",
                                                 _mne_re.IGNORECASE), _v))
        except Exception:
            _mne_log_exc("tts.substitutions")

    def _mne_apply_subs(text):
        out = text or u""
        for _pat, _rep in _MNE_SUBS_RE:
            try:
                out = _pat.sub(_rep, out)
            except Exception:
                pass
        return out

    class _MneLogBackend(object):
        """不出声，只写日志：无声环境与自动化测试用。"""

        name = u"日志"

        def available(self):
            return True

        def speak(self, text):
            return True

        def stop(self):
            pass

    class _MneNvdaBackend(object):
        """NVDA 控制器客户端（LGPL-2.1，未修改，随补丁放在游戏根目录）。"""

        name = u"NVDA"

        def __init__(self):
            self.dll = None
            self.reason = u""
            self._load()

        def _candidates(self):
            bits = 64 if _mne_sys.maxsize > 2 ** 32 else 32
            leaf = "nvdaControllerClient%d.dll" % bits
            dirs = []
            for d in (_mne_gamedir(), _mne_basedir()):
                if d:
                    dirs.append(d)
            try:
                dirs.append(_mne_os.getcwd())
            except Exception:
                pass
            out = []
            for d in dirs:
                out.append(_mne_os.path.join(d, leaf))
            out.append(leaf)
            return out

        def _load(self):
            if not _mne_sys.platform.startswith("win"):
                self.reason = u"非 Windows"
                return
            for path in self._candidates():
                try:
                    dll = _mne_ctypes.WinDLL(path)
                    dll.nvdaController_testIfRunning.restype = _mne_ctypes.c_long
                    dll.nvdaController_speakText.argtypes = [_mne_ctypes.c_wchar_p]
                    dll.nvdaController_speakText.restype = _mne_ctypes.c_long
                    dll.nvdaController_cancelSpeech.restype = _mne_ctypes.c_long
                    rc = dll.nvdaController_testIfRunning()
                    if rc == 0:
                        self.dll = dll
                        self.reason = u"testIfRunning=0 dll=%s" % path
                        return
                    self.reason = u"testIfRunning=%s dll=%s（NVDA 未运行？）" % (rc, path)
                except Exception as exc:
                    self.reason = u"%s (%s)" % (path, _mne_u(exc))
            self.dll = None

        def available(self):
            return self.dll is not None

        def speak(self, text):
            if self.dll is None:
                return False
            try:
                rc = self.dll.nvdaController_speakText(_mne_u(text))
                if rc != 0:
                    _mne_log("错误", u"NVDA speakText rc=%s" % rc)
                    return False
                return True
            except Exception:
                _mne_log_exc("nvda.speak")
                return False

        def stop(self):
            if self.dll is not None:
                try:
                    self.dll.nvdaController_cancelSpeech()
                except Exception:
                    _mne_log_exc("nvda.cancel")

    class _MneEngineBackend(object):
        """引擎自带 SAPI 兜底：直接调用我们保存的原始 config.tts_function。"""

        name = u"引擎SAPI"

        def available(self):
            return _mne_engine_tts is not None

        def speak(self, text):
            try:
                _mne_engine_tts(text)
                return True
            except Exception:
                _mne_log_exc("engine_tts")
                return False

        def stop(self):
            try:
                renpy.display.tts.stop_tts()
            except Exception:
                pass

    # ── ZDSR（争渡读屏）后端 ──────────────────────────────────────────────────
    #
    # 接口依据：官方 ZDSRAPI.txt（随争渡分发，本机逐字读过）。只用四个导出：
    #
    #   int  WINAPI InitTTS(int type, const WCHAR* channelName, BOOL bKeyDownInterrupt)
    #   int  WINAPI Speak(const WCHAR* text, BOOL bInterrupt)
    #   int  WINAPI GetSpeakState()
    #   void WINAPI StopSpeak()
    #
    # 导出名与签名不是猜的 —— 来自 A11yFramework 的 A11yZdsrBackend
    # （已在本机跑通、PE 导出表核对过）。
    #
    # ★ 可用性判据只有一条：GetSpeakState() ∈ {3, 4} ★
    #   InitTTS 返回 0 只表示"版本对得上"，读屏没跑时也返回 0；
    #   Speak 返回 0 不表示成功（未授权时也返回 0）。
    #   唯一能回答"读屏在不在、能不能收"的是 GetSpeakState()：
    #     3 正在朗读 / 4 没有朗读   → 可用
    #     1 / 2 / 8 / 9             → 不可用，顺降下一级
    #
    # ★ 版本不匹配（InitTTS 返回 1）时自动换下一份候选 ★
    #   包里那份可能过期、安装目录那份可能坏掉 —— 两份互为兜底。
    #
    # ★ dll 查找顺序（A11Y_ZDSR_DIR 可钉死）★
    #   1. 注册表 争渡读屏 → InstallLocation（HKLM+HKCU × 32/64 视图）
    #   2. 默认位置 %ProgramFiles(x86)%\zdsr\zdsr 等
    #   3. 补丁目录（game\ 和 basedir）
    #   4. 游戏当前目录
    #
    # ⚠ 状态：**判据已验证，出声未验证**。本机实测 GetSpeakState 返回 4
    #   （读屏在跑），available() 返回 True，但"争渡在跑时真的念出游戏台词"
    #   尚未实机试听。按纪律不标"已验证可用"。

    class _MneZdSrBackend(object):
        """争渡读屏（ZDSR）的 ctypes 封装。上游 Zdsr.cs 的对应物。"""

        name = u"争渡读屏"

        #: dll 文件名，64 位在前。本进程是 64 位，加载 32 位那份会失败。
        DLL_NAMES = ("ZDSRAPI_x64.dll", "ZDSRAPI.dll")

        #: 注册表"卸载"项路径。
        UNINSTALL_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

        #: 默认安装位置（环境变量拼，不写死盘符）。
        DEFAULT_SUBDIRS = (
            ("ProgramFiles(x86)", ("zdsr", "zdsr")),
            ("ProgramFiles", ("zdsr", "zdsr")),
            ("ProgramFiles(x86)", ("zdsr", "zdcloud")),
        )

        #: 环境变量：钉死搜索目录（多个用 ; 分隔）。
        DIR_ENV = "A11Y_ZDSR_DIR"

        #: GetSpeakState 返回值 → 人话。
        STATE_WHY = {
            1: u"版本不匹配",
            2: u"争渡读屏没有运行或没有授权",
            8: u"命令没有成功送达",
            9: u"独立通道尚未就绪",
        }

        #: InitTTS 返回值 → 人话。
        INIT_WHY = {1: u"版本不匹配"}

        #: 状态查询缓存（秒）。
        STATE_TTL = 2.0

        #: 握手失败后重试间隔（秒）。限流：读屏没开时不刷屏 InitTTS。
        INIT_RETRY_INTERVAL = 30.0

        def __init__(self):
            self._lib = None
            self.reason = u"未初始化"
            self._tried = False
            self._load_error = None
            self.loaded_from = None
            self._has_braille = False
            self._handshake_ok = False
            self._init_tried_at = None
            self._state = None
            self._state_at = None
            self._state_error = None
            self._ok = False
            self._paths = []
            self._index = 0
            self._mismatch = []

        # ------------------------------------------------ 注册表
        @staticmethod
        def _dirs_from_registry_entries(entries):
            """把 (DisplayName, InstallLocation) 表变成候选目录。本体排前面。"""
            exact, loose = [], []
            for disp, loc in (entries or ()):
                try:
                    d = (disp or "").strip()
                    p = (loc or "").strip().strip('"').rstrip("\\/")
                    if not d or not p:
                        continue
                    (exact if u"争渡" in d else loose).append(p)
                except Exception:
                    continue
            return exact + loose

        @staticmethod
        def _reg_value(key, winreg, name):
            try:
                v, _t = winreg.QueryValueEx(key, name)
                return v if isinstance(v, str) else None
            except Exception:
                return None

        @staticmethod
        def _read_uninstall_branch(winreg, hive, view):
            out = []
            try:
                key = winreg.OpenKey(hive, _MneZdSrBackend.UNINSTALL_KEY, 0,
                                     winreg.KEY_READ | view)
            except Exception:
                return out
            try:
                n = 0
                while True:
                    try:
                        name = winreg.EnumKey(key, n)
                    except OSError:
                        break
                    n += 1
                    sub = None
                    try:
                        sub = winreg.OpenKey(key, name)
                        disp = _MneZdSrBackend._reg_value(sub, winreg, "DisplayName")
                        loc = _MneZdSrBackend._reg_value(sub, winreg, "InstallLocation")
                        if not disp or not loc:
                            continue
                        if (u"争渡" not in disp) and ("zdsr" not in disp.lower()):
                            continue
                        out.append((disp, loc))
                    except Exception:
                        continue
                    finally:
                        if sub is not None:
                            try:
                                winreg.CloseKey(sub)
                            except Exception:
                                pass
            finally:
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass
            return out

        @staticmethod
        def _registry_uninstall_entries():
            out = []
            try:
                import winreg
            except Exception:
                return out
            try:
                views = [0]
                for name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
                    v = getattr(winreg, name, None)
                    if v:
                        views.append(v)
                for hive in (getattr(winreg, "HKEY_LOCAL_MACHINE", None),
                             getattr(winreg, "HKEY_CURRENT_USER", None)):
                    if hive is None:
                        continue
                    for view in views:
                        out.extend(_MneZdSrBackend._read_uninstall_branch(
                            winreg, hive, view))
            except Exception:
                return out
            return out

        @staticmethod
        def _registry_dirs():
            return _MneZdSrBackend._dirs_from_registry_entries(
                _MneZdSrBackend._registry_uninstall_entries())

        @staticmethod
        def _default_dirs():
            out = []
            for ev, parts in _MneZdSrBackend.DEFAULT_SUBDIRS:
                base = None
                try:
                    base = _mne_os.environ.get(ev)
                except Exception:
                    base = None
                if not base and ev == "ProgramFiles(x86)":
                    base = r"C:\Program Files (x86)"
                if not base and ev == "ProgramFiles":
                    base = r"C:\Program Files"
                if base:
                    out.append(_mne_os.path.join(base, *parts))
            return out

        # ------------------------------------------------ 候选目录
        @staticmethod
        def _candidate_dirs():
            pinned = None
            try:
                pinned = _mne_os.environ.get(_MneZdSrBackend.DIR_ENV)
            except Exception:
                pinned = None
            if pinned:
                out = []
                for one in pinned.split(";"):
                    d = one.strip().strip('"')
                    if d and d not in out:
                        out.append(d)
                return out

            dirs = []
            try:
                dirs.extend(_MneZdSrBackend._registry_dirs())
            except Exception:
                pass
            try:
                dirs.extend(_MneZdSrBackend._default_dirs())
            except Exception:
                pass
            for d in (_mne_gamedir(), _mne_basedir()):
                if d:
                    dirs.append(d)
            try:
                dirs.append(_mne_os.getcwd())
            except Exception:
                pass

            out = []
            seen = set()
            for d in dirs:
                if not d:
                    continue
                key = d.rstrip("\\/").lower()
                if key and key not in seen:
                    seen.add(key)
                    out.append(d)
            return out

        @staticmethod
        def _candidate_paths():
            """绝对路径表，64 位优先于 32 位（按文件名优先，不按目录）。"""
            out = []
            dirs = _MneZdSrBackend._candidate_dirs()
            for n in _MneZdSrBackend.DLL_NAMES:
                for d in dirs:
                    p = _mne_os.path.join(d, n)
                    try:
                        if _mne_os.path.exists(p) and p not in out:
                            out.append(p)
                    except Exception:
                        continue
            return out

        # ------------------------------------------------ 加载 / 换候选
        def _load_at(self, index):
            path = self._paths[index]
            try:
                lib = _mne_ctypes.WinDLL(path)
                lib.InitTTS.argtypes = [_mne_ctypes.c_int, _mne_ctypes.c_wchar_p,
                                        _mne_ctypes.c_bool]
                lib.InitTTS.restype = _mne_ctypes.c_int
                lib.Speak.argtypes = [_mne_ctypes.c_wchar_p, _mne_ctypes.c_bool]
                lib.Speak.restype = _mne_ctypes.c_int
                lib.GetSpeakState.argtypes = []
                lib.GetSpeakState.restype = _mne_ctypes.c_int
                lib.StopSpeak.argtypes = []
                lib.StopSpeak.restype = None
                try:
                    lib.Braille.argtypes = [_mne_ctypes.c_wchar_p, _mne_ctypes.c_bool]
                    lib.Braille.restype = _mne_ctypes.c_int
                    has_braille = True
                except AttributeError:
                    has_braille = False
            except Exception as e:
                self._load_error = u"%s：%s: %s" % (path, type(e).__name__, _mne_u(e))
                return False
            self._lib = lib
            self._index = index
            self.loaded_from = path
            self._has_braille = has_braille
            return True

        def _unload(self):
            lib = self._lib
            self._lib = None
            self._handshake_ok = False
            self._state = None
            self._state_at = None
            self._state_error = None
            self._ok = False
            h = getattr(lib, "_handle", None)
            if not h:
                return
            try:
                _mne_ctypes.windll.kernel32.FreeLibrary(_mne_ctypes.c_void_p(h))
            except Exception:
                pass

        def _select_next_candidate(self):
            if not self._paths:
                return False
            nxt = self._index + 1
            if nxt >= len(self._paths):
                return False
            self._unload()
            for i in range(nxt, len(self._paths)):
                if self._load_at(i):
                    return True
            return False

        def _ensure(self):
            if self._lib is not None:
                return True
            if self._tried:
                return False
            self._tried = True
            self._paths = self._candidate_paths()
            if not self._paths:
                self._load_error = u"未找到 ZDSRAPI_x64.dll（争渡读屏未安装？）"
                self.reason = self._load_error
                return False
            for i in range(len(self._paths)):
                if self._load_at(i):
                    return True
            self.reason = self._load_error or u"加载失败"
            return False

        # ------------------------------------------------ 握手 / 状态
        def _handshake(self):
            """InitTTS(0, None, False)。成功一次后不再重复。"""
            if self._handshake_ok:
                return True
            now = _mne_time.monotonic()
            if self._init_tried_at is not None and \
                    (now - self._init_tried_at) < self.INIT_RETRY_INTERVAL:
                return False
            self._init_tried_at = now

            while True:
                try:
                    rc = self._lib.InitTTS(0, None, False)
                except Exception as e:
                    self.reason = u"InitTTS 调用异常 %s: %s" % (type(e).__name__, _mne_u(e))
                    _mne_log(u"ZDSR", self.reason)
                    return False
                if rc == 0:
                    self._handshake_ok = True
                    _mne_log(u"ZDSR", u"InitTTS(0=读屏通道, NULL, 按键不打断) -> 0")
                    return True
                if rc != 1:
                    self.reason = u"InitTTS 返回 %d（%s）" % (
                        rc, self.INIT_WHY.get(rc, u"未知"))
                    _mne_log(u"ZDSR", self.reason)
                    return False
                # rc == 1：版本不匹配 → 换下一份候选
                if self.loaded_from and self.loaded_from not in self._mismatch:
                    self._mismatch.append(self.loaded_from)
                if not self._select_next_candidate():
                    self.reason = (
                        u"InitTTS 返回 1（版本不匹配），%d 份候选 dll 全试过都不匹配：%s"
                        % (len(self._mismatch), u"、".join(self._mismatch)))
                    _mne_log(u"ZDSR", self.reason)
                    return False
                _mne_log(u"ZDSR",
                         u"InitTTS 返回 1（版本不匹配），换下一份候选重试：%s"
                         % self.loaded_from)

        def _read_state(self):
            """问一次 GetSpeakState()。self._ok 只在这里被写。"""
            self._state = None
            self._state_error = None
            try:
                self._state = int(self._lib.GetSpeakState())
            except Exception as e:
                self._state_error = u"%s: %s" % (type(e).__name__, _mne_u(e))
            self._state_at = _mne_time.monotonic()
            if self._state in (3, 4):
                self._ok = True
                self.reason = u"正在朗读" if self._state == 3 else u"在跑（没有朗读）"
            elif self._state is None:
                self._ok = False
                self.reason = u"GetSpeakState 调用异常（%s）" % (
                    self._state_error or u"未知")
            else:
                self._ok = False
                self.reason = self.STATE_WHY.get(
                    self._state, u"未知返回码 %d" % self._state)

        # ------------------------------------------------ 公开接口
        def available(self):
            """★ 判据只有 GetSpeakState() ∈ {3, 4}。绝不看 Speak 返回值。"""
            if not self._ensure():
                return False
            if not self._handshake():
                return False
            now = _mne_time.monotonic()
            if self._state_at is None or (now - self._state_at) > self.STATE_TTL:
                self._read_state()
            return self._ok

        def speak(self, text):
            """透传 Speak(text, True)。rc != 0 返回 False。

            ⚠ bInterrupt 固定 True：男娘补丁的 interrupt 语义是"新内容优先"，
              且 _MneSpeech.speak 已经先调了 stop()（如果 interrupt=True），
              这里再传 True 是幂等的；如果 stop() 失败了，True 也能确保立即播放。
            """
            if self._lib is None:
                return False
            try:
                rc = self._lib.Speak(_mne_u(text), True)
                if rc != 0:
                    _mne_log(u"错误", u"ZDSR Speak rc=%s" % rc)
                    return False
                return True
            except Exception:
                _mne_log_exc("zdsr.speak")
                return False

        def stop(self):
            if self._lib is not None:
                try:
                    self._lib.StopSpeak()
                except Exception:
                    _mne_log_exc("zdsr.stop")

    class _MneSpeech(object):
        def __init__(self):
            self.nvda = _MneNvdaBackend()
            self.zdsr = _MneZdSrBackend()
            self.engine = _MneEngineBackend()
            self.log = _MneLogBackend()
            self.active = None
            self.last_text = u""
            self.last_raw = u""

        def start(self):
            if _MNE_TEST_LOG or _MNE_TTS_PREF == u"log":
                self.active = self.log
            elif _MNE_TTS_PREF == u"nvda":
                self.active = self.nvda if self.nvda.available() else self.log
            elif _MNE_TTS_PREF == u"zdsr":
                self.active = self.zdsr if self.zdsr.available() else self.log
            elif _MNE_TTS_PREF == u"sapi":
                self.active = self.engine if self.engine.available() else self.log
            elif self.nvda.available():
                self.active = self.nvda
            elif self.zdsr.available():
                self.active = self.zdsr
            elif self.engine.available():
                self.active = self.engine
            else:
                self.active = self.log
            MneHost.backend_name = _mne_u(self.active.name)
            _mne_log(
                u"后端",
                u"NVDA=%s(%s) ZDSR=%s(%s) 引擎SAPI=%s 选用=%s"
                % (self.nvda.available(), _mne_u(self.nvda.reason),
                   self.zdsr.available(), _mne_u(self.zdsr.reason),
                   self.engine.available(), MneHost.backend_name),
            )

        def cycle(self):
            """Alt+Shift+F9：在可用后端之间轮换（朗读侧热键，不碰游戏键位）。"""
            if _MNE_TEST_LOG:
                _mne_log(u"后端", u"测试模式：Alt+Shift+F9 已收到，保持日志后端")
                return MneHost.backend_name
            order = []
            if self.nvda.available():
                order.append(self.nvda)
            if self.zdsr.available():
                order.append(self.zdsr)
            if self.engine.available():
                order.append(self.engine)
            order.append(self.log)
            if not order:
                return MneHost.backend_name
            try:
                i = order.index(self.active)
            except ValueError:
                i = -1
            self.active = order[(i + 1) % len(order)]
            MneHost.backend_name = _mne_u(self.active.name)
            _mne_log(u"后端", u"切换到 %s" % MneHost.backend_name)
            self.speak(u"朗读后端：%s" % MneHost.backend_name, u"系统", dedupe=0)
            return MneHost.backend_name

        def speak(self, raw, kind=u"朗读", dedupe=0.6, interrupt=True):
            text = _mne_clean(raw)
            if not text:
                return False
            now = _mne_time.time()
            if dedupe and text == self.last_text and (now - self.last_text_time) < dedupe:
                return False
            self.last_text = text
            self.last_text_time = now
            if interrupt and self.active is not None:
                try:
                    self.active.stop()
                except Exception:
                    pass
            ok = False
            try:
                ok = self.active.speak(text)
            except Exception:
                _mne_log_exc("speech.speak")
            MneHost.remember(text)
            MneHost.spoken_count += 1
            # 自动化测试断言用：测试模式下落在 <ts>\t<kind>\t<text> 的第 2/3 列
            _mne_log(kind, text)
            return ok

        def repeat(self):
            text = MneHost.repeat()
            if not text:
                return False
            return self.speak(text, u"重读", dedupe=0, interrupt=True)

        def stop(self):
            if self.active is not None:
                try:
                    self.active.stop()
                except Exception:
                    pass

    MneSpeech = _MneSpeech()
    MneSpeech.last_text_time = 0.0

    # ── 接管引擎的出声口 ──────────────────────────────────────────────────────
    def _mne_kind():
        """粗分“这句是台词/选项/界面”，只用于日志与测试断言。"""
        try:
            if renpy.get_screen("choice") is not None:
                return u"选项"
            if renpy.get_screen("say") is not None:
                return u"台词"
        except Exception:
            pass
        return u"界面"

    # 引擎自己会念的两句英文提示，换成中文（玩家的读屏里不该蹦英文）。
    _MNE_ENGINE_NOTICES = {
        u"Self-voicing enabled.": u"朗读已开启",
        u"Self-voicing disabled.": u"朗读已关闭",
        u"Clipboard voicing enabled.": u"剪贴板朗读已开启",
        u"Debug voicing enabled.": u"调试朗读已开启",
        # 引擎按钮/滑条的固定词（直接 speak 出来的，不经过替换表）
        u"activate": u"激活",
        u"deactivate": u"取消选中",
        u"increase": u"增加",
        u"decrease": u"减少",
        u"selected": u"已选中",
        u"bar": u"滑块",
    }

    def _mne_current_voice():
        """这一句 say 的配音文件名；没有就 None。

        与引擎 00voice.rpy:VoiceInfo 同一套规则（config.auto_voice + 当前 context
        的 translate_identifier），但只读、不做任何播放，用来判断“要不要让朗读闭嘴”。
        """
        try:
            cfg = getattr(renpy.config, "auto_voice", None)
            if not cfg:
                return None
            ctx = renpy.game.context()
            tlids = [
                getattr(ctx, "translate_identifier", None),
                getattr(ctx, "alternate_translate_identifier", None),
                getattr(ctx, "deferred_translate_identifier", None),
            ]
            for tlid in tlids:
                if tlid is None:
                    continue
                if isinstance(cfg, str):
                    fn = cfg.format(id=tlid)
                else:
                    fn = cfg(tlid)
                if fn and renpy.loadable(fn, directory="audio"):
                    return fn
        except Exception:
            _mne_log_exc("voice.current")
        return None

    def _mne_speaker_prefix(text):
        """从场景根文本里取“说话人”前缀（引擎 _tts_common 用 ': ' 连接子控件）。

        现在主要用于日志/调试；有配音的台词不再单独朗读它，但完整文本
        （含此前缀）仍会被记住，交给退格重读。
        """
        t = text or u""
        for sep in (u": ", u"："):
            i = t.find(sep)
            if 0 < i <= 24:
                head = t[:i].strip()
                if head:
                    return head
        return u""

    def _mne_tts_function(s):
        """引擎每帧把 tts 队列交给这里。"""
        try:
            if not MneHost.enabled:
                return None
            mode = renpy.game.preferences.self_voicing
            # clipboard/debug 是引擎自己的替代输出方式，尊重它，不重复出声。
            if mode not in (True, 1) and mode:
                if _mne_engine_tts is not None:
                    _mne_engine_tts(s)
                return None

            text = _mne_clean(s)
            if not text:
                return None
            text = _mne_apply_subs(text)

            # 快进时引擎本来就不该念（测试问卷 §3“快进停止补念”）。
            try:
                if renpy.config.skipping:
                    return None
            except Exception:
                pass

            notice = _MNE_ENGINE_NOTICES.get(text)
            if notice:
                MneSpeech.speak(notice, u"系统", dedupe=0.0)
                return None

            # 有些台词会让“角色名”先单独经过一次朗读出口（完整台词里已经带了
            # 说话人前缀），重复念一遍名字很吵，这里只压掉“整串等于说话人”的情况。
            try:
                _sc = renpy.get_screen("say")
                if _sc is not None:
                    _w = (_sc.scope or {}).get("who")
                    if isinstance(_w, str) and _mne_clean(_w) == text:
                        return None
            except Exception:
                pass

            kind = _mne_kind()
            if kind == u"台词":
                if _mne_current_voice():
                    # 这一句有配音：只放游戏配音，不叠读台词，也不朗读角色名。
                    #
                    # 但“角色名 + 台词”的完整文本仍通过 remember() 记下来，
                    # 玩家按 Backspace（重读）时会连同角色名一起念出——
                    # 满足“有配音时默认安静，退格仍可听到名称”。
                    _mne_log(u"配音台词", text)
                    MneHost.remember(text)  # 让 Backspace 能重读这一句（含角色名）
                    return None
                MneSpeech.speak(text, u"台词", dedupe=0.6)
                return None

            MneSpeech.speak(text, kind, dedupe=0.6)
        except Exception:
            _mne_log_exc("tts_function")
        return None

    try:
        renpy.config.tts_function = _mne_tts_function
        _mne_log(u"接管", u"config.tts_function → 补丁出口（引擎自语音管线不变）")
    except Exception:
        _mne_log_exc("tts.takeover")

    MneSpeech.start()