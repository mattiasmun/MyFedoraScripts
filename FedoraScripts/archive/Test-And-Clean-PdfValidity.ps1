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
            return $false
        }

        # --- 2. SIMPLE HEADER CHECK (Robust Stream Read) ---
        $Stream = $null
        try {
            # Open the file stream for reading
            $Stream = [System.IO.File]::OpenRead($PDFPath)
            $HeaderBytes = New-Object byte[] 5
            
            # Read exactly 5 bytes from the stream
            if ($Stream.Read($HeaderBytes, 0, 5) -lt 5) {
                Write-Host "❌ File too small to be a PDF header (less than 5 bytes)." -ForegroundColor Pink
                if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
                return $false
            }

            # Convert the bytes to an ASCII string for comparison
            $Header = [System.Text.Encoding]::ASCII.GetString($HeaderBytes)

            if ($Header -ne "%PDF-") {
                Write-Host "❌ Basic Header Check Failed. Header starts with '$Header', not '%PDF-'." -ForegroundColor Pink
                if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
                return $false
            } else {
                Write-Host "✅ Basic Header Check Passed. Proceeding to structural check..." -ForegroundColor Green
            }

        } catch {
            # Error accessing the file (e.g., permission denied, file locked).
            Write-Error "❌ Error accessing file '$PDFPath': $($_.Exception.Message)"
            if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
            return $false
        } finally {
            # Ensure the stream is always closed, even if errors occur
            if ($Stream) { $Stream.Dispose() }
        }
        
        # --- 3. QPDF STRUCTURAL CHECK ---

        # Run qpdf --check and capture output/errors.
        $QPDFOutput = & qpdf --check $PDFPath 2>&1

        # Check the exit code explicitly for the three defined statuses (0, 3, 2)
        if ($LASTEXITCODE -eq 0) {
            # Status 0: Perfect Success (File is clean)
            Write-Host "✅ Structural Check Passed. PDF is fully valid." -ForegroundColor Green
            return $true
        }
        elseif ($LASTEXITCODE -eq 3) {
            # Status 3: Success with Warnings (File is usable but imperfect)
            Write-Host "⚠️ Structural Check Passed with Warnings (Exit Code: 3):" -ForegroundColor Yellow
            # Display the warnings captured in the output stream
            if ($QPDFOutput) {
                $QPDFOutput | ForEach-Object { Write-Host "   $_" }
            }
            # Since warnings are recoverable, we still return true
            return $true
        }
        else {
            # Status 2 (or any other non-zero/non-three code): Fatal Error/Corruption
            Write-Host "❌ Structural Check Failed. PDF is corrupted (Exit Code: $LASTEXITCODE)." -ForegroundColor Pink
            if ($QPDFOutput) {
                Write-Host "--- QPDF Diagnostic Output ---"
                $QPDFOutput | ForEach-Object { Write-Host "   $_" }
            }

            # DELETE THE FILE IF REQUESTED
            if ($DeleteOnInvalid) { Delete-File -PathToDelete $PDFPath }
            return $false
        }
    } # End Process Block
}

# Run this command to load the function into your current session:
# . .\Test-And-Clean-PdfValidity.ps1

# Example usage:

# Check a single file and delete it if invalid
# Test-And-Clean-PdfValidity -PDFPath "C:\Data\Test.pdf" -DeleteOnInvalid $true

# Use with the pipeline (e.g., to check all files in a folder)
# Get-ChildItem -Path "C:\Incoming" -Filter "*.pdf" | Test-And-Clean-PdfValidity
