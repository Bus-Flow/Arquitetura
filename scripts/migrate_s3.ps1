# =============================================================================
# migrate_s3.ps1 — Migra dados S3 da conta antiga para a conta nova
#                  usando a EC2 da nova conta como ponte (velocidade AWS interna)
#
# Rodar de dentro da pasta: terraform/
#   cd terraform
#   ..\scripts\migrate_s3.ps1
#
# Pre-requisito: terraform apply ja executado na nova conta
# =============================================================================

$ErrorActionPreference = "Continue"
$KEY_FILE = "busflow_key.pem"

if (-not (Test-Path $KEY_FILE)) {
    Write-Error "busflow_key.pem nao encontrado. Rode setup_db.ps1 primeiro."
    exit 1
}

# --------------------------------------------------------------------------
# Outputs da nova conta (terraform)
# --------------------------------------------------------------------------
Write-Host "[1/5] Lendo configuracao da nova conta..." -ForegroundColor Cyan
$EC2_IP      = terraform output -raw ec2_web_app_ip
$RAW_NEW     = terraform output -raw s3_raw_bucket
$TRUSTED_NEW = terraform output -raw s3_trusted_bucket

Write-Host "      EC2       : $EC2_IP"
Write-Host "      Raw novo  : $RAW_NEW"
Write-Host "      Trusted novo: $TRUSTED_NEW"

# --------------------------------------------------------------------------
# Buckets da conta ANTIGA
# --------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/5] Informe os buckets da conta ANTIGA:" -ForegroundColor Cyan
$RAW_OLD     = Read-Host "      Nome do bucket RAW antigo (ex: raw-busflow-2026-0d02809a)"
$TRUSTED_OLD = Read-Host "      Nome do bucket TRUSTED antigo (ex: trusted-busflow-2026-0d02809a)"

# --------------------------------------------------------------------------
# Credenciais da conta ANTIGA (do Learner Lab → AWS Details → Show)
# --------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/5] Credenciais da conta ANTIGA (cole do Learner Lab):" -ForegroundColor Cyan
$OLD_KEY_ID  = Read-Host "      aws_access_key_id"
$OLD_SECRET  = Read-Host "      aws_secret_access_key"
$OLD_TOKEN   = Read-Host "      aws_session_token"

# --------------------------------------------------------------------------
# Monta o script de migração que vai rodar na EC2
# --------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/5] Enviando script de migracao para a EC2..." -ForegroundColor Cyan

$migrationScript = @"
#!/bin/bash
set -e

export AWS_ACCESS_KEY_ID="$OLD_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$OLD_SECRET"
export AWS_SESSION_TOKEN="$OLD_TOKEN"
export AWS_DEFAULT_REGION="us-east-1"

echo "=== Copiando RAW: $RAW_OLD -> $RAW_NEW ==="
aws s3 sync s3://$RAW_OLD /tmp/migration_raw --no-progress
echo "   Download concluido. Iniciando upload..."
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
aws s3 sync /tmp/migration_raw s3://$RAW_NEW --no-progress
echo "   Upload RAW concluido."
rm -rf /tmp/migration_raw

export AWS_ACCESS_KEY_ID="$OLD_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$OLD_SECRET"
export AWS_SESSION_TOKEN="$OLD_TOKEN"

echo ""
echo "=== Copiando TRUSTED: $TRUSTED_OLD -> $TRUSTED_NEW ==="
aws s3 sync s3://$TRUSTED_OLD /tmp/migration_trusted --no-progress
echo "   Download concluido. Iniciando upload..."
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
aws s3 sync /tmp/migration_trusted s3://$TRUSTED_NEW --no-progress
echo "   Upload TRUSTED concluido."
rm -rf /tmp/migration_trusted

echo ""
echo "=== Validando contagens ==="
echo "RAW novo:"
aws s3 ls s3://$RAW_NEW --recursive --summarize --human-readable | tail -2
echo "TRUSTED novo:"
aws s3 ls s3://$TRUSTED_NEW --recursive --summarize --human-readable | tail -2

echo ""
echo "MIGRACAO CONCLUIDA!"
"@

# Salva o script localmente e envia para EC2
$migrationScript | Set-Content -Encoding ascii -Path "migration_temp.sh"
scp -i $KEY_FILE -o StrictHostKeyChecking=no migration_temp.sh "ec2-user@${EC2_IP}:/home/ec2-user/migrate.sh" 2>$null
Remove-Item migration_temp.sh

# --------------------------------------------------------------------------
# Executa na EC2
# --------------------------------------------------------------------------
Write-Host "[5/5] Executando migracao na EC2 (pode demorar dependendo do volume)..." -ForegroundColor Cyan
Write-Host "      Acompanhe o progresso abaixo:" -ForegroundColor Yellow
Write-Host ""
ssh -i $KEY_FILE -o StrictHostKeyChecking=no ec2-user@$EC2_IP "chmod +x /home/ec2-user/migrate.sh && /home/ec2-user/migrate.sh" 2>&1

Write-Host ""
Write-Host "Para validar manualmente, use:" -ForegroundColor Yellow
Write-Host "  aws s3 ls s3://$RAW_NEW --recursive --summarize --human-readable"
Write-Host "  aws s3 ls s3://$TRUSTED_NEW --recursive --summarize --human-readable"
