# make_dist.ps1 - Package the app using git archive to avoid including secrets

# Ensure we're in the repository root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path "$ScriptDir\.."

# Output file name
$Output = "dist.zip"

Write-Host "Creating distributable archive: $Output"
# git archive respects .gitignore, so cache/*.db, data/*.db, and *.log won't be included.
git archive HEAD -o $Output

Write-Host "Packaging complete."
