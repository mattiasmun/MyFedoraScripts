# -----------------------------------------------------------------------------
# PowerShell Profile Script (Microsoft.PowerShell_profile.ps1)
# This script runs every time PowerShell starts.
# -----------------------------------------------------------------------------

# If this file does not exist, you can create it by running this command:
# New-Item -Path $PROFILE -ItemType File -Force

# --- Custom Executable Paths (REQUIRED IF NOT IN SYSTEM PATH) ---
# Set these paths to your custom installation locations.
# IMPORTANT: Use the full path to the executable file (e.g., C:\Program Files\qpdf\bin\qpdf.exe)
$global:QPDFPath = "C:\Your\Custom\Path\To\qpdf.exe"
$global:RocketPDFPath = "C:\Your\Custom\Path\To\RocketPDF.exe"

# --- Set Default Location for Custom Scripts ---
# IMPORTANT: Change 'C:\Scripts\' to the actual folder path where you save
# Convert-Docs-And-Validate.ps1 and Test-And-Clean-PdfValidity.ps1
$ScriptPath = "C:\Your\Path\To\Scripts" 

# --- Function to Safely Load a Script ---
function Load-CustomScript {
    param(
        [Parameter(Mandatory=$true)][string]$FileName,
        [Parameter(Mandatory=$true)][string]$BaseDir
    )
    $FullPath = Join-Path -Path $BaseDir -ChildPath $FileName
    
    if (Test-Path -Path $FullPath -PathType Leaf) {
        # Dot-source the script to load functions into the current session scope
        . $FullPath
        Write-Host "✅ Loaded custom script: $FileName" -ForegroundColor Green
    } else {
        Write-Host "❌ Custom script not found: $FileName at $FullPath" -ForegroundColor Pink
    }
}

# --- Load Your Conversion and Validation Scripts ---
Write-Host "--- Loading Custom PowerShell Utilities ---" -ForegroundColor Cyan

# 1. Load the validation function (Test-And-Clean-PdfValidity.ps1)
Load-CustomScript -FileName "Test-And-Clean-PdfValidity.ps1" -BaseDir $ScriptPath

# 2. Load the main converter function (Convert-Docs-And-Validate.ps1)
Load-CustomScript -FileName "Convert-Docs-And-Validate.ps1" -BaseDir $ScriptPath

# Optional: Add an alias for quick execution
Set-Alias -Name cdocs -Value Convert-Docs-And-Validate -Scope Global

Write-Host "--- Ready to convert documents (use 'cdocs') ---" -ForegroundColor Cyan

# Example of how you would use it after starting PowerShell:
# cdocs -SourceDirectory "C:\Documents" -DeleteOriginalDocx
