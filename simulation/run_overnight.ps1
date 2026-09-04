# Launch the long-running yaw stack study detached from the terminal so it survives the
# session that started it. Progress: out\04_yaw_stack_study\progress.log ; result: REPORT.md
$sim = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $sim "out\04_yaw_stack_study"
New-Item -ItemType Directory -Force $out | Out-Null
$p = Start-Process -FilePath "python" -ArgumentList "-u", "cases\04_yaw_stack_study.py" `
    -WorkingDirectory $sim -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $out "stdout.log") -RedirectStandardError (Join-Path $out "stderr.log")
"started python PID $($p.Id) at $(Get-Date -Format 'HH:mm:ss'); watch $out\progress.log"
