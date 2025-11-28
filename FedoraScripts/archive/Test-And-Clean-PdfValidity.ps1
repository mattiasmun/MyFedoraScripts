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

function Test-And-Clean-PdfValidity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true)]
        [Alias('FullName')]
        [string]$PDFPath,

        [Parameter(Mandatory=$false)]
        [bool]$DeleteOnInvalid = $false
    )

    # PROCESS BLOCK allows the function to handle pipeline input (e.g., Get-ChildItem)
    process {
        Write-Host "--- Checking $($PDFPath) ---"

        # --- Nested Deletion Function ---
        function Delete-File {
            param([string]$PathToDelete)
            try {
                Remove-Item -Path $PathToDelete -Force
                Write-Host "🗑️ Successfully deleted invalid file: $PathToDelete" -ForegroundColor Magenta
            } catch {
                Write-Error "Failed to delete file '$PathToDelete': $($_.Exception.Message)"
            }
        }
        # --------------------------------

        # 1. FILE EXISTENCE AND PATH CHECK
        if (-not (Test-Path -Path $PDFPath -PathType Leaf)) {
            Write-Error "File not found or is a directory: $PDFPath"
            # Return InvalidAccess if file can't even be found
            return [PdfValidationStatus]::InvalidAccess
        }

        # --- 2. SIMPLE HEADER CHECK (Robust Stream Read) ---
        $Stream = $null
        try {
            $Stream = [System.IO.File]::OpenRead($PDFPath)
            $HeaderBytes = New-Object byte[] 5

            if ($Stream.Read($HeaderBytes, 0, 5) -lt 5) {
                Write-Host "❌ File too small to be a PDF header (less than 5 bytes)." -ForegroundColor Pink
                if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
                return [PdfValidationStatus]::InvalidAccess
            }

            $Header = [System.Text.Encoding]::ASCII.GetString($HeaderBytes)

            if ($Header -ne "%PDF-") {
                Write-Host "❌ Basic Header Check Failed. Header starts with '$Header', not '%PDF-'." -ForegroundColor Pink
                if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
                return [PdfValidationStatus]::InvalidHeader # Explicit Header Failure
            } else {
                Write-Host "✅ Basic Header Check Passed. Proceeding to structural check..." -ForegroundColor Green
            }

        } catch {
            Write-Error "❌ Error accessing file '$PDFPath': $($_.Exception.Message)"
            if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
            return [PdfValidationStatus]::InvalidAccess # Explicit Access/IO Failure
        } finally {
            if ($Stream) { $Stream.Dispose() }
        }

        # --- 3. QPDF STRUCTURAL CHECK ---
        $QPDFOutput = & qpdf --check $PDFPath 2>&1

        if ($LASTEXITCODE -eq 0) {
            # Status 0: Perfect Success
            Write-Host "✅ Structural Check Passed. PDF is fully valid." -ForegroundColor Green
            return [PdfValidationStatus]::Valid
        }
        elseif ($LASTEXITCODE -eq 3) {
            # Status 3: Success with Warnings
            Write-Host "⚠️ Structural Check Passed with Warnings (Exit Code: 3):" -ForegroundColor Yellow
            if ($QPDFOutput) {
                $QPDFOutput | ForEach-Object { Write-Host "   $_" }
            }
            return [PdfValidationStatus]::ValidWithWarnings # Explicit Warning Status
        }
        else {
            # Status 2 (or other non-success code): Fatal Error/Corruption
            Write-Host "❌ Structural Check Failed. PDF is corrupted (Exit Code: $LASTEXITCODE)." -ForegroundColor Pink
            if ($QPDFOutput) {
                Write-Host "--- QPDF Diagnostic Output ---"
                $QPDFOutput | ForEach-Object { Write-Host "   $_" }
            }

            if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
            return [PdfValidationStatus]::InvalidCorrupt # Explicit Corruption Status
        }
    } # End Process Block
}

# Run this command to load the function into your current session:
# . .\Test-And-Clean-PdfValidity.ps1

# Example usage:

# 1. Check a single file and delete it if invalid
# Test-And-Clean-PdfValidity -PDFPath "C:\Data\Test.pdf" -DeleteOnInvalid $true

# 2. Use with the pipeline (e.g., to check all files in a folder)
# Get-ChildItem -Path "C:\Incoming" -Filter "*.pdf" | Test-And-Clean-PdfValidity

# 3. Run the function
# $Status = Test-And-Clean-PdfValidity -PDFPath "C:\file_to_check.pdf" -DeleteOnInvalid $true

# 4. Check the result
# if ($Status -eq [PdfValidationStatus]::Valid) {
#     Write-Host "File is completely good!"
# } elseif ($Status -eq [PdfValidationStatus]::ValidWithWarnings) {
#     Write-Host "File is usable but needs inspection." -ForegroundColor Yellow
# } elseif ($Status -eq [PdfValidationStatus]::InvalidCorrupt) {
#     Write-Host "FATAL ERROR: File must be discarded." -ForegroundColor Pink
# }
