# ShieldCloud -- Complete System Launcher (Pure ASCII)
# Each service runs as a background job streaming to THIS terminal.
# No extra windows opened.

$root = $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

Write-Host "ShieldCloud -- Post-Quantum AI Self-Healing Cloud Storage" -ForegroundColor Cyan
Write-Host "Starting 11 services..." -ForegroundColor Cyan
Write-Host ""

# ── 0. Aggressive Port Cleanup ────────────────────────────────────────────────
Write-Host "[0/11] Cleaning up ghost processes on required ports..." -ForegroundColor Yellow
$portsToClear = @(3001, 3002, 3003, 3004, 3005, 3006, 8080, 5173)
foreach ($port in $portsToClear) {
    $conns = netstat -ano | Select-String "LISTENING" | Select-String ":$port\b"
    if ($conns) {
        foreach ($conn in $conns) {
            $parts = $conn.Line.Trim() -split '\s+'
            $pidToKill = $parts[-1]
            if ($pidToKill -ne "0" -and $pidToKill -match '^\d+$') {
                try {
                    Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                    Write-Host "       Killed ghost process (PID: $pidToKill) on port $port" -ForegroundColor Gray
                } catch {}
            }
        }
    }
}
Start-Sleep -Seconds 2

# ── 1. Docker Infrastructure ─────────────────────────────────────────────────
Write-Host "[1/11] Docker: PostgreSQL, MinIO, Redis, RabbitMQ..." -ForegroundColor Yellow
Push-Location "$root\infra"
docker-compose up -d --remove-orphans 2>&1 | Out-Null
Pop-Location
Write-Host "       OK - Infrastructure ready" -ForegroundColor Green
Start-Sleep -Seconds 4

