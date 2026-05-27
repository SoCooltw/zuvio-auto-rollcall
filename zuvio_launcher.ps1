$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

function Find-Python {
    $candidates = @(
        @{ Command = "python"; Args = @("--version") },
        @{ Command = "py"; Args = @("-3", "--version") },
        @{ Command = "python3"; Args = @("--version") }
    )

    foreach ($candidate in $candidates) {
        try {
            $null = & $candidate.Command @($candidate.Args) 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
        }
    }

    return $null
}

function Run-Python {
    param(
        [hashtable]$Python,
        [string[]]$PythonArgs
    )

    if ($Python.Command -eq "py") {
        & $Python.Command -3 @PythonArgs
    } else {
        & $Python.Command @PythonArgs
    }
}

function Test-PythonModule {
    param(
        [hashtable]$Python,
        [string]$ModuleName
    )

    Run-Python -Python $Python -PythonArgs @("-c", "import $ModuleName")
    return $LASTEXITCODE -eq 0
}

function Install-Dependencies {
    $installerPath = Join-Path $PSScriptRoot "install_dependencies.ps1"
    if (-not (Test-Path -LiteralPath $installerPath)) {
        return $false
    }

    & $installerPath
    return $LASTEXITCODE -eq 0
}

function Read-Required {
    param([string]$Prompt)

    while ($true) {
        $value = Read-Host $Prompt
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value.Trim()
        }
        Write-Host "Required. Please enter again."
    }
}

function Convert-SecureStringToPlainText {
    param([securestring]$SecureValue)

    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

$scriptPath = Join-Path $PSScriptRoot "zuvio_interactive.py"
$python = Find-Python

if ($null -eq $python) {
    Write-Host ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("5om+5LiN5Yiw5ZWf5YuV55Kw5aKD77yM6KuL5YWI5Z+36KGM44CM56ys5LiA5qyh5L2/55SoLeWuieijneWll+S7ti5iYXTjgI3jgII=")))
    if (-not (Install-Dependencies)) {
        exit 1
    }
    $python = Find-Python
    if ($null -eq $python) {
        exit 1
    }
}

if (-not (Test-PythonModule -Python $python -ModuleName "requests")) {
    Write-Host ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("57y65bCR5b+F6KaB5aWX5Lu277yM5q2j5Zyo5YWI5Z+36KGM5a6J6KOdLi4u")))
    if (-not (Install-Dependencies)) {
        exit 1
    }
    $python = Find-Python
    if (($null -eq $python) -or (-not (Test-PythonModule -Python $python -ModuleName "requests"))) {
        exit 1
    }
}

Run-Python -Python $python -PythonArgs @($scriptPath)
$exitCode = $LASTEXITCODE

exit $exitCode
