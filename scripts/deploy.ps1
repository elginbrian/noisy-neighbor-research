# ==============================================================================
# Deploy Infrastruktur & Verifikasi Komponen Eksperimen Noisy Neighbor
# Jalankan dari root atau folder scripts:  .\scripts\deploy.ps1
# ==============================================================================
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tf       = Join-Path $repoRoot "terraform"
$key      = "$HOME\.ssh\noisy-neighbor"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [1/5] Menerapkan Konfigurasi Terraform (AWS EC2 & Jaringan)     " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

terraform "-chdir=$tf" apply -auto-approve
if ($LASTEXITCODE -ne 0) { throw "terraform apply gagal." }

$targetPublicIp  = (terraform "-chdir=$tf" output -raw target_public_ip)
$targetPrivateIp = (terraform "-chdir=$tf" output -raw target_private_ip)
$testerPublicIp  = (terraform "-chdir=$tf" output -raw tester_public_ip)
$testerPrivateIp = (terraform "-chdir=$tf" output -raw tester_private_ip)

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [2/5] Menunggu Bootstrap Selesai pada Kedua Instance            " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$nodes = @{
    "Target Instance" = $targetPublicIp
    "Tester Instance" = $testerPublicIp
}

foreach ($name in $nodes.Keys) {
    $ip = $nodes[$name]
    Write-Host "Menunggu bootstrap $name ($ip) ..."
    $ok = $false
    $seen = 0
    for ($i = 0; $i -lt 60; $i++) {   # maksimal ~10 menit
        $remote = "tail -n +$($seen + 1) /var/log/bootstrap.log 2>/dev/null; " +
                  "if [ -f /var/log/bootstrap-failed ]; then echo __NN_FAILED__; " +
                  "elif [ -f /var/log/bootstrap-done ]; then echo __NN_DONE__; fi"
        $ErrorActionPreference = "Continue"
        $lines = @(ssh -i $key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 ubuntu@$ip $remote 2>$null)
        $sshExit = $LASTEXITCODE
        $ErrorActionPreference = "Stop"

        if ($sshExit -ne 0 -and $lines.Count -eq 0) {
            Write-Host "  [$name] belum dapat dihubungi, mencoba lagi ..." -ForegroundColor DarkYellow
        }

        $status = $null
        foreach ($line in $lines) {
            if ($line -eq "__NN_DONE__")       { $status = "DONE" }
            elseif ($line -eq "__NN_FAILED__") { $status = "FAILED" }
            else {
                $seen++
                Write-Host "  [$name] $line" -ForegroundColor DarkGray
            }
        }

        if ($status -eq "DONE")   { $ok = $true; break }
        if ($status -eq "FAILED") { throw "Bootstrap $name gagal. Cek /var/log/bootstrap.log di $ip." }
        Start-Sleep -Seconds 10
    }
    if (-not $ok) { throw "Bootstrap $name tidak selesai dalam batas waktu." }
    Write-Host "  -> Bootstrap $name SELESAI." -ForegroundColor Green
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [3/5] Sinkronisasi Berkas Eksperimen ke Instance                " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

function Sync-DirectoryCached($localDir, $remoteIp, $remoteName) {
    $files = Get-ChildItem -Recurse -File $localDir | Sort-Object FullName
    $sb = [System.Text.StringBuilder]::new()
    foreach ($f in $files) {
        [void]$sb.Append("$($f.Name):$($f.Length):$($f.LastWriteTimeUtc.Ticks);")
    }
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $localHash = [System.BitConverter]::ToString($md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($sb.ToString()))).Replace("-","").ToLower()

    $ErrorActionPreference = "Continue"
    $rawHash = @(ssh -i $key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 ubuntu@$remoteIp "cat /home/ubuntu/.hash_$remoteName 2>/dev/null")
    $remoteHash = ($rawHash -join "").Trim()
    $ErrorActionPreference = "Stop"

    if ($remoteHash -eq $localHash) {
        Write-Host "  -> [$remoteName] Tidak ada perubahan berkas, melewati unggahan." -ForegroundColor DarkGray
        return $false
    } else {
        Write-Host "  -> [$remoteName] Mengunggah pembaruan berkas..." -ForegroundColor DarkYellow
        scp -r -i $key -o StrictHostKeyChecking=accept-new $localDir "ubuntu@${remoteIp}:/home/ubuntu/"
        ssh -i $key ubuntu@$remoteIp "echo $localHash > /home/ubuntu/.hash_$remoteName"
        return $true
    }
}

