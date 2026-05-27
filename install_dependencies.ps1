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

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Install-PythonFromPythonOrg {
    $version = "3.12.10"
    $processorArch = [Environment]::GetEnvironmentVariable("PROCESSOR_ARCHITECTURE")
    $installerName = if ($processorArch -eq "ARM64") {
        "python-$version-arm64.exe"
    } elseif ([Environment]::Is64BitOperatingSystem) {
        "python-$version-amd64.exe"
    } else {
        "python-$version.exe"
    }
    $url = "https://www.python.org/ftp/python/$version/$installerName"
    $installer = Join-Path $env:TEMP $installerName

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Write-Utf8Base64 "5q2j5Zyo5LiL6LyJIFB5dGhvbiDlrpjmlrnlronoo53mqpQuLi4="
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        & $installer /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 SimpleInstall=1
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        Refresh-Path
        return $true
    } catch {
        return $false
    }
}

function Install-Python {
    $winget = Get-Command "winget" -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        Write-Utf8Base64 "5om+5LiN5YiwIHdpbmdldO+8jOaUueeUqCBweXRob24ub3JnIOWumOaWueWuieijneaqlC4uLg=="
        return Install-PythonFromPythonOrg
    }

    & $winget.Source install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        return Install-PythonFromPythonOrg
    }

    Refresh-Path
    return $true
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
    Write-Utf8Base64 "5om+5LiN5YiwIFB5dGhvbiDllZ/li5XnkrDlooPvvIzmraPlnKjlmJfoqaboh6rli5Xlronoo50gUHl0aG9uLi4u"
    if (-not (Install-Python)) {
        Write-Utf8Base64 "UHl0aG9uIOWuieijneWkseaVl+OAguiri+eiuuiqjee2sui3r+WPr+eUqO+8jOaIluaJi+WLleWuieijnSBQeXRob24g5b6M5YaN6YeN5paw5Z+36KGM44CC"
        exit 1
    }

    $python = Find-Python
    if ($null -eq $python) {
        Write-Utf8Base64 "UHl0aG9uIOWuieijneWkseaVl+OAguiri+eiuuiqjee2sui3r+WPr+eUqO+8jOaIluaJi+WLleWuieijnSBQeXRob24g5b6M5YaN6YeN5paw5Z+36KGM44CC"
        exit 1
    }
}

Write-Utf8Base64 "5bey5om+5YiwIFB5dGhvbu+8mumWi+Wni+a6luWCmeWll+S7ti4uLg=="
Write-Utf8Base64 "5q2j5Zyo56K66KqNIHBpcCDlj6/nlKguLi4="
Run-Python -Python $python -PythonArgs @("-m", "ensurepip", "--upgrade")

Write-Host ""
Write-Utf8Base64 "5q2j5Zyo5a6J6KOd5oiW5pu05paw5b+F6KaB5aWX5Lu2IHJlcXVlc3RzLi4u"
Run-Python -Python $python -PythonArgs @("-m", "pip", "install", "--upgrade", "requests")

if ($LASTEXITCODE -ne 0) {
    Run-Python -Python $python -PythonArgs @("-m", "pip", "install", "--user", "--upgrade", "requests")
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Utf8Base64 "5a6J6KOd5aSx5pWX44CC6KuL56K66KqN57ay6Lev5Y+v5Lul5L2/55So77yM5oiW55So57O757Wx566h55CG5ZOh6Lqr5YiG5Z+36KGM44CC"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Utf8Base64 "5a6M5oiQ44CC5LmL5b6M5LiK6Kqy5pmC6KuL6ZuZ5pOK44CM6ZaL5aeL6bue5ZCNLmJhdOOAjeOAgg=="
