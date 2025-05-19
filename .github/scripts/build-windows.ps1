param (
    [string]$PackageVersion
)

$ErrorActionPreference = "Stop"

$RepoName = "python-astroquery-cli"
$ModuleName = "astroquery_cli"
$CmdName = "aqc"

if (-not $PackageVersion) {
    Write-Error "Error: Package version is not set."
    exit 1
}

Write-Host "Starting Windows packaging for $RepoName version $PackageVersion"

# === 1. Clean up/create directories
if (Test-Path "pkg-win") {
    Remove-Item -Recurse -Force "pkg-win"
}
$InstallDir = "pkg-win\$RepoName-$PackageVersion"
$BinDir = "$InstallDir\bin"
$LibDir = "$InstallDir\lib"
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
New-Item -ItemType Directory -Path $LibDir -Force | Out-Null

# === 2. pip install . --target lib
Write-Host "Installing package into $LibDir ..."
python -m pip install . --no-deps --target $LibDir

# === 3. Generate PyInstaller launcher script
$ExecWrapperScript = @"
import os
import sys
import runpy
script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
lib_dir = os.path.abspath(os.path.join(script_dir, '..', 'lib'))
sys.path.insert(0, lib_dir)
runpy.run_module('$ModuleName.main', run_name='__main__')
"@
$ExecWrapperPath = "pkg-win\exec_wrapper.py"
Set-Content -Path $ExecWrapperPath -Value $ExecWrapperScript

python -m pip install --upgrade pyinstaller

Write-Host "Creating Windows executable with PyInstaller ..."
python -m PyInstaller --onefile --console --name $CmdName --distpath $BinDir $ExecWrapperPath

# Clean up
Remove-Item $ExecWrapperPath
Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
Remove-Item "$CmdName.spec" -ErrorAction SilentlyContinue

# === 4. Generate install.ps1 
$InstallScript = @"
# Installation script for $RepoName $PackageVersion
# Please run this script in PowerShell as Administrator to install to Program Files and update your system PATH

`$ErrorActionPreference = 'Stop'
`$InstallDir = "`$env:ProgramFiles\$RepoName"
if (-not (Test-Path `$InstallDir)) {
    New-Item -ItemType Directory -Path `$InstallDir -Force | Out-Null
}
Copy-Item -Path "bin\*" -Destination `$InstallDir -Recurse -Force
Copy-Item -Path "lib" -Destination `$InstallDir -Recurse -Force

`$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", [EnvironmentVariableTarget]::Machine)
if (-not (`$CurrentPath -like "*`$InstallDir*")) {
    [Environment]::SetEnvironmentVariable(
        "PATH", 
        `$CurrentPath + ";`$InstallDir", 
        [EnvironmentVariableTarget]::Machine
    )
    Write-Host "Added $InstallDir to system PATH. Restart your PowerShell or CMD for changes to take effect."
} else {
    Write-Host "$InstallDir is already in system PATH."
}
Write-Host "Installation completed. You can run '$CmdName' after restarting your shell."
"@
Set-Content -Path "$InstallDir\install.ps1" -Value $InstallScript

# === 5. Generate README.md
$ReadmeContent = @"
# $RepoName $PackageVersion

## Installation

**Recommended:**  
- Right-click \`install.ps1\` and choose "Run with PowerShell as Administrator".
  This will copy files to Program Files and add to your system PATH.

**Manual:**  
- Extract the archive anywhere you like.
- Add the \`bin\` directory to your system PATH,
  or run \`$CmdName.exe\` directly from that folder.

## Usage

After installing, you can run \`$CmdName\` from any PowerShell or Command Prompt window.

## Requirements

- Windows 7 or later
- No additional dependencies (self-contained executable)
"@
Set-Content -Path "$InstallDir\README.md" -Value $ReadmeContent

# === 6. Pack ZIP
$ZipFile = "$RepoName-$PackageVersion-win.zip"
if (Test-Path $ZipFile) { Remove-Item $ZipFile -Force }
Write-Host "Creating $ZipFile ..."
Compress-Archive -Path "$InstallDir\*" -DestinationPath $ZipFile -Force

if (Test-Path $ZipFile) {
    Write-Host "Packaging succeeded: $ZipFile"
    "package_name=$ZipFile" | Out-File -FilePath $env:GITHUB_OUTPUT -Append
    "package_path=$ZipFile" | Out-File -FilePath $env:GITHUB_OUTPUT -Append
} else {
    Write-Error "Error: Packaging failed for $ZipFile"
    exit 1
}
