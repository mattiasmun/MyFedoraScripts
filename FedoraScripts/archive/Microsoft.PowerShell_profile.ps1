# -----------------------------------------------------------------------------
# PowerShell Profile Script (Microsoft.PowerShell_profile.ps1)
# This script runs every time PowerShell starts.
# -----------------------------------------------------------------------------

# If this file does not exist, you can create it by running this command:
# New-Item -Path $PROFILE -ItemType File -Force

# --- Custom Executable Paths (REQUIRED IF NOT IN SYSTEM PATH) ---
# Set these paths to your custom installation locations.
# IMPORTANT: Use the full path to the executable file (e.g., C:\Program Files\qpdf\bin\qpdf.exe)
$global:QPDFPath = "C:\Users\ai21558\Program\qpdf-12.2.0-mingw64\bin\qpdf.exe"
$global:RocketPDFPath = "C:\Users\ai21558\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\rocketpdf.exe"

# --- New Paths for Java and VeraPDF Validation ---
# JavaPath should point directly to the java.exe executable.
$global:JavaPath = "C:\Users\ai21558\Program\jdk-24.0.1\bin\java.exe"
# VeraPDFPath should point directly to the vera-pdf-cli.jar file.
$global:VeraPDFPath = "C:\Users\ai21558\Program\verapdf-greenfield-1.28.1\bin\greenfield-apps-1.28.1.jar"

# --- Executable Wrapper Functions (Allows calling by base name, e.g., 'qpdf') ---

function qpdf {
    if (Test-Path -Path $global:QPDFPath -PathType Leaf) {
        # The call operator (&) executes the file, and @($args) forwards all parameters.
        & $global:QPDFPath @($args)
    } else {
        Write-Error "QPDF executable not found at '$global:QPDFPath'. Please check the path."
    }
}

function rocketpdf {
    if (Test-Path -Path $global:RocketPDFPath -PathType Leaf) {
        & $global:RocketPDFPath @($args)
    } else {
        Write-Error "RocketPDF executable not found at '$global:RocketPDFPath'. Please check the path."
    }
}

function java {
    if (Test-Path -Path $global:JavaPath -PathType Leaf) {
        & $global:JavaPath @($args)
    } else {
        Write-Error "Java executable not found at '$global:JavaPath'. Please check the path."
    }
}

# VeraPDF is a JAR file and requires calling Java with the -jar flag
function verapdf-cli {
    if (-not (Test-Path -Path $global:JavaPath -PathType Leaf)) {
        Write-Error "Java executable not found at '$global:JavaPath'. Cannot run VeraPDF."
        return
    }
    if (-not (Test-Path -Path $global:VeraPDFPath -PathType Leaf)) {
        Write-Error "VeraPDF JAR not found at '$global:VeraPDFPath'. Cannot run VeraPDF."
        return
    }
    
    # Call java.exe with the -jar argument pointing to the VeraPDF jar, 
    # followed by all arguments passed to verapdf-cli function.
    & $global:JavaPath -jar $global:VeraPDFPath @($args)
}

# --- Set Default Location for Custom Scripts ---
# IMPORTANT: Change the path below to the actual folder path where you save your scripts.
# If the path is left as the placeholder, it defaults to a safe location.
$ScriptPathPlaceholder = "C:\Users\ai21558\Program"
$PlaceholderCheck = "C:\Your\Path\To\Scripts" # The string to check against
$DefaultScriptPath = Join-Path $HOME "Documents\PowerShellScripts"

$ScriptPath = if ($ScriptPathPlaceholder -eq $PlaceholderCheck) {
    $DefaultScriptPath
} else {
    $ScriptPathPlaceholder
}
# -------------------------------------------------------------------


# --- Function to Safely Load a Script (ENHANCED FOR EXPLICIT SCOPING) ---
function Load-CustomScript {
    param(
        [Parameter(Mandatory=$true)][string]$FileName,
        [Parameter(Mandatory=$true)][string]$BaseDir,
        [Parameter(Mandatory=$false)][string]$AnAlias
    )
    $FullPath = Join-Path -Path $BaseDir -ChildPath $FileName
    # Extract the command name from the file name (e.g., Test-And-Clean-PdfValidity)
    $FunctionName = $FileName -replace '\.ps1$'

    if (Test-Path -Path $FullPath -PathType Leaf) {
        try {
            # Explicitly dot-source the script into the global scope.
            . $FullPath
            if ($AnAlias) {
                # Optional: Add aliases for quick execution
                Set-Alias -Name $AnAlias -Value $FullPath -Scope Global
            }
            
            # IMMEDIATE POST-LOAD CHECK
            $FunctionCheck = Get-Command $FunctionName -ErrorAction SilentlyContinue
            if ($FunctionCheck -is [System.Management.Automation.FunctionInfo]) {
                Write-Host "✅ Loaded and verified function: $FunctionName" -ForegroundColor Green
            } else {
                # This should catch cases where the file was found, but the function 
                # definition (e.g., the 'function { ... }' block) wasn't recognized or defined.
                Write-Host "⚠️ Loaded script '$FileName', but could not find the function '$FunctionName'." -ForegroundColor Yellow
                Write-Host "   -> Ensure the function is defined inside the file using the 'function' keyword." -ForegroundColor Yellow
            }

        } catch {
            # Use Red for failed loading due to script error
            Write-Host "❌ Failed to load script '$FileName' due to error: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "   -> Check the content of the script file for syntax errors." -ForegroundColor Yellow
        }
    } else {
        # Use Magenta for file not found
        Write-Host "❌ Custom script not found: $FileName at $FullPath" -ForegroundColor Magenta
    }
}

