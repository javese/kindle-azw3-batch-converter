$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$engine = Join-Path $PSScriptRoot 'azw3-engine'
$staging = Join-Path ([IO.Path]::GetTempPath()) ("azw3-engine-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $engine, $staging -Force | Out-Null

function Get-EngineFile($Url, $Destination) {
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

try {
    $kindling = Join-Path $engine 'kindling-cli-windows.exe'
    if (!(Test-Path -LiteralPath $kindling)) {
        $download = Join-Path $staging 'kindling-cli-windows.exe'
        Get-EngineFile 'https://github.com/ciscoriordan/kindling/releases/download/v0.46.2/kindling-cli-windows.exe' $download
        Move-Item -LiteralPath $download -Destination $kindling
    }

    $epub = Join-Path $engine 'epub3-kindle'
    if (!(Test-Path -LiteralPath (Join-Path $epub 'epub3-kindle.exe'))) {
        $download = Join-Path $staging 'epub3-kindle.zip'
        Get-EngineFile 'https://github.com/cbz-tools/Epub3-Kindle/releases/download/v0.5.1/epub3-kindle-v0.5.1-windows-x64.zip' $download
        Expand-Archive -LiteralPath $download -DestinationPath $epub -Force
    }

    if (!(Test-Path -LiteralPath (Join-Path $engine 'KindleUnpack-master\lib\kindleunpack.py'))) {
        $download = Join-Path $staging 'kindleunpack.zip'
        $commit = 'bf0ca6ece4e73494625e7950be3e259b6260774c'
        Get-EngineFile "https://codeload.github.com/kevinhendricks/KindleUnpack/zip/$commit" $download
        Expand-Archive -LiteralPath $download -DestinationPath $staging
        Move-Item -LiteralPath (Join-Path $staging "KindleUnpack-$commit") -Destination (Join-Path $engine 'KindleUnpack-master')
    }

    if (!(Test-Path -LiteralPath (Join-Path $engine 'tkinterdnd2\__init__.py'))) {
        & python -m pip install --disable-pip-version-check --no-compile --target $engine 'tkinterdnd2==0.7.0'
        if ($LASTEXITCODE -ne 0) { throw 'Could not install TkinterDnD2.' }
    }

    Write-Host 'Ready. Open Start AZW3 Converter.cmd.'
}
finally {
    Get-ChildItem -LiteralPath $staging -File | Remove-Item -Force
    if (!(Get-ChildItem -LiteralPath $staging)) {
        Remove-Item -LiteralPath $staging
    }
}
