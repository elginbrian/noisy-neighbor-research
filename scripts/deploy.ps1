# Deploy infrastruktur lalu tunggu bootstrap kedua node selesai.
# Jalankan dari folder scripts/:  .\deploy.ps1
$ErrorActionPreference = "Stop"
$tf  = Join-Path $PSScriptRoot "..\terraform"
$key = "$HOME\.ssh\noisy-neighbor"

terraform -chdir=$tf apply
if ($LASTEXITCODE -ne 0) { throw "terraform apply gagal." }

$nodes = @{
    target   = (terraform -chdir=$tf output -raw target_public_ip)
    attacker = (terraform -chdir=$tf output -raw attacker_public_ip)
}

foreach ($name in $nodes.Keys) {
    $ip = $nodes[$name]
    Write-Host "Menunggu bootstrap $name ($ip) ..."
    $ok = $false
    for ($i = 0; $i -lt 60; $i++) {   # maksimal ~10 menit
        $out = ssh -i $key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 ubuntu@$ip `
            "if [ -f /var/log/bootstrap-failed ]; then echo FAILED; elif [ -f /var/log/bootstrap-done ]; then echo DONE; fi" 2>$null
        if ($out -eq "DONE")   { $ok = $true; break }
        if ($out -eq "FAILED") { throw "Bootstrap $name gagal. Cek /var/log/bootstrap.log di $ip." }
        Start-Sleep -Seconds 10
    }
    if (-not $ok) { throw "Bootstrap $name tidak selesai dalam batas waktu." }
    Write-Host "Bootstrap $name selesai." -ForegroundColor Green
}

Write-Host ""
terraform -chdir=$tf output ssh_target
terraform -chdir=$tf output ssh_attacker
