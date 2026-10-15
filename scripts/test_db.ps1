# =============================================================================
# test_db.ps1 — Valida o schema BusFlow no RDS via EC2 jump host
# Rodar de dentro da pasta: terraform/
#   cd terraform
#   ..\scripts\test_db.ps1
# =============================================================================

$ErrorActionPreference = "Continue"
$KEY_FILE    = "busflow_key.pem"
$REMOTE_SQL  = "/home/ec2-user/test_db.sql"

# --------------------------------------------------------------------------
# Outputs do Terraform
# --------------------------------------------------------------------------
$EC2_IP   = terraform output -raw ec2_web_app_ip
$RDS_HOST = terraform output -raw rds_endpoint

Write-Host "EC2 : $EC2_IP"
Write-Host "RDS : $RDS_HOST"

if (-not (Test-Path $KEY_FILE)) {
    Write-Error "busflow_key.pem nao encontrado. Rode setup_db.ps1 primeiro."
    exit 1
}

# --------------------------------------------------------------------------
# Senha — reutiliza $DB_PASS da sessão se já estiver definida
# --------------------------------------------------------------------------
if (-not $DB_PASS) {
    $secPass = Read-Host "Senha do RDS (rds_master_password)" -AsSecureString
    $global:DB_PASS = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                          [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secPass))
} else {
    Write-Host "Reutilizando senha da sessao."
}

# --------------------------------------------------------------------------
# Copia o SQL para a EC2 e executa
# --------------------------------------------------------------------------
Write-Host ""
Write-Host "Copiando test_db.sql para a EC2..." -ForegroundColor Cyan
scp -i $KEY_FILE -o StrictHostKeyChecking=no `
    "..\scripts\test_db.sql" `
    "ec2-user@${EC2_IP}:${REMOTE_SQL}" 2>$null

Write-Host "Executando validacao no RDS..." -ForegroundColor Cyan
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ec2-user@$EC2_IP `
    "PGPASSWORD='$DB_PASS' psql -h $RDS_HOST -U postgres -d busflowdb -f $REMOTE_SQL" 2>&1
