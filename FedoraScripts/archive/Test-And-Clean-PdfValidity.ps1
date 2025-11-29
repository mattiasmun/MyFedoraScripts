# -----------------------------------------------------------------------------
# PowerShell Script: Test-And-Clean-PdfValidity.ps1
# Description: Defines a function to check the structural validity of a PDF
#              using qpdf, optionally cleaning or deleting invalid files.
# Prerequisites: qpdf CLI must be installed and accessible in the system PATH, OR
#                the global variable $global:QPDFPath must be set in the profile.
# -----------------------------------------------------------------------------

# --- GLOBAL SCRIPT HELP CHECK (New) ---
# Check if the user requested help before proceeding to define the function.
if ($args -contains '-help' -or $args -contains '--help' -or $args -contains '-?' -or $args -contains '/?') {
    Write-Host ""
    Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "       Test-And-Clean-PdfValidity.ps1 Usage             " -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "This script defines a single function to validate PDF integrity."
    Write-Host "It uses the 'qpdf' CLI tool to check for structural corruption."
    Write-Host ""
    Write-Host "To load and execute the function, you must first dot-source the script:"
    Write-Host "  . .\Test-And-Clean-PdfValidity.ps1"
    Write-Host "  Test-And-Clean-PdfValidity -PDFPath <path> -DeleteOnInvalid"
    Write-Host ""
    Write-Host "Key Parameters:"
    Write-Host "  -PDFPath (Mandatory) The full path to the PDF file(s) to check."
    Write-Host "  -DeleteOnInvalid (Switch) If present, the file is deleted if validation fails."
    Write-Host "  -LogFunction (Internal) Used by Convert-Docs-And-Validate.ps1 to append to its log file."
    Write-Host ""
    Write-Host "Outputs an Enum status: Valid, ValidWithWarnings, InvalidHeader, InvalidAccess, InvalidCorrupt."
    Write-Host "For detailed parameter help, run: Get-Help Test-And-Clean-PdfValidity -Full"
    Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
    exit
}
# ----------------------------------------


# Define the custom Enum for return status
Add-Type -TypeDefinition @'
public enum PdfValidationStatus {
    Valid = 1,              // Passed all checks (Exit 0)
    InvalidHeader = 2,      // Failed basic %PDF- check
    InvalidAccess = 4,      // Failed due to permission/lock/size
    InvalidCorrupt = 8,     // Failed qpdf structural check (Exit 2)
    ValidWithWarnings = 16  // Passed qpdf with warnings (Exit 3)
}
'@ -Language CSharp


<#
.SYNOPSIS
Checks the structural integrity of a PDF file using qpdf.

.DESCRIPTION
This function performs a series of checks on a PDF file: file existence, header
validation, and a structural check using the 'qpdf --check' command. It returns
a specific Enum status indicating the result and can optionally delete the file
if it is found to be invalid.

.PARAMETER PDFPath
The full path to the PDF file(s) to be checked. This parameter supports pipeline
input, allowing you to pass multiple file paths at once (e.g., from Get-ChildItem).

.PARAMETER DeleteOnInvalid
A switch parameter. If present, the function will attempt to permanently delete
the PDF file if its status is determined to be InvalidHeader, InvalidAccess,
or InvalidCorrupt.

.PARAMETER LogFunction
(Internal Use Only) A scriptblock passed by the calling function (Convert-Docs-And-Validate)
to write all output messages directly to the batch log file.

.OUTPUTS
PdfValidationStatus
Returns one of the PdfValidationStatus enumeration values (Valid, InvalidHeader, etc.)

.EXAMPLE
# Check a single file and delete it if it's corrupt
Test-And-Clean-PdfValidity -PDFPath "C:\Data\Test.pdf" -DeleteOnInvalid $true

.EXAMPLE
# Check all files in a folder and output their status
Get-ChildItem -Path "C:\Incoming" -Filter "*.pdf" | Test-And-Clean-PdfValidity

