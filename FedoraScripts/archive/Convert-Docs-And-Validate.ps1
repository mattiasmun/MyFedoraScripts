# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
# PowerShell Script: Convert-Docs-And-Validate.ps1
# Description: Recursively finds DOCX files, converts them to compressed PDFs
#              using RocketPDF, and then validates the output using the
#              Test-And-Clean-PdfValidity function (which must be loaded).
# Prerequisites:
# 1. RocketPDF CLI must be installed and accessible in the system PATH, OR
#    the global variable $global:RocketPDFPath must be set in the profile.
# 2. qpdf (used by Test-And-Clean-PdfValidity) must be accessible, OR
#    the global variable $global:QPDFPath must be set in the profile.
# 3. The file 'Test-And-Clean-PdfValidity.ps1' must be loaded in the same session.
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# ⎯⎯ GLOBAL SCRIPT HELP CHECK ⎯⎯
# Check if the user requested help before proceeding to load the function or execute.
if ($args -contains '-help' -or $args -contains '--help' -or $args -contains '-?' -or $args -contains '/?') {
    Write-Host " "
    Write-Host "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯" -ForegroundColor Yellow
    Write-Host "          Convert-Docs-And-Validate.ps1 Usage           " -ForegroundColor Yellow
    Write-Host "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯" -ForegroundColor Yellow
    Write-Host "This script converts all DOCX files in a directory (recursively)"
    Write-Host "to compressed PDFs using RocketPDF, and then validates the PDF"
    Write-Host "structure using Test-And-Clean-PdfValidity (qpdf dependency)."
    Write-Host " "
    Write-Host "To execute the main function, you must first load the script (dot-source):"
    Write-Host "  . .\Convert-Docs-And-Validate.ps1"
    Write-Host "  Convert-Docs-And-Validate -SourceDirectory <path> [options]"
    Write-Host " "
    Write-Host "Key Parameters:"
    Write-Host "  -SourceDirectory    (Mandatory) The root folder to scan for DOCX files."
    Write-Host "  -OutputDirectory    (Optional)  The folder to save PDFs (maintains sub-structure)."
    Write-Host "  -DeleteOriginalDocx (Switch)    Deletes the source DOCX upon successful conversion and validation."
    Write-Host "  -SkipExistingPdf    (Switch)    Skips conversion if the target PDF already exists."
    Write-Host "  -WhatIf             (Switch)    Previews all actions (conversions, deletions) without execution."
    Write-Host " "
    Write-Host "For detailed parameter help, run: Get-Help Convert-Docs-And-Validate -Full"
    Write-Host "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯" -ForegroundColor Yellow
    exit
}
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# ⎯⎯ SCRIPT-SCOPE LOGGING FUNCTION (Moved outside the main function) ⎯⎯
# Global variable to hold the path to the current log file
$Script:LogFilePath = $null

function global:Write-Log {
    param(
        [Parameter(Mandatory=$true)][string]$Message,
        [Parameter(Mandatory=$false)][ConsoleColor]$ForegroundColor = $Host.UI.RawUI.ForegroundColor,
        [Parameter(Mandatory=$false)][bool]$IsError = $false
    )

    # 1. Format the message for the log file
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] $($Message)"

    # 2. Append to log file (only if the path has been set by Convert-Docs-And-Validate)
    if ($Script:LogFilePath) {
        try {
            Add-Content -Path $Script:LogFilePath -Value $LogEntry -ErrorAction SilentlyContinue
        } catch {
            # Write a warning to the console if log file writing fails, but continue the main process
            Write-Host "Warning: Failed to write to log file '$Script:LogFilePath'. Log message: '$LogEntry'" -ForegroundColor Yellow
        }
    }

    # 3. Write to console (using original Write-Host/Write-Error behavior)
    if ($IsError) {
        Write-Error $Message
    } else {
        Write-Host $Message -ForegroundColor $ForegroundColor
    }
}
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯


# ⎯⎯ 1. Load the Test-And-Clean-PdfValidity function ⎯⎯
# This assumes the validation script is in the same directory as this script.
# If it is not, adjust the path below.
$ValidationScriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) "Test-And-Clean-PdfValidity.ps1"

if (Test-Path -Path $ValidationScriptPath) {
    . $ValidationScriptPath
    Write-Log -Message "Loaded validation function from: $ValidationScriptPath" -ForegroundColor Cyan
} else {
    Write-Error "Test-And-Clean-PdfValidity.ps1 not found at '$ValidationScriptPath'. Please ensure it is loaded."
    # Exit script if the critical validation function cannot be found
    exit 1
}
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

