<#[
MLO Windows PWA test-package diagnostic.
Run from a PowerShell terminal after extracting your own PWABuilder test package.
Does NOT install certificates or change system security settings.
Example:
  .\tools\windows_pwa_install_diagnostic.ps1 -PackageFolder "$HOME\Downloads\PWABuilder-test"
Add -RunInstaller to invoke install.ps1 in the terminal and capture its output.
]#>
param(
    [Parameter(Mandatory=$true)][string]$PackageFolder,
    [switch]$RunInstaller
)
$ErrorActionPreference = 'Stop'
try { $folder = (Resolve-Path -LiteralPath $PackageFolder).Path }
catch { Write-Error "Folder not found: $PackageFolder. Extract your PWABuilder ZIP first."; exit 1 }
$log = Join-Path $folder 'mlo-windows-install-report.txt'
$lines = @("MLO Windows PWA test installer inspection", "Checked: $(Get-Date -Format o)", "Folder: $folder", "Windows: $([System.Environment]::OSVersion.VersionString)", '')
$files = @(Get-ChildItem -LiteralPath $folder -Recurse -File | Where-Object {
    $_.Extension -in @('.ps1','.exe','.msix','.msixbundle','.appx','.appxbundle','.cer')
})
if ($files.Count -eq 0) { $lines += 'No installer, package or certificate files found. Extract the test ZIP.' }
foreach ($file in $files) {
    $lines += "FILE: $($file.FullName)"
    if ($file.Extension -in @('.exe','.msix','.msixbundle','.appx','.appxbundle')) {
        try {
            $sig = Get-AuthenticodeSignature -LiteralPath $file.FullName
            $lines += "  Signing status: $($sig.Status)"
            $lines += "  Signer: $($sig.SignerCertificate.Subject)"
        } catch { $lines += "  Signature lookup failed: $($_.Exception.Message)" }
    }
}
$lines | Set-Content -Path $log -Encoding utf8
$lines | ForEach-Object { Write-Host $_ }
if ($RunInstaller) {
    $installer = $files | Where-Object {$_.Name -eq 'install.ps1'} | Select-Object -First 1
    if (-not $installer) { Write-Warning 'No install.ps1 found in extracted folder.' }
    else {
        Write-Host "Running: $($installer.FullName)" -ForegroundColor Cyan
        $prior = (Get-Location).Path
        try {
            Set-Location -LiteralPath $installer.DirectoryName
            & $installer.FullName *>&1 | Tee-Object -FilePath $log -Append
            "Installer exit code (when available): $LASTEXITCODE" | Tee-Object -FilePath $log -Append
        } catch { ($_ | Out-String) | Tee-Object -FilePath $log -Append }
        finally { Set-Location -LiteralPath $prior }
    }
}
Write-Host "\nReport written to: $log" -ForegroundColor Green
Write-Host 'If it fails, share the error lines, not certificate private keys or tokens.'