.NOTES
Requires the 'qpdf' command line utility to be installed and accessible in the system PATH,
or the global variable $global:QPDFPath to be set in the PowerShell profile.
#>
function Test-And-Clean-PdfValidity {
    [CmdletBinding(DefaultParameterSetName='Path')]
    param(
        [Parameter(Mandatory=$true, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true)]
        [Alias('FullName')]
        [string]$PDFPath,

        [Parameter(Mandatory=$false)]
        [bool]$DeleteOnInvalid = $false,

        [Parameter(Mandatory=$false)]
        [scriptblock]$LogFunction # New parameter for unified logging
    )

    # Helper function to consolidate all output, using the passed LogFunction if available
    function Write-TestLog {
        param(
            [Parameter(Mandatory=$true)][string]$Message,
            [Parameter(Mandatory=$false)][ConsoleColor]$ForegroundColor,
            [Parameter(Mandatory=$false)][bool]$IsError = $false
        )

        if ($LogFunction) {
            # Execute the LogFunction scriptblock provided by the caller
            # The Write-Log function handles both file logging and console output
            & $LogFunction -Message $Message -ForegroundColor $ForegroundColor -IsError $IsError
        } else {
            # Fallback for standalone use (or if LogFunction wasn't passed)
            if ($IsError) {
                Write-Error $Message -ForegroundColor Pink
            } elseif ($ForegroundColor) {
                Write-Host $Message -ForegroundColor $ForegroundColor
            } else {
                Write-Host $Message
            }
        }
    }
    # ----------------------------------------------------------------------------------

    # PROCESS BLOCK allows the function to handle pipeline input (e.g., Get-ChildItem)
    process {
        Write-TestLog -Message "--- Checking $($PDFPath) ---" -ForegroundColor White

        # --- Nested Deletion Function ---
        function Delete-File {
            param([string]$PathToDelete)
            try {
                Remove-Item -Path $PathToDelete -Force
                Write-TestLog -Message "🗑️ Successfully deleted invalid file: $PathToDelete" -ForegroundColor Magenta
            } catch {
                # Use IsError $true to ensure it gets logged as an error
                Write-TestLog -Message "Failed to delete file '$PathToDelete': $($_.Exception.Message)" -IsError $true
            }
        }
        # --------------------------------

        # --- 1. FILE EXISTENCE AND PATH CHECK
        if (-not (Test-Path -Path $PDFPath -PathType Leaf)) {
            Write-TestLog -Message "❌ File Not Found: $PDFPath" -ForegroundColor Pink
            return [PdfValidationStatus]::InvalidAccess # Treated as access/path error
        }

        # --- 2. SIMPLE HEADER CHECK (Robust Stream Read) ---
        $Stream = $null
        try {
            $Stream = [System.IO.File]::OpenRead($PDFPath)
            $HeaderBytes = New-Object byte[] 5

            if ($Stream.Read($HeaderBytes, 0, 5) -lt 5) {
                Write-TestLog -Message "❌ File too small to be a PDF header (less than 5 bytes)." -ForegroundColor Pink
                if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
                return [PdfValidationStatus]::InvalidAccess
            }

            $Header = [System.Text.Encoding]::ASCII.GetString($HeaderBytes)

            if ($Header -ne "%PDF-") {
                Write-TestLog -Message "❌ Basic Header Check Failed. Header starts with '$Header', not '%PDF-'." -ForegroundColor Pink
                if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
                return [PdfValidationStatus]::InvalidHeader # Explicit Header Failure
            } else {
                Write-TestLog -Message "✅ Basic Header Check Passed. Proceeding to structural check..." -ForegroundColor Green
            }

        } catch {
            # This handles permission denied or file lock errors
            Write-TestLog -Message "❌ Access Error: Could not read file header (File might be locked or permission denied)." -ForegroundColor Pink
            if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
            return [PdfValidationStatus]::InvalidAccess # Explicit Access/IO Failure
        } finally {
            if ($Stream) { $Stream.Dispose() }
        }


        # --- 3. QPDF STRUCTURAL VALIDATION CHECK (Updated Path Logic) ---
        # 1. Check for global path first (set in profile)
        $QPDFCmd = if ($global:QPDFPath -and (Test-Path -Path $global:QPDFPath -PathType Leaf)) {
            $global:QPDFPath
        } else {
            "qpdf"
        }

        # 2. Check if the command is available (either in PATH or via the explicit path)
        if (($QPDFCmd -eq "qpdf") -and -not (Get-Command -Name $QPDFCmd -ErrorAction SilentlyContinue)) {
            Write-TestLog -Message "❌ qpdf command not found. Ensure the CLI is in your PATH, or set the \$global:QPDFPath variable in your profile." -ForegroundColor Pink
            return [PdfValidationStatus]::InvalidAccess # Treat lack of dependency as failure
        }

        # qpdf --check returns non-zero exit codes for issues:
        # 0: Success, 2: Serious/fatal error/corruption, 3: Warnings

        # Capture the output and the exit code
        $QPDFOutput = & $QPDFCmd --check $PDFPath 2>&1
        $ExitCode = $LASTEXITCODE

        if ($ExitCode -eq 0) {
            # Status 0: Success, no warnings
            Write-TestLog -Message "✅ Structural Check Passed: PDF is valid." -ForegroundColor Green
            return [PdfValidationStatus]::Valid
        } elseif ($ExitCode -eq 3) {
            # Status 3: Success with warnings
            Write-TestLog -Message "⚠️ Structural Check Passed with Warnings." -ForegroundColor Yellow
            if ($QPDFOutput) {
                Write-TestLog -Message "--- QPDF Warnings ---" -ForegroundColor Yellow
                # Log each line of QPDF output using Write-TestLog
                $QPDFOutput | ForEach-Object { Write-TestLog -Message "   $_" -ForegroundColor DarkYellow }
            }
            return [PdfValidationStatus]::ValidWithWarnings
        } else {
            # Status 2 (or other non-success code): Fatal Error/Corruption
            Write-TestLog -Message "❌ Structural Check Failed. PDF is corrupted (Exit Code: $ExitCode)." -ForegroundColor Pink
            if ($QPDFOutput) {
                Write-TestLog -Message "--- QPDF Diagnostic Output ---" -ForegroundColor Pink
                # Log each line of QPDF output using Write-TestLog and marking as error
                $QPDFOutput | ForEach-Object { Write-TestLog -Message "   $_" -ForegroundColor Pink -IsError $true }
            }

            if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
            return [PdfValidationStatus]::InvalidCorrupt # Explicit Corruption Status
        }
    } # End Process Block
}