Write-Host "Memeriksa sinkronisasi berkas ke Target Instance ($targetPublicIp)..."
Sync-DirectoryCached "$repoRoot\apps" $targetPublicIp "apps"
Sync-DirectoryCached "$repoRoot\monitoring" $targetPublicIp "monitoring"

Write-Host "Memeriksa sinkronisasi berkas ke Tester Instance ($testerPublicIp)..."
Sync-DirectoryCached "$repoRoot\jmeter" $testerPublicIp "jmeter"
Sync-DirectoryCached "$repoRoot\orchestrator" $testerPublicIp "orchestrator"

# Periksa SSH key di Tester Instance
$ErrorActionPreference = "Continue"
$rawKey = @(ssh -i $key -o StrictHostKeyChecking=accept-new ubuntu@$testerPublicIp "test -s /home/ubuntu/.ssh/noisy-neighbor && echo YES || echo NO")
$keyCheck = ($rawKey -join "").Trim()
$ErrorActionPreference = "Stop"

if ($keyCheck -eq "YES") {
    Write-Host "  -> [SSH Key] Sudah ada di Tester Instance, melewati salinan." -ForegroundColor DarkGray
} else {
    Write-Host "  -> [SSH Key] Menyalin SSH key ke Tester Instance..." -ForegroundColor DarkYellow
    scp -i $key -o StrictHostKeyChecking=accept-new $key "ubuntu@${testerPublicIp}:/home/ubuntu/.ssh/noisy-neighbor"
    ssh -i $key ubuntu@$testerPublicIp "chmod 600 ~/.ssh/noisy-neighbor && chmod +x /home/ubuntu/jmeter/run_test.sh"
}

Write-Host "  -> Seluruh berkas siap dan terverifikasi." -ForegroundColor Green

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [4/5] Membangun Image & Verifikasi Kesiapan Komponen           " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

Write-Host "Memeriksa container image nn-victim dan nn-aggressor di Target Instance..."
$buildScript = @'
set -e
NEED_BUILD=0
if ! docker image inspect nn-victim:latest >/dev/null 2>&1 || ! docker image inspect nn-aggressor:latest >/dev/null 2>&1; then
    NEED_BUILD=1
elif [ ! -f /tmp/.nn_docker_verified ] || [ /home/ubuntu/.hash_apps -nt /tmp/.nn_docker_verified 2>/dev/null ]; then
    NEED_BUILD=1
fi

if [ "$NEED_BUILD" -eq 1 ]; then
    echo "Membangun container image nn-victim dan nn-aggressor..."
    docker build -t nn-victim:latest /home/ubuntu/apps/victim >/dev/null
    docker build -t nn-aggressor:latest /home/ubuntu/apps/aggressor >/dev/null
    echo "[OK] Docker images berhasil dibangun."

    # Smoke test kesiapan container
    docker run -d --name nn-victim-probe -p 80:80 nn-victim:latest >/dev/null
    docker run -d --name nn-aggressor-probe -p 8000:8000 nn-aggressor:latest >/dev/null
    sleep 2
    curl -s -f http://localhost:80/health >/dev/null && echo "[OK] Victim container merespons /health."
    curl -s -f http://localhost:8000/health >/dev/null && echo "[OK] Aggressor container merespons /health."
    docker rm -f nn-victim-probe nn-aggressor-probe >/dev/null
    touch /tmp/.nn_docker_verified
else
    echo "[OK] Container image sudah tersedia dan terverifikasi (skip rebuild)."
fi
'@
$buildScript | ssh -i $key ubuntu@$targetPublicIp "bash -s"

