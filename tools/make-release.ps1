# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# 男娘恋爱物语 · 无障碍补丁 · 打包脚本
#
# 用法：
#   pwsh -File tools\make-release.ps1
#   pwsh -File tools\make-release.ps1 -OutDir D:\some\where
#
# 产出：<OutDir>\MeiNiangLoveForAccessibility-<版本>.zip
#   zip 内是 MeiNiangLoveForAccessibility\ 一个顶层目录，包含：
#     README.md / CHANGELOG.md / NOTICE.md / LICENSE / 测试文档.md
#     docs\  mod\  tools\  tests\
#   不包含：evidence\（测试证据里抄到了游戏台词，属版权内容）
#
# 注意：本脚本必须保存为 UTF-8 带 BOM，且不要在 Windows PowerShell 5.1 里
#       用 Get-Content -Raw 读无 BOM 的 UTF-8（会按 GBK 解码成乱码）。
# ═══════════════════════════════════════════════════════════════════════════

[CmdletBinding()]
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$OutDir = $Root,
    [switch]$NoZip
)

$ErrorActionPreference = 'Stop'

# ── 版本号从补丁里读，避免手写两份
$contract = Join-Path $Root 'mod\game\a11y_platform\00_contract.rpy'
if (-not (Test-Path $contract)) { throw "找不到 $contract（-Root 指错了？）" }
$ver = $null
foreach ($line in Get-Content $contract -Encoding UTF8) {
    if ($line -match '_MNE_PATCH_VERSION\s*=\s*"([^"]+)"') { $ver = $Matches[1]; break }
}
if (-not $ver) { throw "没能从 00_contract.rpy 读到 _MNE_PATCH_VERSION" }

$name = "MeiNiangLoveForAccessibility-$ver"
"版本: $ver"
"源目录: $Root"

# ── 必须入包的文件/目录（缺一个就报错，避免发出空包）
$items = @(
    'README.md', 'CHANGELOG.md', 'NOTICE.md', 'LICENSE', '测试文档.md',
    'docs', 'mod', 'tools', 'tests'
)
foreach ($it in $items) {
    if (-not (Test-Path (Join-Path $Root $it))) { throw "缺少需要打包的 $it" }
}

# ── 暂存目录
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mne-release-" + [guid]::NewGuid().ToString('N'))
$stage = Join-Path $stageRoot $name
New-Item -ItemType Directory -Path $stage -Force | Out-Null
try {
    foreach ($it in $items) {
        $src = Join-Path $Root $it
        $dst = Join-Path $stage $it
        if ((Get-Item $src).PSIsContainer) {
            Copy-Item $src $dst -Recurse -Force
        } else {
            Copy-Item $src $dst -Force
        }
    }

    # 去掉不该进包的东西（防御性：即使源目录里有残留）
    $junk = @('__pycache__', '*.rpyc', '*.pyc', '*.log', 'a11y_speech.log', '.install-manifest.json')
    foreach ($pattern in $junk) {
        Get-ChildItem $stage -Recurse -Force -Include $pattern -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }

    # ── 校验 .ps1 都带 UTF-8 BOM（PS5.1 的硬要求）
    $bad = @()
    Get-ChildItem $stage -Recurse -Filter *.ps1 | ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        if (-not ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) {
            $bad += $_.FullName
        }
    }
    if ($bad.Count -gt 0) { throw ("以下 .ps1 缺 UTF-8 BOM：" + ($bad -join '; ')) }

    # ── 打包
    if (-not $NoZip) {
        New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
        $zip = Join-Path $OutDir ($name + '.zip')
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal
        $size = (Get-Item $zip).Length
        "打包完成: $zip（$size 字节）"

        # ── 校验 zip 里没有版权内容
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
        try {
            $badEntry = $z.Entries | Where-Object {
                $_.FullName -match 'evidence/|extracted/|decompiled/|\.rpa$|\.rpyc$|\.log$'
            }
            if ($badEntry) { throw ("zip 里混进了不该发布的文件：" + (($badEntry | ForEach-Object FullName) -join '; ')) }
            "入口数: " + $z.Entries.Count
        } finally { $z.Dispose() }
    } else {
        "已按要求跳过压缩，仅校验。暂存目录: $stage"
    }
}
finally {
    if (Test-Path $stageRoot) { Remove-Item $stageRoot -Recurse -Force -ErrorAction SilentlyContinue }
}