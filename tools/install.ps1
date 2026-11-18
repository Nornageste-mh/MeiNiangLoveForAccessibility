# 安装 / 卸载《男娘恋爱物语》无障碍补丁（给玩家用，也用于开发期部署到副本）
#
# 用法（Windows PowerShell 5.1 与 PowerShell 7 都可用）：
#   powershell -ExecutionPolicy Bypass -File tools\install.ps1
#   powershell -ExecutionPolicy Bypass -File tools\install.ps1 -Uninstall
#   powershell -ExecutionPolicy Bypass -File tools\install.ps1 -GameDir "D:\Steam\steamapps\common\mei"
#   powershell -ExecutionPolicy Bypass -File tools\install.ps1 -Verify
#
# 不传 -GameDir 时自动探测：注册表 Steam 安装目录 → libraryfolders.vdf 全部库 →
#   当前目录 → 脚本上级目录。命中哪个会打印，一个都没命中会列出「试过哪里」。
#
# ⚠ 本文件必须以 **UTF-8 带 BOM** 保存（PS 5.1 读无 BOM 的中文会按 GBK 解码→语法错误）。
#
# 设计原则：
#   **只往 game\ 下放我们自己的文件，绝不改动游戏原有文件。**
#   Ren'Py 的 loader 明确「磁盘上的松散文件优先于 .rpa 归档」，所以补丁 = 松散 .rpy 叠加层，
#   不需要重新打包任何 .rpa，也不分发游戏资源。
#   卸载 = 删掉我们登记过的文件 + 我们自己的 .rpyc，游戏目录回到装前状态（-Verify 可校验）。

