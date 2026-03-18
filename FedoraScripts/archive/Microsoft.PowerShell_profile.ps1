# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
# PowerShell Profile Script (Microsoft.PowerShell_profile.ps1)
# This script runs every time PowerShell starts.
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# Starta alltid i användarens hemkatalog
Set-Location $HOME

# ⎯⎯ Helper Functions ⎯⎯

function Find-Exe {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue

    if ($cmd) {
        return $cmd.Source
    } else {
        Write-Warning "Executable '$Name' not found in PATH"
    }
}

function Find-ExecutableDeep {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    $result = Find-Exe $Name
    if ($result) { return $result }

    # 2. Common search locations
    $searchPaths = @(
        "$env:ProgramFiles",
        "${env:ProgramFiles(x86)}",
        "$HOME\AppData\Local",
        "$HOME\AppData\Roaming",
        "$HOME\AppData\Local\Programs",
        "$HOME\AppData\Local\Microsoft\WindowsApps"
    )

    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            $result = Get-ChildItem -Path $path -Filter $Name -Recurse -Depth 4 -ErrorAction SilentlyContinue -File | Select-Object -First 1
            if ($result) {
                return $result.FullName
            }
        }
    }

    Write-Warning "Executable '$Name' not found."
}

function whereis {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    $cmds = Get-Command $Name -All -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty Source

    if (-not $cmds) {
        Write-Warning "$Name not found"
        return
    }

    $i = 0

    foreach ($cmd in $cmds) {

        $version = ""

        try {
            $v = & $cmd --version 2>$null | Select-Object -First 1
            if ($v) { $version = " ($v)" }
        }
        catch {}

        if ($i -eq 0) {
            Write-Host "▶ $cmd$version  [used]" -ForegroundColor Green
        }
        else {
            Write-Host "  $cmd$version" -ForegroundColor DarkGray
        }

        $i++
    }
}

function which-open {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    $path = Find-ExeCached $Name | Select-Object -First 1

    if ([string]::IsNullOrWhiteSpace($path)) {
        Write-Warning "$Name not found"
        return
    }

    $folder = Split-Path $path

    Write-Host "Opening: $folder" -ForegroundColor Cyan

    Start-Process explorer $folder
}

# ⎯⎯ Executable Cache ⎯⎯

$ExeCache = @{}

function Build-ExecutableCache {

    foreach ($dir in ($env:PATH -split ';')) {

        $dir = $dir.Trim()

        if (-not $dir) { continue }
        if (-not (Test-Path $dir)) { continue }

        try {

            foreach ($file in [System.IO.Directory]::EnumerateFiles($dir)) {

                $ext = [System.IO.Path]::GetExtension($file)

                if ($ext -in '.exe','.cmd','.bat') {

                    $name = [System.IO.Path]::GetFileName($file).ToLower()

                    if (-not $ExeCache[$name]) {
                        $ExeCache[$name] = $file
                    }

                }

            }

        }
        catch {}

    }

}

function Find-ExeCached {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    $pattern = $Name.ToLower()

    $matches = $ExeCache.Keys |
           Where-Object { $_ -like "$pattern*" } |
           Sort-Object

    if ($matches) {
        foreach ($m in $matches) {
            $ExeCache[$m]
        }
    } else {
        Write-Warning "$Name not found in executable cache"
    }
}

function tools {
    param([string]$Filter)

    if ($ExeCache.Count -eq 0) {
        Write-Warning "Executable cache is empty. Run refresh-exec-cache."
        return
    }

    $keys = $ExeCache.Keys | Sort-Object

    if ($Filter) {
        $keys = $keys | Where-Object { $_ -like "*$Filter*" }
    }

    $keys |
    ForEach-Object {
        [PSCustomObject]@{
            Tool = $_
            Path = $ExeCache[$_]
        }
    } |
    Sort-Object Tool
}

function Save-ExecutableCache {
    $ExeCache | ConvertTo-Json | Set-Content "$HOME\exe-cache.json"
}

function Load-ExecutableCache {

    $file = "$HOME\exe-cache.json"

    if (Test-Path $file) {

        try {

            $data = Get-Content $file | ConvertFrom-Json

            $global:ExeCache = @{}

            $data.psobject.Properties | ForEach-Object {
                $ExeCache[$_.Name] = $_.Value
            }

            return $true
        }
        catch {
            Write-Warning "Executable cache corrupted. Rebuilding."
        }
    }

    return $false
}

function Get-PathHash {
    $PathString = $env:PATH
    $Bytes = [System.Text.Encoding]::UTF8.GetBytes($PathString)
    $Sha = [System.Security.Cryptography.SHA256]::Create()
    $HashBytes = $Sha.ComputeHash($Bytes)

    # Konvertera bytes till en läsbar sträng (hex)
    $Hash = [System.BitConverter]::ToString($HashBytes) -replace '-'
    return $Hash
}

function Save-PathHash {
    Get-PathHash | Set-Content "$HOME\path-hash.txt"
}

function Load-PathHash {
    $file = "$HOME\path-hash.txt"

    if (Test-Path $file) {
        return Get-Content $file
    }

    return $null
}

function refresh-exec-cache {

    $global:ExeCache.Clear()

    Build-ExecutableCache
    Save-ExecutableCache

    Write-Host "Executable cache rebuilt." -ForegroundColor Green
}

function ftool {

    if ($ExeCache.Count -eq 0) {
        Write-Warning "Executable cache empty."
        return
    }

    $selection = $ExeCache.Keys |
        Sort-Object |
        fzf

    if ($selection) {
        $ExeCache[$selection]
    }
}

