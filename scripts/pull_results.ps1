# ==============================================================================
# Menarik Berkas Hasil Eksperimen dari Tester Instance ke Lokal
# Jalankan dari root atau folder scripts:  .\scripts\pull_results.ps1
# ==============================================================================
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tf       = Join-Path $repoRoot "terraform"
$results  = Join-Path $repoRoot "results"
$key      = "$HOME\.ssh\noisy-neighbor"

$ip = terraform "-chdir=$tf" output -raw tester_public_ip 2>$null
if (-not $ip) {
    throw "IP Tester Instance tidak ditemukan di state Terraform. Pastikan infrastruktur aktif."
}

Write-Host "Memeriksa berkas hasil di Tester Instance ($ip)..."
$remoteCount = ssh -i $key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 ubuntu@$ip `
    "find ~/results -type f 2>/dev/null | wc -l" 2>$null

if ([int]$remoteCount -eq 0) {
    Write-Host "Tidak ada berkas di ~/results pada Tester Instance." -ForegroundColor Yellow
    exit 0
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dest  = Join-Path $results $stamp
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Write-Host "Menarik $remoteCount berkas dari Tester Instance ($ip) ke $dest..." -ForegroundColor Cyan
scp -i $key -o StrictHostKeyChecking=accept-new -r "ubuntu@${ip}:~/results/*" $dest

$count = (Get-ChildItem -Recurse -File $dest | Measure-Object).Count
Write-Host "Sukses: $count berkas hasil eksperimen berhasil disimpan ke $dest." -ForegroundColor Green
