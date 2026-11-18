# -*- coding: utf-8 -*-
# 男娘恋爱物语 · 无障碍补丁：安装校验入口（等价于 install.ps1 -Verify）
param(
    [string]$GameDir = ""
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$install = Join-Path $here 'install.ps1'
if (-not (Test-Path $install)) { Write-Error "找不到 install.ps1"; exit 1 }
$argsList = @{ Verify = $true }
if ($GameDir) { $argsList['GameDir'] = $GameDir }
& $install @argsList
exit $LASTEXITCODE