function frun {

    $selection = $ExeCache.Keys |
        Sort-Object |
        fzf

    if ($selection) {
        Start-Process $ExeCache[$selection]
    }
}

function fpath {

    $dir = ($env:PATH -split ';') | fzf

    if ($dir) {
        Start-Process explorer $dir
    }
}

function fh {

    Get-History |
    Select-Object -ExpandProperty CommandLine |
    fzf
}

function ff {

    $file = Get-ChildItem -Recurse -File |
        Select-Object -ExpandProperty FullName |
        fzf

    if ($file) {
        $file
    }
}

function fe {

    $file = Get-ChildItem -Recurse -File |
        Select-Object -ExpandProperty FullName |
        fzf

    if ($file) {
        Start-Process $file
    }
}

# ── Better history & autosuggestions ────────────────

Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle InlineView
Set-PSReadLineOption -HistoryNoDuplicates
Set-PSReadLineOption -MaximumHistoryCount 10000

# Search command history with arrow keys
Set-PSReadLineKeyHandler -Key UpArrow   -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward

# ── Useful aliases ──────────────────────────────────

Set-Alias ll Get-ChildItem
Set-Alias which Find-ExeCached

# ── Small utility functions ─────────────────────────

function addpath {
    param([string]$dir)

    if (-not (Test-Path $dir)) {
        Write-Warning "Directory not found: $dir"
        return
    }

    if ($env:PATH -notlike "*$dir*") {
        $env:PATH += ";$dir"
        Write-Host "Added to PATH: $dir" -ForegroundColor Green
    }
    else {
        Write-Host "Already in PATH: $dir" -ForegroundColor DarkGray
    }
}

function path {

    $i = 0

    foreach ($p in ($env:PATH -split ';')) {

        if (Test-Path $p) {
            Write-Host ("{0,2}: {1}" -f $i, $p)
        }
        else {
            Write-Host ("{0,2}: {1}" -f $i, $p) -ForegroundColor Red
        }

        $i++
    }
}

function reload-profile {
    . $PROFILE
    Write-Host "Profile reloaded." -ForegroundColor Green
}

function edit-profile {
    notepad $PROFILE
}

$currentHash = Get-PathHash
$storedHash = Load-PathHash
$loadedCache = Load-ExecutableCache

#Write-Host "Loaded Cache? " $loadedCache ". currentHash: " $currentHash " storedHash: " $storedHash "."

if (-not $loadedCache -or $currentHash -ne $storedHash) {

    Write-Host "Rebuilding executable cache…" -ForegroundColor Gray

    Build-ExecutableCache
    Save-ExecutableCache
    Save-PathHash
}
else {
    Write-Host "Loaded executable cache." -ForegroundColor DarkGray
}

# ⎯⎯ Custom Executable Paths ⎯⎯

$JavaPath = which java.exe
if (-not $JavaPath) {
    $JavaPath = Find-ExecutableDeep java.exe
}
$QPDFPath = which qpdf.exe
if (-not $QPDFPath) {
    $QPDFPath = Find-ExecutableDeep qpdf.exe
}
$RocketPDFPath = which rocketpdf.exe
if (-not $RocketPDFPath) {
    $RocketPDFPath = Find-ExecutableDeep rocketpdf.exe
}
$VeraPDFPath1 = which verapdf-gui.bat
if (-not $VeraPDFPath1) {
    $VeraPDFPath1 = Find-ExecutableDeep verapdf-gui.bat
}
$VeraPDFPath2 = which verapdf.bat
if (-not $VeraPDFPath2) {
    $VeraPDFPath2 = Find-ExecutableDeep verapdf.bat
}

function qpdf {
    if (Test-Path -Path $QPDFPath -PathType Leaf) {
        # The call operator (&) executes the file, and @($args) forwards all parameters.
        & $QPDFPath @($args)
    } else {
        Write-Error "QPDF executable not found at '$QPDFPath'."
    }
}

function rocketpdf {
    if (Test-Path -Path $RocketPDFPath -PathType Leaf) {
        & $RocketPDFPath @($args)
    } else {
        Write-Error "RocketPDF executable not found at '$RocketPDFPath'."
    }
}

# New function for pip that uses python -m pip
function pip {
    python -m pip @($args)
}

function verapdf-gui {
    if (-not (Test-Path -Path $VeraPDFPath1 -PathType Leaf)) {
        Write-Error "VeraPDF JAR not found at '$VeraPDFPath1'. Cannot run VeraPDF."
        return
    }

    $processParams = @{
        FilePath     = $VeraPDFPath1
        WindowStyle  = 'Hidden'
        # Vi skickar med eventuella argument som matats in i funktionen
        ArgumentList = $args
    }
    Start-Process @processParams
}

function verapdf {
    if (-not (Test-Path -Path $VeraPDFPath2 -PathType Leaf)) {
        Write-Error "VeraPDF JAR not found at '$VeraPDFPath2'. Cannot run VeraPDF."
        return
    }

    $processParams = @{
        FilePath     = $VeraPDFPath2
        # Vi skickar med eventuella argument som matats in i funktionen
        ArgumentList = $args
    }
    Start-Process @processParams
}

# ⎯⎯ Set Default Location for Custom Scripts ⎯⎯
$ScriptPath = "$HOME\Program"

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

    Write-Host "⎯⎯ Ready to use 'verapdf-gui', 'verapdf', 'pip' ⎯⎯" -ForegroundColor Cyan

    Write-Host "PowerShell ready." -ForegroundColor Cyan
    Write-Host "Profile: $PROFILE" -ForegroundColor DarkGray
}