Write-Host "Memverifikasi Apache JMeter dan koneksi SSH internal di Tester Instance..."
$verifyTesterScript = @"
set -e
/opt/jmeter/bin/jmeter -v | head -n 2
ssh -i ~/.ssh/noisy-neighbor -o StrictHostKeyChecking=no ubuntu@$targetPrivateIp "docker --version" >/dev/null
echo "[OK] Tester terhubung ke Target via IP privat: $targetPrivateIp"

# Memastikan direktori results dan Dashboard Web aktif di latar belakang (port 8080)
mkdir -p /home/ubuntu/results
if pgrep -f "orchestrator/dashboard.py" >/dev/null; then
    echo "[OK] Dashboard Web sudah aktif di port 8080."
else
    nohup python3 /home/ubuntu/orchestrator/dashboard.py --port 8080 --results-dir /home/ubuntu/results >/home/ubuntu/dashboard.log 2>&1 &
    sleep 1
    curl -s -f http://localhost:8080/ >/dev/null && echo "[OK] Dashboard Web aktif di port 8080."
fi
"@
$verifyTesterScript | ssh -i $key ubuntu@$testerPublicIp "bash -s"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [5/5] STATUS: SELURUH KOMPONEN SIAP DIJALANKAN!                " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Target Instance IP : Publik = $targetPublicIp | Privat = $targetPrivateIp"
Write-Host "Tester Instance IP : Publik = $testerPublicIp | Privat = $testerPrivateIp"
Write-Host "Dashboard Web URL  : http://${testerPublicIp}:8080" -ForegroundColor Cyan
Write-Host "                     (Buka di browser untuk memantau progres & unduh .zip)" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "Pilih aksi yang ingin dijalankan sekarang:" -ForegroundColor Yellow
Write-Host " [1] Jalankan Pilot Study (16 sel x 1 replikasi)" -ForegroundColor White
Write-Host " [2] Jalankan Single Cell Test (Sel 1 Kontrol - Tanpa Limit)" -ForegroundColor White
Write-Host " [3] Jalankan Single Cell Test (Sel 16 - Limit Paling Ketat)" -ForegroundColor White
Write-Host " [4] Jalankan Full Experiment (80 sesi acak)" -ForegroundColor White
Write-Host " [0] Selesai / Keluar (Infrastruktur tetap aktif, uji coba manual nanti)" -ForegroundColor Gray
Write-Host ""

$pilihan = Read-Host "Masukkan nomor pilihan [0-4]"

switch ($pilihan) {
    "1" {
        Write-Host "`nMemulai Pilot Study dari Tester Instance..." -ForegroundColor Green
        ssh -t -i $key ubuntu@$testerPublicIp "python3 /home/ubuntu/orchestrator/runner.py --target-ip $targetPrivateIp --mode pilot"
    }
    "2" {
        Write-Host "`nMemulai pengujian Sel 1 (Kontrol)..." -ForegroundColor Green
        ssh -t -i $key ubuntu@$testerPublicIp "python3 /home/ubuntu/orchestrator/runner.py --target-ip $targetPrivateIp --mode single --cell 1"
    }
    "3" {
        Write-Host "`nMemulai pengujian Sel 16 (Limit Ketat)..." -ForegroundColor Green
        ssh -t -i $key ubuntu@$testerPublicIp "python3 /home/ubuntu/orchestrator/runner.py --target-ip $targetPrivateIp --mode single --cell 16"
    }
    "4" {
        Write-Host "`nMemulai Full Experiment 80 Sesi..." -ForegroundColor Green
        ssh -t -i $key ubuntu@$testerPublicIp "python3 /home/ubuntu/orchestrator/runner.py --target-ip $targetPrivateIp --mode full"
    }
    Default {
        Write-Host "`nInfrastruktur aktif dan siap digunakan kapan saja." -ForegroundColor Cyan
        Write-Host "Perintah SSH manual:"
        Write-Host "  Target : ssh -i $key ubuntu@$targetPublicIp"
        Write-Host "  Tester : ssh -i $key ubuntu@$testerPublicIp"
        Write-Host "Untuk menjalankan orkestrator manual di Tester:"
        Write-Host "  python3 /home/ubuntu/orchestrator/runner.py --target-ip $targetPrivateIp --mode pilot"
    }
}
