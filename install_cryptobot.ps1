# PowerShell script to set up the CryptoBot environment

Write-Host "========================================" -ForegroundColor Green
Write-Host "CryptoBot Environment Setup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Set variables
$currentDir = Get-Location
$venvName = ".venv"
$requirementsFilePath = Join-Path $currentDir "requirements.txt"

Write-Host "Current directory: $currentDir"
Write-Host "Virtual environment name: $venvName"

# Check if requirements.txt exists
if (-Not (Test-Path $requirementsFilePath)) 
{
    Write-Error "requirements.txt not found in the current directory. Please ensure it exists before running this script."
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment '$venvName'..."
try 
{
    python -m venv $venvName
    Write-Host "Virtual environment created successfully!"
} 
catch 
{
    Write-Error "Failed to create virtual environment: $_"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
try 
{
    & "$venvName\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated!"
} 
catch 
{
    Write-Error "Failed to activate virtual environment: $_"
    exit 1
}

# Install packages from requirements.txt
Write-Host "Installing packages from $requirementsFilePath..."
try 
{
    pip install -r $requirementsFilePath
    Write-Host "All packages installed successfully!"
} 
catch 
{
    Write-Error "Failed to install packages from $requirementsFilePath"
    exit 1
}

# Display installed packages
Write-Host "`nInstalled packages:"
pip list

Write-Host "`n========================================"
Write-Host "Setup completed successfully!"
Write-Host "========================================"

Write-Host "`nPress Enter to continue..."
Read-Host