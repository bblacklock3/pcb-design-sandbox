# Launch a case script detached from the terminal so it survives the session that started
# it. Usage:  powershell -File run_detached.ps1 cases\04_yaw_stack_study.py --workers 8
# Output goes to out\<script stem>.detached.log; the case's own progress.log/REPORT.md as usual.
param([Parameter(Mandatory = $true)][string]$Script, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
$sim = Split-Path -Parent $MyInvocation.MyCommand.Path
$stem = [IO.Path]::GetFileNameWithoutExtension($Script)
New-Item -ItemType Directory -Force (Join-Path $sim "out") | Out-Null
$argList = @("-u", $Script) + $Args
$p = Start-Process -FilePath "python" -ArgumentList $argList -WorkingDirectory $sim -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $sim "out\$stem.detached.log") -RedirectStandardError (Join-Path $sim "out\$stem.detached.err")
"started $Script (PID $($p.Id)) at $(Get-Date -Format 'HH:mm:ss'); log out\$stem.detached.log"
