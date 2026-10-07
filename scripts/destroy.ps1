# Tarik hasil eksperimen dari Attacker Node, baru hancurkan infrastruktur.
# - Ada hasil di ~/results      : hasil ditarik; destroy dibatalkan bila penarikan gagal.
# - Tidak ada hasil (kosong)    : beri peringatan, lanjut ke konfirmasi destroy.
# - Attacker tidak bisa dihubungi: destroy dibatalkan, kecuali memakai -Force.
# Jalankan dari folder scripts/:  .\destroy.ps1  [-Force]
param(
    [switch]$Force   # lewati penarikan hasil bila Attacker Node tidak dapat dihubungi
)

$ErrorActionPreference = "Stop"
$tf      = Join-Path $PSScriptRoot "..\terraform"
$results = Join-Path $PSScriptRoot "..\results"
$key     = "$HOME\.ssh\noisy-neighbor"

$ip = terraform "-chdir=$tf" output -raw attacker_public_ip 2>$null
$haveAttacker = ($LASTEXITCODE -eq 0 -and $ip)

if ($haveAttacker) {
    # Cek jumlah berkas di ~/results; keluaran berupa angka, atau gagal bila SSH tidak tersambung
    $ErrorActionPreference = "Continue"
    $remoteCount = ssh -i $key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 ubuntu@$ip `
        "find ~/results -type f 2>/dev/null | wc -l" 2>$null
    $sshExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    if ($sshExit -ne 0) {
        if (-not $Force) {
            Write-Error "Attacker Node ($ip) tidak dapat dihubungi. Destroy DIBATALKAN. Gunakan -Force untuk tetap melanjutkan tanpa menarik hasil."
            exit 1
        }
        Write-Host "PERINGATAN: Attacker Node tidak dapat dihubungi; hasil tidak ditarik (-Force)." -ForegroundColor Yellow
    }
    elseif ([int]$remoteCount -gt 0) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $dest  = Join-Path $results $stamp
        New-Item -ItemType Directory -Force -Path $dest | Out-Null

        Write-Host "Menarik $remoteCount berkas dari Attacker Node ($ip) ke $dest ..."
        scp -i $key -o StrictHostKeyChecking=accept-new -r "ubuntu@${ip}:~/results/*" $dest
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Gagal menarik hasil. Destroy DIBATALKAN agar data tidak hilang."
            exit 1
        }

        $count = (Get-ChildItem -Recurse -File $dest | Measure-Object).Count
        if ($count -eq 0) {
            Write-Error "Folder hasil kosong setelah penarikan. Destroy DIBATALKAN."
            exit 1
        }
        Write-Host "$count berkas berhasil ditarik." -ForegroundColor Green
    }
    else {
        Write-Host "Tidak ada hasil di ~/results pada Attacker Node; tidak ada yang perlu ditarik." -ForegroundColor Yellow
    }
}
else {
    Write-Host "IP Attacker Node tidak ditemukan di state Terraform; melewati penarikan hasil." -ForegroundColor Yellow
}

$confirm = Read-Host "Ketik 'destroy' untuk menghancurkan SELURUH infrastruktur"
if ($confirm -ne "destroy") { Write-Host "Dibatalkan."; exit 0 }

terraform "-chdir=$tf" destroy
Write-Host "Selesai. Cek AWS Console (EC2, EBS, Elastic IP) untuk memastikan tidak ada resource tersisa."
