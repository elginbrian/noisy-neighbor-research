# Deploy infrastruktur lalu tunggu bootstrap kedua node selesai.
# Jalankan dari folder scripts/:  .\deploy.ps1
$ErrorActionPreference = "Stop"
$tf  = Join-Path $PSScriptRoot "..\terraform"
$key = "$HOME\.ssh\noisy-neighbor"

terraform "-chdir=$tf" apply -auto-approve
if ($LASTEXITCODE -ne 0) { throw "terraform apply gagal." }

$nodes = @{
    target   = (terraform "-chdir=$tf" output -raw target_public_ip)
    attacker = (terraform "-chdir=$tf" output -raw attacker_public_ip)
}

foreach ($name in $nodes.Keys) {
    $ip = $nodes[$name]
    Write-Host "Menunggu bootstrap $name ($ip) ..."
    $ok = $false
    $seen = 0   # jumlah baris log yang sudah ditampilkan
    for ($i = 0; $i -lt 60; $i++) {   # maksimal ~10 menit
        $remote = "tail -n +$($seen + 1) /var/log/bootstrap.log 2>/dev/null; " +
                  "if [ -f /var/log/bootstrap-failed ]; then echo __NN_FAILED__; " +
                  "elif [ -f /var/log/bootstrap-done ]; then echo __NN_DONE__; fi"
        $ErrorActionPreference = "Continue"   # stderr ssh (timeout saat boot) bukan error fatal
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
    Write-Host "Bootstrap $name selesai." -ForegroundColor Green
}

Write-Host ""
terraform "-chdir=$tf" output ssh_target
terraform "-chdir=$tf" output ssh_attacker
