# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
# PowerShell Profile Script (Microsoft.PowerShell_profile.ps1)
# This script runs every time PowerShell starts.
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# Starta alltid i användarens hemkatalog
Set-Location $HOME

# If this file does not exist, you can create it by running this command:
# New-Item -Path $PROFILE -ItemType File -Force

# ⎯⎯ Custom Executable Paths (REQUIRED IF NOT IN SYSTEM PATH) ⎯⎯
# Set these paths to your custom installation locations.
# IMPORTANT: Use the full path to the executable file (e.g., C:\Program Files\qpdf\bin\qpdf.exe)
$global:QPDFPath = Join-Path $HOME "msys64\ucrt64\bin\qpdf.exe"
$global:RocketPDFPath = Join-Path $HOME "AppData\Local\Python\pythoncore-3.14-64\Scripts\rocketpdf.exe"

# ⎯⎯ New Paths for Java and VeraPDF Validation ⎯⎯
# JavaPath should point directly to the java.exe executable.
#$global:JavaPath = java.exe
# VeraPDFPath should point directly to the vera-pdf-cli.jar file.
$global:VeraPDFPath1 = Join-Path $HOME "msys64\home\ai21558\verapdf\verapdf-gui.bat"
$global:VeraPDFPath2 = Join-Path $HOME "msys64\home\ai21558\verapdf\verapdf.bat"

# ⎯⎯ Executable Wrapper Functions ⎯⎯

function qpdf {
    if (Test-Path -Path $global:QPDFPath -PathType Leaf) {
        # The call operator (&) executes the file, and @($args) forwards all parameters.
        & $global:QPDFPath @($args)
    } else {
        Write-Error "QPDF executable not found at '$global:QPDFPath'."
    }
}

function rocketpdf {
    if (Test-Path -Path $global:RocketPDFPath -PathType Leaf) {
        & $global:RocketPDFPath @($args)
    } else {
        Write-Error "RocketPDF executable not found at '$global:RocketPDFPath'."
    }
}

# New function for pip that uses python -m pip
function pip {
    python -m pip @args
}

function verapdf-gui {
    if (-not (Test-Path -Path $global:VeraPDFPath1 -PathType Leaf)) {
        Write-Error "VeraPDF JAR not found at '$global:VeraPDFPath'. Cannot run VeraPDF."
        return
    }

    $processParams = @{
        FilePath     = $global:VeraPDFPath1
        WindowStyle  = 'Hidden'
        # Vi skickar med eventuella argument som matats in i funktionen
        ArgumentList = $args
    }
    Start-Process @processParams
}

function verapdf {
    if (-not (Test-Path -Path $global:VeraPDFPath2 -PathType Leaf)) {
        Write-Error "VeraPDF JAR not found at '$global:VeraPDFPath'. Cannot run VeraPDF."
        return
    }

    $processParams = @{
        FilePath     = $global:VeraPDFPath2
        # Vi skickar med eventuella argument som matats in i funktionen
        ArgumentList = $args
    }
    Start-Process @processParams
}

# ⎯⎯ Set Default Location for Custom Scripts ⎯⎯
$ScriptPathPlaceholder = Join-Path $HOME "Program"
$PlaceholderCheck = "C:\Your\Path\To\Scripts"
$DefaultScriptPath = Join-Path $HOME "Documents\PowerShellScripts"

$ScriptPath = if ($ScriptPathPlaceholder -eq $PlaceholderCheck) {
    $DefaultScriptPath
} else {
    $ScriptPathPlaceholder
}
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# ⎯⎯ Function to Safely Load a Script ⎯⎯
function Load-CustomScript {
    param(
        [Parameter(Mandatory=$true)][string]$FileName,
        [Parameter(Mandatory=$true)][string]$BaseDir,
        [Parameter(Mandatory=$false)][string]$AnAlias
    )
    $FullPath = Join-Path -Path $BaseDir -ChildPath $FileName
    $FunctionName = $FileName -replace '\.ps1$'

    if (Test-Path -Path $FullPath -PathType Leaf) {
        try {
            if ($AnAlias) {
                Set-Alias -Name $AnAlias -Value $FullPath -Scope Global
            }
            . $FullPath
            $FunctionCheck = Get-Command $FunctionName -ErrorAction SilentlyContinue
            if ($FunctionCheck -is [System.Management.Automation.FunctionInfo]) {
                Write-Host "✅ Loaded and verified function: $FunctionName" -ForegroundColor Green
            } else {
                # This should catch cases where the file was found, but the function
                # definition (e.g., the 'function { … }' block) wasn't recognized or defined.
                Write-Host "⚠️ Loaded script '$FileName', but could not find the function '$FunctionName'." -ForegroundColor Yellow
                Write-Host "   → Ensure the function is defined inside the file using the 'function' keyword." -ForegroundColor Yellow
            }
        } catch {
            # Use Red for failed loading due to script error
            Write-Host "❌ Failed to load script '$FileName' due to error: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "   → Check the content of the script file for syntax errors." -ForegroundColor Yellow
        }
    } else {
        # Use Magenta for file not found
        Write-Host "❌ Custom script not found: $FileName at $FullPath" -ForegroundColor Magenta
    }
}

# ⎯⎯ Main Script Loading Block ⎯⎯
if ($Host.Name -eq 'ConsoleHost') {
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -eq 'Restricted') {
        Write-Host "🛑 WARNING: Execution Policy is '$policy'. Scripts cannot run." -ForegroundColor Red
        Write-Host "   → Run 'Set-ExecutionPolicy RemoteSigned -Scope CurrentUser' to fix." -ForegroundColor Yellow
    }

    Write-Host "⎯⎯ Loading Custom PowerShell Utilities ⎯⎯" -ForegroundColor Cyan
    Write-Host "→ Terminal started in: $PWD" -ForegroundColor Gray
    Write-Host "→ Determined Script Path: '$ScriptPath'" -ForegroundColor Yellow

    # Load-CustomScript -FileName "Example.ps1" -BaseDir $ScriptPath -AnAlias ex

    # Check Wrapper Functions inkl. nya pip
    @("verapdf-gui", "verapdf", "pip") | ForEach-Object {
        $check = Get-Command $_ -ErrorAction SilentlyContinue
        if ($check -is [System.Management.Automation.FunctionInfo]) {
            Write-Host "  🛠️ Wrapper Function '$_' is available." -ForegroundColor DarkCyan
        } else {
            Write-Host "  ❌ Wrapper Function '$_' is MISSING. Check wrapper function definition." -ForegroundColor Red
        }
    }

    Write-Host "⎯⎯ Ready to use 'pip', 'verapdf-gui' ⎯⎯" -ForegroundColor Cyan
}
