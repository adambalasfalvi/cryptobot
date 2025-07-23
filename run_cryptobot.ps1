$venvPath = ".\.venv\Scripts\Activate.ps1"
$scriptToRun = "main.py"

if (-Not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found at $venvPath"
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host "Activating virtual environment..."
. $venvPath

Write-Host "Running $scriptToRun ..."
python $scriptToRun

Write-Host "`Script finished. Press Enter to close."
Read-Host