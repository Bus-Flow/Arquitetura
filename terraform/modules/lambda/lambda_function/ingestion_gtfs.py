import os
import io
import json
import zipfile
import hashlib
import re
import boto3
import requests
from datetime import datetime

s3 = boto3.client('s3')
sns = boto3.client('sns')

LOGIN_URL = "https://www.sptrans.com.br/desenvolvedores/login-desenvolvedores"
PERFIL_URL = "https://www.sptrans.com.br/desenvolvedores/perfil-desenvolvedor/"
DOWNLOAD_URL = "https://www.sptrans.com.br/umbraco/Surface/PerfilDesenvolvedor/BaixarGTFS?memberName=_sptrans"

SPTRANS_USERNAME = os.environ.get("SPTRANS_USERNAME", "")
SPTRANS_PASSWORD = os.environ.get("SPTRANS_PASSWORD", "")

def obter_token_ufprt(session):
    """Extrai o token de segurança ufprt da página de login da SPTrans usando regex flexível"""
    response = session.get(LOGIN_URL, timeout=30)
    response.raise_for_status()
    match = re.search(r'<input[^>]*name=["\']ufprt["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
    if not match:
        match = re.search(r'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']ufprt["\']', response.text, re.IGNORECASE)
    if not match:
        print(f"URL recebida: {response.url}, Status: {response.status_code}")
        print(f"Trecho HTML: {response.text[:500]}")
        raise RuntimeError("Campo ufprt não localizado na página de login da SPTrans.")
    return match.group(1)

def realizar_login_sptrans(session, token_ufprt):
    """Realiza a autenticação no portal de desenvolvedores"""
    dados_login = {
        "loginModel.Username": SPTRANS_USERNAME,
        "loginModel.Password": SPTRANS_PASSWORD,
        "ufprt": token_ufprt,
    }
    response = session.post(
        LOGIN_URL,
        data=dados_login,
        headers={"Referer": LOGIN_URL, "Origin": "https://www.sptrans.com.br"},
        timeout=30,
        allow_redirects=True
    )
    response.raise_for_status()
    if "perfil-desenvolvedor" not in response.url.lower() and "perfil desenvolvedor" not in response.text.lower():
        raise RuntimeError("Falha no login da SPTrans. Verifique credenciais.")

def baixar_gtfs(session):
    """Faz o download do arquivo ZIP GTFS"""
    response = session.get(DOWNLOAD_URL, headers={"Referer": PERFIL_URL}, timeout=180)
    response.raise_for_status()
    conteudo = response.content
    if not conteudo or not zipfile.is_zipfile(io.BytesIO(conteudo)):
        raise RuntimeError("Conteúdo baixado não é um arquivo ZIP GTFS válido.")
    return conteudo

def obter_hash_s3(bucket, key):
    """Obtém o hash SHA-256 do arquivo atualmente salvo no S3 para comparação"""
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        metadata = head.get('Metadata', {})
        return metadata.get('sha256')
    except:
        return None

def lambda_handler(event, context):
    """
    Lambda Ingestão GTFS Inteligente (BusFlow Arquitetura V3)
    Verifica se o GTFS da SPTrans sofreu atualização antes de gravar no S3 RAW.
    """
    bucket_raw = os.environ.get('BUCKET_RAW')
    topic_arn = os.environ.get('SNS_TOPIC_ARN')
    
    if not SPTRANS_USERNAME or not SPTRANS_PASSWORD:
        return {
            'statusCode': 400,
            'body': json.dumps('Credenciais SPTRANS_USERNAME e SPTRANS_PASSWORD não configuradas.')
        }

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
        })
        
        # 1. Login e Download
        token_ufprt = obter_token_ufprt(session)
        realizar_login_sptrans(session, token_ufprt)
        conteudo_zip = baixar_gtfs(session)
        
        # 2. Calcular Checksum SHA-256
        sha256_novo = hashlib.sha256(conteudo_zip).hexdigest()
        key_latest = "gtfs/latest/gtfs_atual.zip"
        
        # 3. Inteligência de Atualização (Verificação de Hash)
        if bucket_raw:
            sha256_atual = obter_hash_s3(bucket_raw, key_latest)
            if sha256_atual == sha256_novo:
                print("O arquivo GTFS não sofreu alterações desde a última coleta. Nenhuma alteração realizada.")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'status': 'sem_alteracao', 'mensagem': 'GTFS já atualizado no S3.'})
                }
        
        # 4. Salvar versão no Histórico e no Latest
        agora = datetime.utcnow()
        key_historico = f"gtfs/historico/ano={agora.year}/mes={agora.month:02d}/moovitbr_gtfs_{agora.strftime('%Y%m%d_%H%M%S')}.zip"
        
        if bucket_raw:
            # Upload histórico
            s3.put_object(
                Bucket=bucket_raw,
                Key=key_historico,
                Body=conteudo_zip,
                Metadata={'sha256': sha256_novo},
                ContentType='application/zip'
            )
            # Upload Latest
            s3.put_object(
                Bucket=bucket_raw,
                Key=key_latest,
                Body=conteudo_zip,
                Metadata={'sha256': sha256_novo},
                ContentType='application/zip'
            )
            print(f"Novo GTFS salvo em s3://{bucket_raw}/{key_latest}")
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'atualizado',
                'tamanho_bytes': len(conteudo_zip),
                'sha256': sha256_novo,
                'key_historico': key_historico
            })
        }

    except Exception as e:
        print(f"Erro na Ingestão GTFS: {str(e)}")
        if topic_arn:
            try:
                sns.publish(
                    TopicArn=topic_arn,
                    Subject='[BusFlow] Erro na Ingestão GTFS',
                    Message=f'Falha ao baixar GTFS: {str(e)}'
                )
            except:
                pass
        return {
            'statusCode': 500,
            'body': json.dumps({'erro': str(e)})
        }
