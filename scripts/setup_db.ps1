# =============================================================================
# setup_db.ps1 — Cria o schema BusFlow no RDS via EC2 jump host
# Rodar de dentro da pasta: terraform/
#   cd terraform
#   ..\scripts\setup_db.ps1
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$SCHEMA_PATH = "..\src\database\schema_busflow_rds.sql"
$KEY_FILE    = "busflow_key.pem"

# --------------------------------------------------------------------------
# 1. Lê outputs do Terraform
# --------------------------------------------------------------------------
Write-Host "[1/5] Lendo outputs do Terraform..." -ForegroundColor Cyan
$EC2_IP   = terraform output -raw ec2_web_app_ip
$RDS_HOST = terraform output -raw rds_endpoint

Write-Host "      EC2 IP  : $EC2_IP"
Write-Host "      RDS Host: $RDS_HOST"

# --------------------------------------------------------------------------
# 2. Extrai a chave SSH do state e salva como PEM
# --------------------------------------------------------------------------
Write-Host "[2/5] Salvando chave SSH..." -ForegroundColor Cyan
terraform output -raw ec2_private_key | Set-Content -Encoding ascii -Path $KEY_FILE

# Permissão restrita (SSH recusa chave world-readable no OpenSSH Windows)
icacls $KEY_FILE /inheritance:r /grant:r "${env:USERNAME}:R" | Out-Null
Write-Host "      Chave salva em: $KEY_FILE"

# --------------------------------------------------------------------------
# 3. Aguarda EC2 aceitar SSH (pode demorar ~60s no primeiro boot)
# --------------------------------------------------------------------------
Write-Host "[3/5] Aguardando EC2 ficar acessível..." -ForegroundColor Cyan
$tries = 0
$connected = $false
do {
    $tries++
    Start-Sleep -Seconds 10
    try {
        $result = (ssh -i $KEY_FILE -o StrictHostKeyChecking=no -o ConnectTimeout=5 `
                       ec2-user@$EC2_IP "echo ok" 2>$null)
        if ($result -match "ok") { $connected = $true }
    } catch { }
} while (-not $connected -and $tries -lt 18)

if (-not $connected) {
    Write-Error "EC2 nao respondeu em 3 minutos. Verifique o Security Group e tente de novo."
}
Write-Host "      EC2 acessível!"

# --------------------------------------------------------------------------
# 4. Copia schema SQL para EC2 e executa via psql
# --------------------------------------------------------------------------
Write-Host "[4/5] Copiando schema para EC2..." -ForegroundColor Cyan
scp -i $KEY_FILE -o StrictHostKeyChecking=no $SCHEMA_PATH `
    "ec2-user@${EC2_IP}:/home/ec2-user/schema_busflow.sql"

Write-Host "[4/5] Criando tabelas no RDS..." -ForegroundColor Cyan

# Pede a senha sem exibir no terminal
$secPass  = Read-Host "      Digite rds_master_password" -AsSecureString
$DB_PASS  = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secPass))

$psqlCmd  = "PGPASSWORD='$DB_PASS' psql -h $RDS_HOST -U postgres -d busflowdb -f /home/ec2-user/schema_busflow.sql 2>&1"
$output   = ssh -i $KEY_FILE -o StrictHostKeyChecking=no ec2-user@$EC2_IP $psqlCmd
Write-Host $output

# --------------------------------------------------------------------------
# 5. Valida schema
# --------------------------------------------------------------------------
Write-Host "[5/5] Validando schema..." -ForegroundColor Cyan
$testSql = @"
\echo '--- Tabelas criadas ---'
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
\echo '--- Views criadas ---'
SELECT viewname FROM pg_views WHERE schemaname = 'public' ORDER BY viewname;
\echo '--- Indices criados ---'
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;
"@

$psqlTest = "PGPASSWORD='$DB_PASS' psql -h $RDS_HOST -U postgres -d busflowdb -c `"$testSql`" 2>&1"
$validation = ssh -i $KEY_FILE -o StrictHostKeyChecking=no ec2-user@$EC2_IP $psqlTest
Write-Host $validation

Write-Host ""
Write-Host "Schema criado com sucesso!" -ForegroundColor Green
Write-Host "Para rodar os testes completos:" -ForegroundColor Yellow
Write-Host "  ..\scripts\test_db.ps1"
