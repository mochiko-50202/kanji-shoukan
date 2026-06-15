# =================================================
# 週刊ニュース自動印刷 - セットアップスクリプト
# 右クリック→「PowerShellで実行」で起動してください
# =================================================

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host ""
    Write-Host ">>> $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "    [OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "    [NG] $msg" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Yellow
Write-Host "  週刊ニュース自動印刷 セットアップ" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow

# --------------------------------------------------
# 1. スクリプトの保存先を決める
# --------------------------------------------------
Write-Step "1. インストール先フォルダを作成"
$installDir = "$env:USERPROFILE\Documents\weekly_news"
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Write-OK "フォルダ作成: $installDir"

# print_weekly_news.py をコピー
$scriptSrc = Join-Path $PSScriptRoot "print_weekly_news.py"
$scriptDst = Join-Path $installDir "print_weekly_news.py"
Copy-Item -Path $scriptSrc -Destination $scriptDst -Force
Write-OK "スクリプトをコピーしました"

# --------------------------------------------------
# 2. Python の確認
# --------------------------------------------------
Write-Step "2. Python の確認"
try {
    $pyVersion = & python --version 2>&1
    Write-OK "Python が見つかりました: $pyVersion"
} catch {
    Write-Fail "Python が見つかりません"
    Write-Host "    https://www.python.org/downloads/ からインストールしてください" -ForegroundColor Yellow
    Write-Host "    ※「Add Python to PATH」に必ずチェックを入れてください" -ForegroundColor Yellow
    Read-Host "インストール後、Enterを押してください"
    $pyVersion = & python --version 2>&1
    Write-OK "Python: $pyVersion"
}

# --------------------------------------------------
# 3. 必要ライブラリのインストール
# --------------------------------------------------
Write-Step "3. 必要ライブラリのインストール (requests, pywin32)"
& python -m pip install --quiet --upgrade requests pywin32
Write-OK "ライブラリのインストール完了"

# --------------------------------------------------
# 4. NOTION_TOKEN の設定
# --------------------------------------------------
Write-Step "4. Notion トークンの設定"

$existingToken = [System.Environment]::GetEnvironmentVariable("NOTION_TOKEN", "User")
if ($existingToken) {
    Write-OK "NOTION_TOKEN はすでに設定済みです"
    $change = Read-Host "    変更しますか？ (y/N)"
    if ($change -ne "y" -and $change -ne "Y") {
        Write-OK "変更しません"
    } else {
        $existingToken = ""
    }
}

if (-not $existingToken) {
    Write-Host ""
    Write-Host "    GitHub の「シークレットと変数→アクション」の NOTION_TOKEN と" -ForegroundColor White
    Write-Host "    同じ値を入力してください (secret_xxx...)" -ForegroundColor White
    Write-Host ""
    $token = Read-Host "    NOTION_TOKEN を入力"
    [System.Environment]::SetEnvironmentVariable("NOTION_TOKEN", $token.Trim(), "User")
    Write-OK "NOTION_TOKEN を環境変数に保存しました"
}

# --------------------------------------------------
# 5. タスクスケジューラに登録
# --------------------------------------------------
Write-Step "5. タスクスケジューラに登録（毎週月曜 08:30 / スリープ解除あり）"

$taskName = "週刊ニュース自動印刷"
$pythonPath = (& where.exe python 2>$null | Select-Object -First 1).Trim()
$scriptPath = $scriptDst

# 既存タスクを削除
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-OK "既存タスクを削除しました"
}

# タスクを作成
$action  = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "`"$scriptPath`"" `
    -WorkingDirectory $installDir

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday `
    -At "08:30:00"

$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType InteractiveToken `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-OK "タスクスケジューラに登録しました"

# --------------------------------------------------
# 6. テスト実行の確認
# --------------------------------------------------
Write-Step "6. 今すぐテスト実行しますか？"
Write-Host "    （Notionに今日のニュースがある場合のみ印刷されます）" -ForegroundColor Gray
$doTest = Read-Host "    実行しますか？ (y/N)"

if ($doTest -eq "y" -or $doTest -eq "Y") {
    Write-Host ""
    Write-Host "    実行中... ログは $installDir\print_log.txt に記録されます" -ForegroundColor Gray
    & python $scriptPath
}

# --------------------------------------------------
# 完了
# --------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Yellow
Write-Host "  セットアップ完了！" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "  毎週月曜 08:30 に自動で：" -ForegroundColor White
Write-Host "  ・PCがスリープから自動復帰" -ForegroundColor White
Write-Host "  ・Notionからニュースを取得" -ForegroundColor White
Write-Host "  ・EP-881A に自動印刷（失敗時は3回リトライ）" -ForegroundColor White
Write-Host ""
Write-Host "  ログファイル: $installDir\print_log.txt" -ForegroundColor Gray
Write-Host ""
Read-Host "Enterを押して閉じる"
