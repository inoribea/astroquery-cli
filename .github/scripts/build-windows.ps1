param (
    [string]$WheelFilename,
    [string]$PackageVersion
)

$ErrorActionPreference = "Stop"

$RepoName = "python-astroquery-cli"
$ModuleName = "astroquery_cli"
$CmdName = "aqc"

# Validate inputs
if (-not $PackageVersion) {
    Write-Error "Error: Package version is not set."
    exit 1
}

if (-not $WheelFilename) {
    Write-Error "Error: Wheel filename is not set."
    exit 1
}

$WheelFile = "dist/$WheelFilename"
Write-Host "Expecting wheel file at: $WheelFile"

if (-not (Test-Path $WheelFile)) {
    Write-Error "Error: Wheel file '$WheelFile' not found in dist/ directory."
    Write-Host "Contents of dist/ directory:"
    Get-ChildItem -Recurse -Path "dist"
    exit 1
}
Write-Host "Using wheel file: $WheelFile"

Write-Host "Starting Windows packaging for $RepoName version $PackageVersion"

# Clean up and create package directories
if (Test-Path "pkg-win") {
    Remove-Item -Recurse -Force "pkg-win"
}
New-Item -ItemType Directory -Path "pkg-win" | Out-Null

# Detect Python version
$PythonVersion = (python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
Write-Host "Detected Python version: $PythonVersion"

# Create installation directories
$InstallDir = "pkg-win\$RepoName-$PackageVersion"
$BinDir = "$InstallDir\bin"
$SitePackagesDir = "$InstallDir\lib"

New-Item -ItemType Directory -Path $BinDir | Out-Null
New-Item -ItemType Directory -Path $SitePackagesDir | Out-Null

# Install wheel to package directory
Write-Host "Installing wheel $WheelFile to $SitePackagesDir"
python -m pip install --no-deps --target $SitePackagesDir $WheelFile

# Create Windows executable wrapper using PyInstaller
Write-Host "Creating standalone executable wrapper"

# Create a temporary Python script that will be converted to executable
$ExecWrapperScript = @"
import os
import sys
import site
import runpy

# Add the lib directory to the Python path
script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
lib_dir = os.path.abspath(os.path.join(script_dir, '..', 'lib'))
sys.path.insert(0, lib_dir)

# Run the module
runpy.run_module('$ModuleName.main', run_name='__main__')
"@

# Create a temporary script file
$ExecWrapperPath = "pkg-win\exec_wrapper.py"
Set-Content -Path $ExecWrapperPath -Value $ExecWrapperScript

# Install PyInstaller if not already installed
python -m pip install pyinstaller

# Create single-file executable
Write-Host "Creating standalone executable using PyInstaller"
python -m PyInstaller --onefile --console --name $CmdName --distpath $BinDir $ExecWrapperPath

# Clean up temporary files
Remove-Item -Path $ExecWrapperPath
Remove-Item -Recurse -Force -Path "build" -ErrorAction SilentlyContinue
Remove-Item -Path "$CmdName.spec" -ErrorAction SilentlyContinue

# Create an installer script to help users set up PATH
$InstallScript = @"
# Installation script for $RepoName $PackageVersion
# Run this script in PowerShell with administrator privileges to install to Program Files and update PATH

`$ErrorActionPreference = 'Stop'

# Define installation directory in Program Files
`$InstallDir = "`$env:ProgramFiles\$RepoName"

# Create directory if it doesn't exist
if (-not (Test-Path `$InstallDir)) {
    Write-Host "Creating directory `$InstallDir"
    New-Item -ItemType Directory -Path `$InstallDir -Force | Out-Null
}

# Copy files
Write-Host "Copying files to `$InstallDir"
Copy-Item -Path "bin\*" -Destination `$InstallDir -Recurse -Force
Copy-Item -Path "lib" -Destination `$InstallDir -Recurse -Force

# Add to PATH if not already there
`$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", [EnvironmentVariableTarget]::Machine)
if (-not (`$CurrentPath -like "*`$InstallDir*")) {
    Write-Host "Adding `$InstallDir to system PATH"
    [Environment]::SetEnvironmentVariable(
        "PATH", 
        `$CurrentPath + ";`$InstallDir", 
        [EnvironmentVariableTarget]::Machine
    )
    Write-Host "PATH updated. Changes will take effect after restarting your PowerShell/CMD sessions."
} else {
    Write-Host "`$InstallDir is already in PATH."
}

Write-Host "Installation completed successfully. You can run '$CmdName' from any PowerShell or Command Prompt window (after restarting it)."
"@

Set-Content -Path "$InstallDir\install.ps1" -Value $InstallScript

# Create a basic README file
$ReadmeContent = @"
# $RepoName $PackageVersion

## Quick Installation

1. **Easy Install (Recommended)**: 
   - Right-click on `install.ps1` and select "Run with PowerShell as Administrator"
   - This will install to Program Files and add to your system PATH

## Manual Installation

1. Extract this archive to any directory
2. Add the directory containing `$CmdName.exe` to your PATH, or call it directly

## Usage

Once installed, you can run \`$CmdName\` from any PowerShell or Command Prompt window.

## Requirements

- Windows 7 or later
- No additional requirements (the executable is self-contained)
"@

Set-Content -Path "$InstallDir\README.md" -Value $ReadmeContent

# Create a ZIP package
$ZipFile = "$RepoName-$PackageVersion-win.zip"
Write-Host "Creating ZIP package: $ZipFile"
Compress-Archive -Path $InstallDir\* -DestinationPath $ZipFile -Force

if (Test-Path $ZipFile) {
    Write-Host "Successfully created Windows package: $ZipFile"
    "package_name=$ZipFile" | Out-File -FilePath $env:GITHUB_OUTPUT -Append
    "package_path=$ZipFile" | Out-File -FilePath $env:GITHUB_OUTPUT -Append
} else {
    Write-Error "Error: Failed to create Windows package $ZipFile"
    exit 1
}

