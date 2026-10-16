param(
    [string]$GradleVersion = "8.7"
)

$ErrorActionPreference = "Stop"
$androidRoot = Join-Path $PSScriptRoot "..\android-collector"
if (-not (Get-Command gradle -ErrorAction SilentlyContinue)) {
    throw "No system Gradle found. Install Gradle $GradleVersion or open android-collector in Android Studio, then rerun this script."
}

Push-Location $androidRoot
try {
    gradle wrapper --gradle-version $GradleVersion --distribution-type bin
} finally {
    Pop-Location
}
