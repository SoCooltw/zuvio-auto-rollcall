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

function Write-Utf8Base64 {
    param([string]$Text)
    Write-Host ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($Text)))
}

Write-Utf8Base64 "WnV2aW8g6Ieq5YuV6bue5ZCN5Yqp5omLIC0g56ys5LiA5qyh5L2/55So5a6J6KOd"
Write-Host ""

$python = Find-Python
if ($null -eq $python) {
    Write-Utf8Base64 "5om+5LiN5Yiw5ZWf5YuV55Kw5aKD77yM6KuL6IGv57Wh5o+Q5L6b6YCZ5YCL5bel5YW355qE5Lq644CC"
    exit 1
}

Write-Utf8Base64 "5bey5om+5Yiw5ZWf5YuV55Kw5aKD77yM6ZaL5aeL5rqW5YKZ5aWX5Lu2Li4u"
Run-Python -Python $python -PythonArgs @("-m", "ensurepip", "--upgrade")

Write-Host ""
Write-Utf8Base64 "5q2j5Zyo5a6J6KOd5oiW5pu05paw5b+F6KaB5aWX5Lu2Li4u"
Run-Python -Python $python -PythonArgs @("-m", "pip", "install", "--upgrade", "requests")

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Utf8Base64 "5a6J6KOd5aSx5pWX44CC6KuL56K66KqN57ay6Lev5Y+v5Lul5L2/55So77yM5oiW55So57O757Wx566h55CG5ZOh6Lqr5YiG5Z+36KGM44CC"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Utf8Base64 "5a6M5oiQ44CC5LmL5b6M5LiK6Kqy5pmC6KuL6ZuZ5pOK44CM6ZaL5aeL6bue5ZCNLmJhdOOAjeOAgg=="