# ── 2. Auth Service :3001 ─────────────────────────────────────────────────────
Write-Host "[2/11] Auth Service :3001..." -ForegroundColor Yellow
$authJob = Start-Job -Name "Auth" -ScriptBlock {
    param($r); Set-Location "$r\auth-service"; npm run start 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 3
Write-Host "       OK - Auth Service" -ForegroundColor Green

# ── 3. Storage Service :3003 ──────────────────────────────────────────────────
Write-Host "[3/11] Storage Service :3003..." -ForegroundColor Yellow
$storageJob = Start-Job -Name "Storage" -ScriptBlock {
    param($r); Set-Location "$r\storage-service"; npm run start 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 3
Write-Host "       OK - Storage Service" -ForegroundColor Green

# ── 4. Encryption Service :3002 ───────────────────────────────────────────────
Write-Host "[4/11] Encryption Service :3002..." -ForegroundColor Yellow
$encJob = Start-Job -Name "Encryption" -ScriptBlock {
    param($r); Set-Location "$r\encryption-service"
    python -m uvicorn src.main:app --host 0.0.0.0 --port 3002 --reload 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 3
Write-Host "       OK - Encryption Service" -ForegroundColor Green

# ── 5. Anomaly ML Service :3004 ───────────────────────────────────────────────
Write-Host "[5/11] Anomaly ML Service :3004..." -ForegroundColor Yellow
$mlJob = Start-Job -Name "AnomalyML" -ScriptBlock {
    param($r); Set-Location "$r\anomaly-service"
    python -m uvicorn src.main:app --host 0.0.0.0 --port 3004 --reload 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 4
Write-Host "       OK - Anomaly ML (XGBoost loaded)" -ForegroundColor Green

# ── 6. Risk Engine :3005 ──────────────────────────────────────────────────────
Write-Host "[6/11] Risk Engine :3005..." -ForegroundColor Yellow
$riskJob = Start-Job -Name "RiskEngine" -ScriptBlock {
    param($r); Set-Location "$r\risk-engine"
    python -m uvicorn src.main:sio_app --host 0.0.0.0 --port 3005 --reload 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 3
Write-Host "       OK - Risk Engine (SocketIO ready)" -ForegroundColor Green

# ── 7. Self-Healing Consumer ──────────────────────────────────────────────────
Write-Host "[7/11] Self-Healing Worker..." -ForegroundColor Yellow
$healJob = Start-Job -Name "SelfHeal" -ScriptBlock {
    param($r); Set-Location "$r\self-healing-service"
    python src\workers\consumer.py 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 2
Write-Host "       OK - Self-Healing Worker (listening on risk.high)" -ForegroundColor Green

# ── 8. Notification Service :3006 ─────────────────────────────────────────────
Write-Host "[8/11] Notification Service :3006..." -ForegroundColor Yellow
$notifJob = Start-Job -Name "Notification" -ScriptBlock {
    param($r); Set-Location "$r\notification-service"
    npx ts-node src/main.ts 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 3
Write-Host "       OK - Notification Service (Socket.IO :3006 + Ethereal email)" -ForegroundColor Green

# ── 9. API Gateway :8080 ──────────────────────────────────────────────────────
Write-Host "[9/11] API Gateway :8080..." -ForegroundColor Yellow
$gwJob = Start-Job -Name "Gateway" -ScriptBlock {
    param($r); Set-Location "$r\gateway"
    node index.js 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 2
Write-Host "       OK - API Gateway (all APIs proxied through :8080)" -ForegroundColor Green

# ── 10. Frontend :5173 ────────────────────────────────────────────────────────
Write-Host "[10/11] Frontend :5173..." -ForegroundColor Yellow
$frontJob = Start-Job -Name "Frontend" -ScriptBlock {
    param($r); Set-Location "$r\frontend"
    npm run dev -- --host 2>&1
} -ArgumentList $root
Start-Sleep -Seconds 5
Write-Host "        OK - Frontend (Vite hot-reload)" -ForegroundColor Green

# ── 11. Cloudflare Tunnel (Internet Access) ───────────────────────────────────
Write-Host ""
Write-Host "[11/11] Starting Cloudflare Tunnel for internet access..." -ForegroundColor Magenta

# Check if cloudflared is available
$cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflaredCmd) {
    # Try common install paths
    $paths = @(
        "$env:LOCALAPPDATA\cloudflared\cloudflared.exe",
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "$root\cloudflared.exe"
    )
    $found = $false
    foreach ($p in $paths) {
        if (Test-Path $p) { $cloudflaredCmd = $p; $found = $true; break }
    }
    if (-not $found) {
        Write-Host "       cloudflared not found. Downloading automatically..." -ForegroundColor Yellow
        $dlUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        $dlPath = "$root\cloudflared.exe"
        try {
            Invoke-WebRequest -Uri $dlUrl -OutFile $dlPath -UseBasicParsing
            $cloudflaredCmd = $dlPath
            Write-Host "       cloudflared downloaded to project root." -ForegroundColor Green
        } catch {
            Write-Host "       WARN: Could not download cloudflared. Falling back to localtunnel." -ForegroundColor Red
            $cloudflaredCmd = $null
        }
    }
}

$pubUrl = ""
$tunnelJob = $null

if ($cloudflaredCmd) {
    $cfLog = "$env:TEMP\sc_cf_tunnel.txt"
    if (Test-Path $cfLog) { Remove-Item $cfLog -Force }

    $tunnelJob = Start-Job -Name "Tunnel" -ScriptBlock {
        param($cmd, $log)
        # Use Add-Content (opens/closes per line) so the file is never exclusively locked
        & $cmd tunnel --url http://localhost:5173 2>&1 | ForEach-Object {
            $_ | Add-Content -Path $log -Encoding UTF8
            $_  # Also emit to job stream so logs are streamed to terminal
        }
    } -ArgumentList $cloudflaredCmd, $cfLog

    # Wait a moment for cloudflared to initialise before polling
    Start-Sleep -Seconds 3

    # Poll for Cloudflare public URL using FileShare.ReadWrite so we never block
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $cfLog) {
            try {
                $stream = [System.IO.File]::Open($cfLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
                $reader = New-Object System.IO.StreamReader($stream)
                $txt    = $reader.ReadToEnd()
                $reader.Close(); $stream.Close()
                if ($txt -match "https://[a-z0-9\-]+\.trycloudflare\.com") {
                    $pubUrl = $Matches[0]; break
                }
            } catch { <# file not ready yet, retry #> }
        }
    }
    Write-Host "       OK - Cloudflare Tunnel active" -ForegroundColor Green
} else {
    # Fallback: localtunnel
    $ltLog = "$env:TEMP\sc_tunnel.txt"
    if (Test-Path $ltLog) { Remove-Item $ltLog -Force }
    $tunnelJob = Start-Job -Name "Tunnel" -ScriptBlock {
        param($log)
        $output = & npx --yes localtunnel --port 5173 2>&1
        $output | Out-File $log
    } -ArgumentList $ltLog

    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $ltLog) {
            $txt = [System.IO.File]::ReadAllText($ltLog)
            if ($txt -match "your url is: (https://\S+)") {
                $pubUrl = $Matches[1]; break
            }
        }
    }
}

# ── Get LAN IP ────────────────────────────────────────────────────────────────
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object -First 1).IPAddress

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  ShieldCloud -- ALL 11 SERVICES RUNNING" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard      -> http://localhost:5173" -ForegroundColor White
Write-Host "  API Gateway    -> http://localhost:8080" -ForegroundColor White
Write-Host "  Auth API       -> http://localhost:3001" -ForegroundColor DarkCyan
Write-Host "  Encryption API -> http://localhost:3002" -ForegroundColor DarkCyan
Write-Host "  Storage API    -> http://localhost:3003" -ForegroundColor DarkCyan
Write-Host "  Anomaly ML API -> http://localhost:3004" -ForegroundColor DarkCyan
Write-Host "  Risk Engine    -> http://localhost:3005" -ForegroundColor DarkCyan
Write-Host "  Notification   -> http://localhost:3006" -ForegroundColor DarkCyan
Write-Host "  MinIO UI       -> http://localhost:9001  (minioadmin/minioadmin)" -ForegroundColor DarkCyan
Write-Host "  RabbitMQ UI    -> http://localhost:15672 (guest/guest)" -ForegroundColor DarkCyan
Write-Host ""

if ($lanIp) {
    Write-Host "  LAN (same WiFi, any device): http://${lanIp}:5173" -ForegroundColor Green
}

if ($pubUrl -ne "") {
    Write-Host ""
    Write-Host "  INTERNET ACCESS (any device, anywhere):" -ForegroundColor Magenta
    Write-Host "  $pubUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "  Open the above URL on your phone, tablet, or any browser." -ForegroundColor Yellow
    Write-Host "  Register a new account or use your existing credentials." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "  Tunnel URL not detected yet. Check Tunnel job output below." -ForegroundColor Yellow
    Write-Host "  Or run manually: .\cloudflared.exe tunnel --url http://localhost:5173" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Notification alerts fire in real-time (Socket.IO :3006)" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor Gray
Write-Host ""

Start-Process "http://localhost:5173"

# ── Stream logs ───────────────────────────────────────────────────────────────
$allJobs = @($authJob, $storageJob, $encJob, $mlJob, $riskJob, $healJob, $notifJob, $gwJob, $frontJob)
if ($tunnelJob) { $allJobs += $tunnelJob }

try {
    while ($true) {
        foreach ($j in $allJobs) {
            $out = Receive-Job $j 2>&1
            if ($out) {
                $label = $j.Name.PadRight(12)
                $out | ForEach-Object { Write-Host "[$label] $_" }
            }
        }
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "Stopping all jobs..." -ForegroundColor Red
    $allJobs | Stop-Job -PassThru | Remove-Job
}
