param([string]$Destination = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
    throw 'Choose an existing shortcut destination directory.'
}
$shell = New-Object -ComObject WScript.Shell
foreach ($item in @(
    @{ Name = 'SQL Intelligence Agent - Live'; Arguments = 'start --mode live --open-browser' },
    @{ Name = 'SQL Intelligence Agent - Mock'; Arguments = 'start --mode mock --open-browser' },
    @{ Name = 'SQL Intelligence Agent - Stop'; Arguments = 'stop' }
)) {
    $path = Join-Path $Destination ($item.Name + '.lnk')
    if (Test-Path -LiteralPath $path) { throw 'A shortcut already exists; review it before replacing it.' }
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $env:ComSpec
    $shortcut.Arguments = '/k ""' + (Join-Path $projectRoot 'local.cmd') + '" ' + $item.Arguments + '"'
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Description = 'Local Docker Desktop SQL Intelligence Agent. Live questions use Azure OpenAI.'
    $shortcut.Save()
}
Write-Output 'Created Live, Mock and Stop shortcuts. Launch does not submit an inference request.'
