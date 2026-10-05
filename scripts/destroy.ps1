# Tarik hasil eksperimen dari Attacker Node, baru hancurkan infrastruktur.
# Destroy dibatalkan bila log gagal ditarik atau folder hasil kosong.
# Jalankan dari folder scripts/:  .\destroy.ps1
$ErrorActionPreference = "Stop"
$tf      = Join-Path $PSScriptRoot "..\terraform"
$results = Join-Path $PSScriptRoot "..\results"
$key     = "$HOME\.ssh\noisy-neighbor"

$ip = terraform -chdir=$tf output -raw attacker_public_ip
if ($LASTEXITCODE -ne 0 -or -not $ip) { throw "Tidak dapat membaca IP Attacker Node dari output Terraform." }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dest  = Join-Path $results $stamp
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Write-Host "Menarik hasil dari Attacker Node ($ip) ke $dest ..."
scp -i $key -o StrictHostKeyChecking=accept-new -r "ubuntu@${ip}:~/results/*" $dest
if ($LASTEXITCODE -ne 0) {
    Write-Error "Gagal menarik hasil. Destroy DIBATALKAN agar data tidak hilang."
    exit 1
}

$count = (Get-ChildItem -Recurse -File $dest | Measure-Object).Count
if ($count -eq 0) {
    Write-Error "Folder hasil kosong. Destroy DIBATALKAN."
    exit 1
}
Write-Host "$count berkas berhasil ditarik." -ForegroundColor Green

$confirm = Read-Host "Salinan cadangan sudah aman? Ketik 'destroy' untuk menghancurkan infrastruktur"
if ($confirm -ne "destroy") { Write-Host "Dibatalkan."; exit 0 }

terraform -chdir=$tf destroy
Write-Host "Selesai. Cek AWS Console (EC2, EBS, Elastic IP) untuk memastikan tidak ada resource tersisa."