# --- Main Script Loading Block ---
# Only show startup messages if the session is interactive (not running in the background)
if ($Host.Name -eq 'ConsoleHost') {
    # Diagnostic: Check Execution Policy
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -eq 'Restricted') {
        Write-Host "🛑 WARNING: Execution Policy is '$policy'. Scripts cannot run." -ForegroundColor Red
        Write-Host "   -> Run 'Set-ExecutionPolicy RemoteSigned -Scope CurrentUser' to fix." -ForegroundColor Yellow
    }

    Write-Host "--- Loading Custom PowerShell Utilities ---" -ForegroundColor Cyan
    Write-Host "-> Determined Script Path: '$ScriptPath'" -ForegroundColor Yellow

    # 1. Load the validation function (Test-And-Clean-PdfValidity.ps1)
    Load-CustomScript -FileName "Test-And-Clean-PdfValidity.ps1" -BaseDir $ScriptPath -AnAlias cdocs

    # 2. Load the main converter function (Convert-Docs-And-Validate.ps1)
    Load-CustomScript -FileName "Convert-Docs-And-Validate.ps1" -BaseDir $ScriptPath -AnAlias tpdf

    Write-Host "--- Ready to convert documents (use 'cdocs') and test PDFs (use 'tpdf') ---" -ForegroundColor Cyan

    # -----------------------------------------------------------------------
    # DIAGNOSTIC CHECKS: Verify functions and aliases are actually available
    # -----------------------------------------------------------------------
    
    # Check custom script functions
    $cdocsCheck = Get-Command cdocs -ErrorAction SilentlyContinue
    $tpdfCheck = Get-Command tpdf -ErrorAction SilentlyContinue

    if ($cdocsCheck -is [System.Management.Automation.AliasInfo]) {
        Write-Host "  ✅ Alias 'cdocs' is available, pointing to $($cdocsCheck.Definition)" -ForegroundColor DarkGreen
    } else {
        Write-Host "  ❌ Alias 'cdocs' FAILED to resolve. Check function name spelling." -ForegroundColor Red
    }

    if ($tpdfCheck -is [System.Management.Automation.AliasInfo]) {
        Write-Host "  ✅ Alias 'tpdf' is available, pointing to $($tpdfCheck.Definition)" -ForegroundColor DarkGreen
    } else {
        Write-Host "  ❌ Alias 'tpdf' FAILED to resolve. Check function name spelling." -ForegroundColor Red
    }
    
    # Check the underlying custom script functions themselves
    $cdocsFunction = Get-Command Convert-Docs-And-Validate -ErrorAction SilentlyContinue
    if ($cdocsFunction -is [System.Management.Automation.FunctionInfo]) {
        Write-Host "  ✅ Function 'Convert-Docs-And-Validate' is defined." -ForegroundColor DarkGreen
    } else {
        Write-Host "  ❌ Function 'Convert-Docs-And-Validate' is MISSING. Ensure it is defined with 'function' in your .ps1 file." -ForegroundColor Red
    }
    
    # Check Executable Wrappers
    @("qpdf", "rocketpdf", "java", "verapdf-cli") | ForEach-Object {
        $check = Get-Command $_ -ErrorAction SilentlyContinue
        if ($check -is [System.Management.Automation.FunctionInfo]) {
            Write-Host "  🛠️ Wrapper Function '$_' is available." -ForegroundColor DarkCyan
        } else {
            Write-Host "  ❌ Wrapper Function '$_' is MISSING. Check wrapper function definition." -ForegroundColor Red
        }
    }

    # Diagnostic Output for Custom Paths
    if (Test-Path -Path $global:QPDFPath -PathType Leaf) {
        Write-Host "  QPDF Path Resolved: $($global:QPDFPath)" -ForegroundColor DarkGreen
    }
    if (Test-Path -Path $global:RocketPDFPath -PathType Leaf) {
        Write-Host "  RocketPDF Path Resolved: $($global:RocketPDFPath)" -ForegroundColor DarkGreen
    }
    if (Test-Path -Path $global:VeraPDFPath -PathType Leaf) {
        Write-Host "  VeraPDF JAR Path Resolved: $($global:VeraPDFPath)" -ForegroundColor DarkGreen
    }
}
