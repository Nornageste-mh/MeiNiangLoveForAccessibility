# -*- coding: utf-8 -*-
# 提交前检查：.ps1 必须带 UTF-8 BOM，否则 Windows PowerShell 5.1 会按 GBK
# 解码中文注释并报语法错。只检查将被 git 跟踪的 .ps1（未跟踪文件也一起查）。
[CmdletBinding()]
param([string]$Root = (Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference = 'Stop'
$bad = @()
Get-ChildItem $Root -Recurse -Filter *.ps1 -File |
    Where-Object { $_.FullName -notmatch '\\evidence\\|\\release\\|\\.git\\' } |
    ForEach-Object {
        $b = [System.IO.File]::ReadAllBytes($_.FullName)
        $ok = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
        if (-not $ok) { $bad += $_.FullName }
    }
if ($bad.Count -gt 0) {
    $bad | ForEach-Object { "缺 BOM: $_" }
    exit 1
}
"OK：所有 .ps1 都带 UTF-8 BOM"