[CmdletBinding()]
param(
    [string]$GameDir = "",
    [switch]$Uninstall,
    [switch]$Verify,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$SrcGame    = Join-Path $RepoRoot "mod\game"
$DllSrc     = Join-Path $RepoRoot "mod\nvdaControllerClient64.dll"
$OurDirName = "a11y_platform"          # game\ 下属于本补丁的唯一目录
$ExeNames   = @("mei.exe", "mei.py")   # 本作启动器（Ren'Py 8.5.2 官方发行包）
$GameName   = "男娘恋爱物语"

function Write-Step($m) { if (-not $Quiet) { Write-Host $m } }

# ---------------------------------------------------------------- 游戏目录自动探测
function Normalize-Path([string]$Path) {
    $p = $Path.Trim().Replace("/", "\")
    $p = $p.TrimEnd("\")
    if (-not $p) { return $Path.Trim() }
    return $p
}

function Test-GameDir([string]$Path) {
    if (-not $Path) { return $false }
    if (-not (Test-Path (Join-Path $Path "game"))) { return $false }
    foreach ($exe in $ExeNames) {
        if (Test-Path (Join-Path $Path $exe)) { return $true }
    }
    return $false
}

function Add-Probed([string]$Path) {
    $n = Normalize-Path $Path
    foreach ($q in $script:Probed) { if ($q -ieq $n) { return } }
    $script:Probed.Add($n)
}

function Get-SteamInstallPaths {
    $out = New-Object System.Collections.Generic.List[string]
    $probes = @(
        @{ Key = "HKCU:\Software\Valve\Steam";             Name = $null },
        @{ Key = "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam"; Name = $null },
        @{ Key = "HKLM:\SOFTWARE\Valve\Steam";             Name = $null }
    )
    foreach ($p in $probes) {
        foreach ($name in @("InstallPath", "SteamPath")) {
            try { $v = (Get-ItemProperty -Path $p.Key -Name $name -ErrorAction Stop).$name }
            catch { continue }
            if (-not $v) { continue }
            $v = Normalize-Path $v
            if (-not (Test-Path $v)) { continue }
            $seen = $false
            foreach ($q in $out) { if ($q -ieq $v) { $seen = $true } }
            if (-not $seen) { $out.Add($v) }
        }
    }
    return $out
}

function Get-VdfLibraryPaths([string]$VdfPath) {
    if (-not (Test-Path $VdfPath)) { return @() }
    $out = @()
    foreach ($line in ([System.IO.File]::ReadAllLines($VdfPath, [System.Text.Encoding]::UTF8))) {
        if ($line -match '^\s*"path"\s*"(.+?)"\s*$') {
            $v = $Matches[1] -replace '\\\\', '\'
            $v = $v -replace '\\"', '"'
            if ($v -and (Test-Path $v)) { $out += $v }
        }
    }
    return $out
}

function Find-GameDir {
    $script:Probed = New-Object System.Collections.Generic.List[string]
    $steamRoots = New-Object System.Collections.Generic.List[string]
    foreach ($s in (Get-SteamInstallPaths)) {
        $s = Normalize-Path $s
        if (-not ($steamRoots | Where-Object { $_ -ieq $s })) { $steamRoots.Add($s) }
    }

    foreach ($s in $steamRoots) { Add-Probed $s; if (Test-GameDir $s) { return $s } }

    $libs = New-Object System.Collections.Generic.List[string]
    foreach ($root in $steamRoots) {
        if ((Test-Path (Join-Path $root "steamapps")) -and (-not ($libs | Where-Object { $_ -ieq $root }))) {
            $libs.Add($root)
        }
    }
    $vdfs = @()
    foreach ($root in ($steamRoots + $libs)) { $vdfs += (Join-Path $root "steamapps\libraryfolders.vdf") }
    foreach ($vdf in $vdfs) {
        foreach ($lib in (Get-VdfLibraryPaths $vdf)) {
            $lib = Normalize-Path $lib
            if (-not ($libs | Where-Object { $_ -ieq $lib })) { $libs.Add($lib) }
        }
    }

    foreach ($lib in $libs) {
        $cand = Join-Path $lib "steamapps\common\mei"
        Add-Probed $cand
        if (Test-GameDir $cand) { return $cand }
    }

    foreach ($h in @((Get-Location).Path, (Split-Path -Parent $PSScriptRoot))) {
        if (-not $h) { continue }
        Add-Probed $h
        if (Test-GameDir $h) { return $h }
    }

    foreach ($guess in @("C:\Program Files (x86)\Steam", "C:\Program Files\Steam",
                         "D:\Steam", "D:\SteamLibrary", "E:\Steam", "E:\SteamLibrary")) {
        Add-Probed $guess
        if (Test-GameDir $guess) { return $guess }
        $cand = Join-Path $guess "steamapps\common\mei"
        Add-Probed $cand
        if (Test-GameDir $cand) { return $cand }
    }
    return $null
}

if (-not $GameDir -and $env:MEI_A11Y_GAME_DIR) { $GameDir = $env:MEI_A11Y_GAME_DIR }

if (-not $GameDir) {
    $GameDir = Find-GameDir
    if ($GameDir) {
        Write-Host "自动探测到游戏目录: $GameDir"
    } else {
        Write-Host "自动探测没能找到游戏目录。试过这些位置："
        foreach ($p in $script:Probed) { Write-Host "  · $p" }
        Write-Host ""
        Write-Host '请用 -GameDir 指定游戏**根**目录（里面有 mei.exe 与 game\ 子目录）：'
        Write-Host '  powershell -ExecutionPolicy Bypass -File tools\install.ps1 -GameDir "<游戏根目录>"'
        Write-Host '  （Steam 里右键游戏 → 管理 → 浏览本地文件，就是那个目录。）'
        Write-Error "找不到游戏目录 —— 自动探测失败，且没有指定 -GameDir"
        exit 1
    }
}

if (-not (Test-Path $GameDir)) { Write-Error "游戏目录不存在: $GameDir"; exit 1 }
if (-not (Test-GameDir $GameDir)) {
    Write-Error "在 $GameDir 找不到 mei.exe 或 game\ 子目录 —— 用 -GameDir 指定正确的游戏根目录"
    exit 1
}

$GameRoot      = (Resolve-Path $GameDir).Path
$DstDir        = Join-Path $GameRoot "game\$OurDirName"
$ManifestPath  = Join-Path $DstDir ".install-manifest.json"
$DllDst        = Join-Path $GameRoot "nvdaControllerClient64.dll"

function Get-Sha256([string]$Path) {
    (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Remove-OurRpyc {
    # 只删我们自己的 .rpyc（编译产物）。目录是我们的专属目录，整目录删除即可；
    # 但早期手工试验可能把 .rpyc 生成在 game\ 根，这里按前缀兜底清理。
    $prefixes = @("00_contract", "01_speech", "02_ui", "05_repeat", "06_boot", "07_choice", "10_probe")
    foreach ($f in (Get-ChildItem (Join-Path $GameRoot "game") -File -Filter *.rpyc -ErrorAction SilentlyContinue)) {
        $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
        if ($prefixes -contains $base) {
            Remove-Item $f.FullName -Force
            Write-Step "已删除编译产物 $($f.Name)"
        }
    }
}

if ($Verify) {
    if (-not (Test-Path $ManifestPath)) {
        Write-Host "未安装（找不到 $ManifestPath）"
        exit 2
    }
    $man = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $bad = 0; $ok = 0
    foreach ($e in $man.files) {
        $p = Join-Path $GameRoot $e.path
        if (-not (Test-Path $p)) { Write-Host "  [缺失] $($e.path)"; $bad++; continue }
        $h = Get-Sha256 $p
        if ($h -ne $e.sha256) { Write-Host "  [被改动] $($e.path)"; $bad++; continue }
        $ok++
    }
    Write-Host "校验完成：$ok 个文件一致，$bad 个异常。补丁版本 $($man.version)。"
    exit ($(if ($bad -gt 0) { 1 } else { 0 }))
}

if ($Uninstall) {
    if (-not (Test-Path $ManifestPath)) {
        # 没有清单时保守处理：只删我们专属目录与 dll，不碰 game\ 下其它任何东西。
        if (Test-Path $DstDir) { Remove-Item $DstDir -Recurse -Force; Write-Step "已删除 $DstDir（无清单，按目录删除）" }
        if (Test-Path $DllDst) { Remove-Item $DllDst -Force; Write-Step "已删除 nvdaControllerClient64.dll" }
        Remove-OurRpyc
    } else {
        $man = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($e in $man.files) {
            $p = Join-Path $GameRoot $e.path
            if (Test-Path $p) { Remove-Item $p -Force; Write-Step "已删除 $($e.path)" }
        }
        if (Test-Path $DstDir) { Remove-Item $DstDir -Recurse -Force }
        Remove-OurRpyc
        Write-Step "卸载完成。游戏原有文件一个都没动过。"
    }
    exit 0
}

if (-not (Test-Path $SrcGame)) { Write-Error "找不到补丁源目录: $SrcGame"; exit 1 }

$srcFiles = Get-ChildItem (Join-Path $SrcGame $OurDirName) -File -Filter *.rpy -ErrorAction SilentlyContinue
if (-not $srcFiles) { Write-Error "补丁源目录里没有 .rpy 文件: $SrcGame"; exit 1 }

New-Item -ItemType Directory -Force -Path $DstDir | Out-Null
$files = New-Object System.Collections.Generic.List[object]
foreach ($f in $srcFiles) {
    $dst = Join-Path $DstDir $f.Name
    Copy-Item $f.FullName $dst -Force
    $rel = "game\$OurDirName\$($f.Name)"
    $files.Add([ordered]@{ path = $rel; sha256 = (Get-Sha256 $dst); size = (Get-Item $dst).Length })
    Write-Step "已安装 $rel"
}

if (Test-Path $DllSrc) {
    Copy-Item $DllSrc $DllDst -Force
    $files.Add([ordered]@{ path = "nvdaControllerClient64.dll"; sha256 = (Get-Sha256 $DllDst); size = (Get-Item $DllDst).Length })
    Write-Step "已安装 nvdaControllerClient64.dll（NVDA 后端的桥，LGPL-2.1，未修改）"
} else {
    Write-Warning "没找到 mod\nvdaControllerClient64.dll —— 没有它就只能用引擎自带的 SAPI 语音。"
}

Remove-OurRpyc

$ver = "0.1.1.0"
$opt = Join-Path $RepoRoot "mod\version.txt"
if (Test-Path $opt) { $ver = (Get-Content $opt -Raw).Trim() }

$manifest = [ordered]@{
    patch     = "MeiNiangLoveForAccessibility"
    version   = $ver
    game      = $GameName
    installed = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    gameRoot  = $GameRoot
    files     = $files
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Step "安装完成（版本 $ver）。"
Write-Step ""
Write-Step "  默认朗读已开启（引擎自己的 self-voicing 通道 + NVDA），无需任何补丁专属开关。"
Write-Step "  Backspace        重读最近一句"
Write-Step "  Alt+Shift+F9     切换朗读后端（自动 / NVDA / 引擎 SAPI）"
Write-Step "  方向键 / 回车    引擎原生：界面导航与确认"
Write-Step "  V                引擎原生的自语音开关（关掉后本补丁不朗读）"
Write-Step ""
Write-Step "  卸载：powershell -ExecutionPolicy Bypass -File tools\install.ps1 -Uninstall"
