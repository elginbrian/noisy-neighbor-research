# ==============================================================================
# Monitor Status Pengujian & Live Log pada Tester Instance (AWS)
# Jalankan dari root atau folder scripts:  .\scripts\monitor.ps1
# ==============================================================================
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tf       = Join-Path $repoRoot "terraform"
$key      = "$HOME\.ssh\noisy-neighbor"

$ip = terraform "-chdir=$tf" output -raw tester_public_ip 2>$null
if (-not $ip) {
    throw "IP Tester Instance tidak ditemukan di state Terraform. Pastikan infrastruktur aktif."
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " MONITOR STATUS PENGUJIAN - $ip" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$ErrorActionPreference = "Continue"
$chk = @(ssh -n -i $key -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=5 ubuntu@$ip "tmux has-session -t orchestrator 2>/dev/null && echo RUNNING || echo STOPPED")
$status = ($chk -join "").Trim()

$stateJson = @(ssh -n -i $key -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=5 ubuntu@$ip "cat /home/ubuntu/results/state.json 2>/dev/null")
$stateRaw = $stateJson -join "`n"
$ErrorActionPreference = "Stop"

$stateObj = $null
if ($stateRaw) {
    try { $stateObj = $stateRaw | ConvertFrom-Json } catch {}
}

if ($status -eq "RUNNING") {
    Write-Host "Status Pengujian : " -NoNewline
    Write-Host "SEDANG BERJALAN" -ForegroundColor Green
    if ($stateObj) {
        Write-Host "Mode Eksekusi    : $($stateObj.mode)" -ForegroundColor White
        Write-Host "Progres Sesi     : $($stateObj.completed_count) / $($stateObj.total_sessions) sesi" -ForegroundColor Cyan
        if ($stateObj.current_session) {
            Write-Host "Sesi Aktif       : $($stateObj.current_session.session_id) - $($stateObj.current_session.cell_name)" -ForegroundColor Yellow
            Write-Host "Batas CPU/RAM    : CPU $($stateObj.current_session.cpus) | RAM $($stateObj.current_session.memory)" -ForegroundColor DarkGray
        }
        Write-Host "Tahap Terkini    : $($stateObj.current_stage)" -ForegroundColor White
    }
} else {
    Write-Host "Status Pengujian : " -NoNewline
    Write-Host "TIDAK AKTIF / SELESAI" -ForegroundColor DarkGray
    if ($stateObj) {
        Write-Host "Status Terakhir  : $($stateObj.status)" -ForegroundColor White
        Write-Host "Hasil Tersimpan  : $($stateObj.completed_count) sesi di ~/results" -ForegroundColor Green
    }
}

Write-Host "Web Dashboard    : http://${ip}:8080" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pilihan aksi:" -ForegroundColor Yellow
Write-Host " [1] Live Log" -ForegroundColor White
Write-Host " [2] Attach Tmux" -ForegroundColor White
Write-Host " [3] Buka Web Dashboard" -ForegroundColor White
Write-Host " [4] Tarik Hasil Eksperimen" -ForegroundColor White
if ($status -eq "RUNNING") {
    Write-Host " [5] Hentikan Pengujian" -ForegroundColor Red
}
Write-Host " [0] Keluar" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Masukkan pilihan [0-5]"
switch ($choice) {
    "1" {
        Write-Host "`nMenampilkan log... Tekan Ctrl+C untuk kembali`n" -ForegroundColor DarkGray
        ssh -t -i $key ubuntu@$ip "tail -f -n 50 /home/ubuntu/orchestrator.log"
    }
    "2" {
        Write-Host "`nMenghubungkan ke tmux... Tekan Ctrl+B lalu D untuk keluar`n" -ForegroundColor DarkGray
        ssh -t -i $key ubuntu@$ip "tmux attach -t orchestrator"
    }
    "3" {
        Start-Process "http://${ip}:8080"
    }
    "4" {
        & (Join-Path $PSScriptRoot "pull_results.ps1")
    }
    "5" {
        $confirm = Read-Host "Yakin ingin menghentikan pengujian? [y/N]"
        if ($confirm -match "^[Yy]") {
            Write-Host "Menghentikan pengujian..." -ForegroundColor Red
            ssh -n -i $key -o StrictHostKeyChecking=accept-new -o BatchMode=yes ubuntu@$ip "tmux kill-session -t orchestrator 2>/dev/null; pkill -f 'runner.py' 2>/dev/null || true"
            Write-Host "Pengujian dihentikan." -ForegroundColor Green
        }
    }
    Default {}
}
