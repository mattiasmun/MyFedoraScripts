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

# --- New Paths for Java and VeraPDF Validation ---
# JavaPath should point directly to the java.exe executable.
$global:JavaPath = "C:\Your\Custom\Path\To\java.exe"
# VeraPDFPath should point directly to the vera-pdf-cli.jar file.
$global:VeraPDFPath = "C:\Your\Custom\Path\To\vera-pdf-cli.jar"

# --- Set Default Location for Custom Scripts ---
# IMPORTANT: Change the path below to the actual folder path where you save your scripts.
# If the path is left as the placeholder, it defaults to a safe location.
$ScriptPathPlaceholder = "C:\Your\Path\To\Scripts"
$DefaultScriptPath = Join-Path $HOME "Documents\PowerShellScripts"

$ScriptPath = if ($ScriptPathPlaceholder -eq "C:\Your\Path\To\Scripts") {
    $DefaultScriptPath
} else {
    $ScriptPathPlaceholder
}
# -------------------------------------------------------------------


# --- Function to Safely Load a Script ---
function Load-CustomScript {
    param(
        [Parameter(Mandatory=$true)][string]$FileName,
        [Parameter(Mandatory=$true)][string]$BaseDir
    )
    $FullPath = Join-Path -Path $BaseDir -ChildPath $FileName

    if (Test-Path -Path $FullPath -PathType Leaf) {
        try {
            # Dot-source the script to load functions into the current session scope
            . $FullPath
            Write-Host "✅ Loaded custom script: $FileName" -ForegroundColor Green
        } catch {
            Write-Host "❌ Failed to load script '$FileName' due to error: $($_.Exception.Message)" -ForegroundColor Pink
        }
    } else {
        Write-Host "❌ Custom script not found: $FileName at $FullPath" -ForegroundColor Pink
    }
}

# --- Main Script Loading Block ---
# Only show startup messages if the session is interactive (not running in the background)
if ($Host.UI.IsInteractive) {
    Write-Host "--- Loading Custom PowerShell Utilities from '$ScriptPath' ---" -ForegroundColor Cyan

    # 1. Load the validation function (Test-And-Clean-PdfValidity.ps1)
    Load-CustomScript -FileName "Test-And-Clean-PdfValidity.ps1" -BaseDir $ScriptPath

    # 2. Load the main converter function (Convert-Docs-And-Validate.ps1)
    Load-CustomScript -FileName "Convert-Docs-And-Validate.ps1" -BaseDir $ScriptPath

    # Optional: Add aliases for quick execution
    Set-Alias -Name cdocs -Value Convert-Docs-And-Validate -Scope Global
    Set-Alias -Name tpdf -Value Test-And-Clean-PdfValidity -Scope Global

    Write-Host "--- Ready to convert documents (use 'cdocs') and test PDFs (use 'tpdf') ---" -ForegroundColor Cyan

    # Diagnostic Output for Custom Paths
    if (Test-Path -Path $global:QPDFPath -PathType Leaf) {
        Write-Host "  QPDF Path Resolved: $($global:QPDFPath)" -ForegroundColor DarkGreen
    }
    if (Test-Path -Path $global:RocketPDFPath -PathType Leaf) {
        Write-Host "  RocketPDF Path Resolved: $($global:RocketPDFPath)" -ForegroundColor DarkGreen
    }
}
