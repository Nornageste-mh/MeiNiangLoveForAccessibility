@{
    # 每个用例的语音日志期望。键 = testcase 文件名（不含 .rpy）。
    # MinLines     : A11Y_TEST_LOG 至少多少行
    # RequireKinds : 必须出现的日志 kind（dialogue/choice/ui/repeat/system）
    #
    # 说明：日志格式来自补丁 00_contract.rpy 的 _mne_log：
    #   测试模式下每行 = "<秒>\t<kind>\t<文本>"，kind 已映射成英文。
    # 这些期望是“补丁功能断言”，故意只要求最低限度（不写死台词/选项原文）。

    'tc01_boot_load'      = @{ MinLines = 3; RequireKinds = @('system') }
    'tc02_dialogue_read'  = @{ MinLines = 4; RequireKinds = @('dialogue') }
    'tc03_choice_read'    = @{ MinLines = 2; RequireKinds = @('choice') }
    'tc04_choice_select'  = @{ MinLines = 2; RequireKinds = @('choice') }
    'tc05_ui_title'       = @{ MinLines = 2; RequireKinds = @('ui') }
    'tc06_repeat'         = @{ MinLines = 2; RequireKinds = @('repeat') }
    'tc07_backend'        = @{ MinLines = 2; RequireKinds = @('system') }
    'tc08_preferences_ui' = @{ MinLines = 2; RequireKinds = @('ui') }
    'tc09_load_screen'    = @{ MinLines = 2; RequireKinds = @('ui') }
    'tc10_quit_confirm'   = @{ MinLines = 2; RequireKinds = @('ui') }
}

