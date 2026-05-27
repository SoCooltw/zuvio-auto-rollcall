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
    Write-Host "Cannot start. Please contact the person who shared this tool."
    exit 1
}

Run-Python -Python $python -PythonArgs @($scriptPath)
$exitCode = $LASTEXITCODE

exit $exitCode
