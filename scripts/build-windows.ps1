# Builds the native Windows app (WPF, .NET 8) as one self-contained exe per architecture:
#   dist/windows/win-x64/UsageMonitor.exe and dist/windows/win-arm64/UsageMonitor.exe
# Needs the .NET 8 SDK (it also runs on macOS and Linux with PowerShell 7). The same, by hand:
#   dotnet publish windows/UsageMonitor -c Release -r win-x64 -o dist/windows/win-x64
# -Backend copies a standalone usage.exe (scripts/build-standalone.sh, built on Windows) next to each exe;
# the app looks for it there before the PATH. Only copy one that matches the architecture.
param(
    [string[]]$Runtime = @('win-x64', 'win-arm64'),
    [string]$Backend
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
foreach ($rid in $Runtime) {
    $out = Join-Path $root "dist/windows/$rid"
    dotnet publish (Join-Path $root 'windows/UsageMonitor') -c Release -r $rid -o $out -nologo
    if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed for $rid" }
    if ($Backend) {
        # The standalone build is a folder: usage.exe needs its _internal folder next to it.
        $exe = if (Test-Path $Backend -PathType Container) { Join-Path $Backend 'usage.exe' } else { $Backend }
        if (-not (Test-Path $exe -PathType Leaf)) { throw "no usage.exe at $Backend" }
        Copy-Item $exe (Join-Path $out 'usage.exe') -Force
        $internal = Join-Path (Split-Path -Parent $exe) '_internal'
        if (Test-Path $internal) { Copy-Item $internal $out -Recurse -Force }
    }
    Join-Path $out 'UsageMonitor.exe'
}