<#
.SYNOPSIS
Converts DOCX files to compressed PDFs and validates their integrity.

.DESCRIPTION
This function recursively scans a source directory for *.docx files, converts them
to compressed *.pdf files using the RocketPDF CLI, and then verifies the PDF
structure and validity using the external function Test-And-Clean-PdfValidity.
It tracks statistics and provides robust logging and -WhatIf support.

.PARAMETER SourceDirectory
The root directory path where the script should begin scanning for DOCX files.
The scan is recursive.

.PARAMETER OutputDirectory
The destination directory for the generated PDF files. If this parameter is not
specified, PDFs will be placed in the same folder as their source DOCX files.
The sub-folder structure of the SourceDirectory will be maintained here.

.PARAMETER DeleteOriginalDocx
If this switch is present, the original DOCX file will be permanently deleted
only after successful conversion and validation of the corresponding PDF.

.PARAMETER SkipExistingPdf
If this switch is present, the script will check if the target PDF file already
exists and will skip the conversion process for that DOCX file if found.

.EXAMPLE
C:\PS> Convert-Docs-And-Validate -SourceDirectory "C:\Input" -OutputDirectory "C:\Output" -SkipExistingPdf

.EXAMPLE
C:\PS> Convert-Docs-And-Validate -SourceDirectory "C:\Input" -DeleteOriginalDocx -WhatIf

