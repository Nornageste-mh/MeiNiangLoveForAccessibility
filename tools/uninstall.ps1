# -*- coding: utf-8 -*-
# 男娘恋爱物语 · 无障碍补丁：卸载入口（等价于 install.ps1 -Uninstall）
param(
    [string]$GameDir = "",
    [switch]$WhatIfOnly
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$install = Join-Path $here 'install.ps1'
if (-not (Test-Path $install)) { Write-Error "找不到 install.ps1"; exit 1 }
$argsList = @{ Uninstall = $true }
if ($GameDir) { $argsList['GameDir'] = $GameDir }
& $install @argsList
exit $LASTEXITCODE