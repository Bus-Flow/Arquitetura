import json
import boto3
import os
import requests
from datetime import datetime

s3 = boto3.client('s3')
sns = boto3.client('sns')

SPTRANS_TOKEN = os.environ.get('SPTRANS_TOKEN', '')
OPENWEATHER_KEY = os.environ.get('OPENWEATHER_KEY', '')
HERE_API_KEY = os.environ.get('HERE_API_KEY', '')
CITY_NAME = os.environ.get('CITY_NAME', 'Sao Paulo,BR')

def autenticar_sptrans(session, token):
    """Autentica na API Olho Vivo da SPTrans"""
    url = f"http://api.olhovivo.sptrans.com.br/v2.1/Login/Autenticar?token={token}"
    response = session.post(url, headers={"Content-Length": "0"}, timeout=15)
    return response.status_code == 200 and response.text.lower() == "true"

def coletar_posicoes_sptrans(session):
    """Obtém as posições de todos os veículos ativos da SPTrans"""
    url = "http://api.olhovivo.sptrans.com.br/v2.1/Posicao"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

def coletar_clima(api_key, cidade):
    """Obtém dados meteorológicos atuais da OpenWeather"""
    if not api_key:
        return {"aviso": "Chave OpenWeather não configurada"}
    
    url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric&lang=pt_br"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()

def coletar_trafego_here(api_key):
    """
    Coleta dados viários da HERE Traffic API
    Fallback ativo enquanto a chave/endpoint estiver pendente
    """
    if not api_key:
        return {
            "status": "fallback_ativo",
            "mensagem": "Chave HERE_API_KEY pendente de configuração",
            "traffic_flow": {
                "jamFactor": 3.0,
                "speed": 22.5,
                "freeFlow": 45.0,
                "confidence": 0.85
            },
            "incidents": []
        }
    
    try:
        # Exemplo de chamada para HERE Traffic Flow v7 (São Paulo Bounding Box)
        bbox = "-23.70,-46.80,-23.40,-46.40"
        url = f"https://data.traffic.hereapi.com/v7/flow?in=bbox:{bbox}&apiKey={api_key}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "status": "erro_coleta",
            "erro": str(e),
            "traffic_flow": {"jamFactor": 3.0, "speed": 22.5, "freeFlow": 45.0}
        }

def lambda_handler(event, context):
    """
    Lambda de Ingestão em Tempo Real (BusFlow Arquitetura V3)
    Coleta dados das APIs SPTrans, OpenWeather e HERE e salva na camada RAW S3.
    """
    try:
        bucket_raw = os.environ.get('BUCKET_RAW')
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        agora = datetime.utcnow()
        timestamp_str = agora.strftime("%Y%m%d_%H%M%S")
        
        # 1. Coletar SPTrans
        session = requests.Session()
        session.headers.update({"User-Agent": "BusFlow-Lambda-Ingestion/3.0"})
        
        if not autenticar_sptrans(session, SPTRANS_TOKEN):
            raise RuntimeError("Falha de autenticação na SPTrans Olho Vivo.")
            
        dados_sptrans = coletar_posicoes_sptrans(session)
        
        # 2. Coletar Clima
        dados_clima = coletar_clima(OPENWEATHER_KEY, CITY_NAME)
        
        # 3. Coletar Tráfego
        dados_trafego = coletar_trafego_here(HERE_API_KEY)
        
        # 4. Consolidar Payload RAW
        payload_raw = {
            "metadata": {
                "projeto": "BusFlow",
                "versao": "3.0",
                "timestamp_extracao_utc": agora.isoformat(),
                "ano": agora.year,
                "mes": agora.month,
                "dia": agora.day
            },
            "sptrans": dados_sptrans,
            "clima": dados_clima,
            "trafego": dados_trafego
        }
        
        # 5. Salvar no S3 RAW (Particionado)
        partition_path = f"realtime/ano={agora.year}/mes={agora.month:02d}/dia={agora.day:02d}"
        file_key = f"{partition_path}/raw_busflow_{timestamp_str}.json"
        
        if bucket_raw:
            s3.put_object(
                Bucket=bucket_raw,
                Key=file_key,
                Body=json.dumps(payload_raw, ensure_ascii=False, indent=2),
                ContentType='application/json'
            )
            print(f"Salvo com sucesso em s3://{bucket_raw}/{file_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensagem': 'Ingestão em tempo real concluída com sucesso',
                's3_key': file_key,
                'linhas_coletadas': len(dados_sptrans.get('l', []))
            })
        }
        
    except Exception as e:
        print(f"Erro na Ingestão: {str(e)}")
        if topic_arn:
            try:
                sns.publish(
                    TopicArn=topic_arn,
                    Subject='[BusFlow] Erro na Lambda Ingestion',
                    Message=f'Falha na ingestão de dados em tempo real: {str(e)}'
                )
            except:
                pass
                
        return {
            'statusCode': 500,
            'body': json.dumps({'erro': str(e)})
        }