.NOTES
To see the full help, run: Get-Help Convert-Docs-And-Validate -Full
#>
function global:Convert-Docs-And-Validate {
    [CmdletBinding(SupportsShouldProcess=$true)] # Added SupportsShouldProcess for -WhatIf safety
    param(
        [Parameter(Mandatory=$true)]
        [string]$SourceDirectory,

        [Parameter(Mandatory=$false)]
        [string]$OutputDirectory = $SourceDirectory, # New parameter: Defaults to SourceDirectory

        [Parameter(Mandatory=$false)]
        [switch]$DeleteOriginalDocx = $false,

        [Parameter(Mandatory=$false)]
        [switch]$SkipExistingPdf = $false
    )

    # ⎯⎯ LOGGING SETUP (Initialize the log file path) ⎯⎯
    # $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $LogFileName = "Conversion_Validation_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    $Script:LogFilePath = Join-Path $OutputDirectory $LogFileName # Set the script-level variable

    # Define the logger scriptblock to pass to Test-And-Clean-PdfValidity
    # This closure ensures the validation function uses our Write-Log wrapper
    $Logger = {
        param([string]$Message, [ConsoleColor]$ForegroundColor, [bool]$IsError)
        Write-Log -Message $Message -ForegroundColor $ForegroundColor -IsError $IsError
    }
    # ⎯⎯ END LOGGING SETUP ⎯⎯

    # ⎯⎯ EXECUTABLE PATH RESOLUTION (New) ⎯⎯
    # Use the global path defined in the profile if available, otherwise assume it's in PATH.
    $RocketPdfCmd = if ($global:RocketPDFPath -and (Test-Path -Path $global:RocketPDFPath -PathType Leaf)) {
        $global:RocketPDFPath
    } else {
        "rocketpdf"
    }
    # We will pass the QPDF path resolution logic to the Test-And-Clean-PdfValidity function
    # via the $global:QPDFPath variable.
    # ⎯⎯ END PATH RESOLUTION ⎯⎯

    # Log the start of the script
    Write-Log -Message "⎯⎯ Starting Conversion and Validation Script ⎯⎯" -ForegroundColor Cyan
    Write-Log -Message "Log file created at: $Script:LogFilePath" -ForegroundColor Cyan
    Write-Log -Message "Source Directory: $SourceDirectory" -ForegroundColor Cyan
    Write-Log -Message "Output Directory: $OutputDirectory" -ForegroundColor Cyan
    Write-Log -Message "Delete Original DOCX: $DeleteOriginalDocx" -ForegroundColor Cyan
    Write-Log -Message "Skip Existing PDF: $SkipExistingPdf" -ForegroundColor Cyan


    # Resolve paths to ensure proper handling of relative/absolute paths
    try {
        $SourceDirectory = Get-Item -Path $SourceDirectory -ErrorAction Stop | Select-Object -ExpandProperty FullName
        $OutputDirectory = Get-Item -Path $OutputDirectory -ErrorAction Stop | Select-Object -ExpandProperty FullName
    } catch {
        Write-Log -Message "Error resolving directory paths: $($_.Exception.Message)" -IsError $true
        return
    }

    # Record the start time for total processing duration
    $StartTime = Get-Date

    # Initialize counters for validation results
    $ValidCount = 0
    $WarningsCount = 0
    $InvalidCount = 0
    $SkippedCount = 0 # New counter for skipped files

    # Check if RocketPDF is available
    if (($RocketPdfCmd -eq "RocketPDF") -and -not (Get-Command -Name $RocketPdfCmd -ErrorAction SilentlyContinue)) {
        Write-Log -Message "RocketPDF command not found. Ensure the CLI is in your PATH, or set the \$global:RocketPDFPath variable in your profile." -IsError $true
        return
    }

    # Find all DOCX files recursively
    Write-Log -Message "Searching for *.docx files recursively in: '$SourceDirectory'" -ForegroundColor Yellow
    $DocxFiles = Get-ChildItem -Path $SourceDirectory -Filter "*.docx" -Recurse -File

    if (-not $DocxFiles) {
        Write-Log -Message "No DOCX files found in '$SourceDirectory'." -ForegroundColor Yellow

        # Calculate time even if no files were found
        $EndTime = Get-Date
        $TotalTime = New-TimeSpan -Start $StartTime -End $EndTime
        Write-Log -Message "⎯⎯ Conversion and Validation Process Complete ⎯⎯" -ForegroundColor Cyan
        Write-Log -Message "Total processing time (no files found): $($TotalTime.TotalSeconds) seconds" -ForegroundColor Cyan
        return
    }

    Write-Log -Message "Found $($DocxFiles.Count) DOCX file(s). Starting conversion…" -ForegroundColor Yellow

    # Process each file
    foreach ($File in $DocxFiles) {
        # Calculate the relative path from the source directory root
        $RelativePath = $File.DirectoryName.Substring($SourceDirectory.Length).TrimStart([System.IO.Path]::DirectorySeparatorChar)

        # Determine the target output folder (maintains subfolder structure)
        $OutputFolder = Join-Path $OutputDirectory $RelativePath

        # Construct the final PDF path
        $PdfPath = Join-Path $OutputFolder ($File.BaseName + ".pdf")

        Write-Log -Message " "
        Write-Log -Message "Processing: $($File.Name)" -ForegroundColor White

        # ⎯⎯ Create Output Directory if it doesn't exist ⎯⎯
        if (-not (Test-Path -Path $OutputFolder -PathType Container)) {
            Write-Log -Message "  → Creating output directory: $OutputFolder" -ForegroundColor DarkGray
            # Check if ShouldProcess is supported before creating the directory
            if ($PSCmdlet.ShouldProcess("Creating output directory '$OutputFolder'")) {
                New-Item -Path $OutputFolder -ItemType Directory | Out-Null
            }
        }

        # ⎯⎯ Check for existing PDF and skip if requested ⎯⎯
        if ($SkipExistingPdf -and (Test-Path -Path $PdfPath -PathType Leaf)) {
            $SkippedCount++
            Write-Log -Message "  ⏩ Skipped: Matching PDF already exists at '$PdfPath'." -ForegroundColor DarkYellow
            continue
        }

        # ⎯⎯ 2. RocketPDF Conversion and Compression (Wrapped in ShouldProcess) ⎯⎯
        if ($PSCmdlet.ShouldProcess("Converting '$($File.FullName)'", "Convert and save to '$PdfPath'")) {
            try {
                Write-Log -Message "  → Converting and compressing to: $PdfPath" -ForegroundColor DarkGray

                # The -Force argument is added to overwrite existing PDFs without prompt
                $RocketPdfOutput = & $RocketPdfCmd parsedoc "$($File.FullName)" compress

                if ($LASTEXITCODE -ne 0) {
                    Write-Log -Message "  ❌ RocketPDF Conversion Failed for $($File.Name). Exit Code: $LASTEXITCODE" -IsError $true
                    $RocketPdfOutput | ForEach-Object { Write-Log -Message "     $_" -IsError $true }
                    continue # Skip validation and move to the next file
                }

                Write-Log -Message "  ✅ Conversion Successful. Starting validation." -ForegroundColor Green

                # ⎯⎯ 3. Run Validation and Cleanup (NOW PASSING THE LOGGER) ⎯⎯
                # The validation function will now look for $global:QPDFPath
                $Status = Test-And-Clean-PdfValidity -PDFPath $PdfPath -DeleteOnInvalid $true -LogFunction $Logger

                if ($Status -eq [PdfValidationStatus]::Valid) {
                    $ValidCount++ # Increment Valid counter
                    Write-Log -Message "  ✨ PDF validation complete: Valid." -ForegroundColor Green

                    # ⎯⎯ 4. Optional Original File Deletion (Wrapped in ShouldProcess) ⎯⎯
                    if ($DeleteOriginalDocx) {
                        if ($PSCmdlet.ShouldProcess("Deleting original file '$($File.Name)'")) {
                            Write-Log -Message "  🗑️ Deleting original DOCX file: $($File.Name)" -ForegroundColor Magenta
                            Remove-Item -Path $File.FullName -Force
                        }
                    }
                }
                elseif ($Status -eq [PdfValidationStatus]::ValidWithWarnings) {
                    $WarningsCount++ # Increment Warnings counter
                    Write-Log -Message "  ⚠️ PDF validation complete: Valid with warnings." -ForegroundColor Yellow
                }
                else {
                    # This covers InvalidHeader, InvalidAccess, and InvalidCorrupt.
                    $InvalidCount++ # Increment Invalid counter
                    # If InvalidHeader, InvalidAccess, or InvalidCorrupt, the Test-And-Clean function
                    # handled the deletion because we passed -DeleteOnInvalid $true.
                    Write-Log -Message "  🚫 PDF validation failed (Status: $Status). PDF was invalid and has been deleted." -ForegroundColor Magenta
                }

            } catch {
                Write-Log -Message "An unhandled error occurred during processing $($File.Name): $($_.Exception.Message)" -IsError $true
            }
        } # End ShouldProcess for conversion
    }

    # ⎯⎯ 5. Calculate and display total time and summary ⎯⎯
    $EndTime = Get-Date
    $TotalTime = New-TimeSpan -Start $StartTime -End $EndTime

    Write-Log -Message " "
    Write-Log -Message "⎯⎯ Conversion and Validation Process Complete ⎯⎯" -ForegroundColor Cyan
    Write-Log -Message "Total processing time: $($TotalTime.TotalSeconds) seconds ($($TotalTime.Minutes)m $($TotalTime.Seconds)s)" -ForegroundColor Cyan
    Write-Log -Message "⎯⎯ Summary of Results ⎯⎯" -ForegroundColor Yellow
    Write-Log -Message "  Total Files Found: $($DocxFiles.Count)" -ForegroundColor White
    Write-Log -Message "  ⏩ Files Skipped (PDF Existed): $($SkippedCount)" -ForegroundColor DarkYellow
    Write-Log -Message "  ✅ Valid PDFs (Clean): $($ValidCount)" -ForegroundColor Green
    Write-Log -Message "  ⚠️ Valid PDFs with Warnings: $($WarningsCount)" -ForegroundColor Yellow
    Write-Log -Message "  ❌ Invalid PDFs (Deleted): $($InvalidCount)" -ForegroundColor Magenta
    Write-Log -Message "⎯⎯ End of Log File $Script:LogFilePath ⎯⎯" -ForegroundColor Cyan

    # Clean up the script-level variable after the run is complete
    $Script:LogFilePath = $null
}

# ⎯⎯ EXAMPLE USAGE ⎯⎯
# IMPORTANT: Replace "C:\Your\Docs\Folder" with the actual path you want to process.

# Example 1 (Original): Convert files in place, delete original DOCX, skip if PDF exists
# Convert-Docs-And-Validate -SourceDirectory "C:\Your\Docs\Folder" -DeleteOriginalDocx -SkipExistingPdf

# Example 2 (New Feature): Convert files from Source to a separate Output folder
# This maintains the folder structure of "C:\Your\Docs\Folder" inside "C:\Your\PDF\Output"
# Convert-Docs-And-Validate -SourceDirectory "C:\Your\Docs\Folder" -OutputDirectory "C:\Your\PDF\Output"

# Example 3 (Safety Check): Run with -WhatIf to preview all changes without execution
# Convert-Docs-And-Validate -SourceDirectory "C:\Your\Docs\Folder" -DeleteOriginalDocx -WhatIf
