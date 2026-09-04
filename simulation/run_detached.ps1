# Launch a case script detached from the terminal so it survives the session that started
# it. Usage:  powershell -File run_detached.ps1 cases\04_yaw_stack_study.py --workers 4
# Refuses to start while another case is running (the worker budget is per machine and
# every worker holds a factorised K matrix); pass -Force to start anyway, which makes the
# new study take only what is left of the budget. Output: out\<script stem>.detached.log.
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [switch]$Force,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
)
$sim = Split-Path -Parent $MyInvocation.MyCommand.Path
$running = Get-CimInstance Win32_Process -Filter "name='python.exe'" |
    Where-Object { $_.CommandLine -match 'cases[\\/]\d\d_' } |
    Where-Object { $_.CommandLine -notmatch 'multiprocessing' }
if ($running -and -not $Force) {
    "another case is already running (PID $($running.ProcessId -join ', ')); wait for it or pass -Force"
    exit 1
}
$stem = [IO.Path]::GetFileNameWithoutExtension($Script)
New-Item -ItemType Directory -Force (Join-Path $sim "out") | Out-Null
$argList = @("-u", $Script) + $Args
$p = Start-Process -FilePath "python" -ArgumentList $argList -WorkingDirectory $sim -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $sim "out\$stem.detached.log") -RedirectStandardError (Join-Path $sim "out\$stem.detached.err")
"started $Script (PID $($p.Id)) at $(Get-Date -Format 'HH:mm:ss'); log out\$stem.detached.log"
