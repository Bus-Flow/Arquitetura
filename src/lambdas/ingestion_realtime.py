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

# Bounding Box oficial da Grande São Paulo para a API HERE (Oeste, Sul, Leste, Norte)
BBOX_SAO_PAULO = os.environ.get('HERE_BBOX', 'bbox:-46.826,-24.008,-46.365,-23.356')
HERE_FLOW_URL = "https://data.traffic.hereapi.com/v7/flow"
HERE_INCIDENTS_URL = "https://data.traffic.hereapi.com/v7/incidents"

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
        return {"status": "fallback_ativo", "aviso": "Chave OpenWeather não configurada"}
    
    url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric&lang=pt_br"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()

def converter_ms_para_kmh(valor):
    """Converte velocidade de m/s para km/h"""
    if valor is None:
        return None
    return round(valor * 3.6, 2)

def extrair_centroide_shape(shape_obj):
    """
    Calcula a latitude e longitude central (centroide) de um trecho viário
    a partir dos pontos do shape retornado pela HERE, descartando a polilinha densa.
    """
    if not shape_obj or not isinstance(shape_obj, dict):
        return None, None
    
    links = shape_obj.get("links", [])
    if not links:
        return None, None
    
    lats = []
    lngs = []
    for link in links:
        points = link.get("points", [])
        for pt in points:
            if "lat" in pt and "lng" in pt:
                lats.append(pt["lat"])
                lngs.append(pt["lng"])
                
    if not lats or not lngs:
        return None, None
        
    return round(sum(lats) / len(lats), 6), round(sum(lngs) / len(lngs), 6)

def extrair_texto(valor):
    """Normaliza campos de texto da HERE que podem vir como dict {'value': '...'}"""
    if isinstance(valor, dict):
        return valor.get("value")
    return valor

def sanitizar_fluxo_here(flow_raw):
    """
    Sanitiza os trechos de fluxo de trânsito:
    Extrai via, métricas operacionais e centroide (lat, lng),
    descartando a polilinha densa para manter o payload leve (~2 MB).
    """
    trechos = []
    for item in flow_raw.get("results", []):
        location = item.get("location", {})
        current_flow = item.get("currentFlow", {})
        
        lat, lng = extrair_centroide_shape(location.get("shape"))
        speed_ms = current_flow.get("speed")
        free_flow_ms = current_flow.get("freeFlow")
        
        trecho = {
            "via": location.get("description"),
            "comprimento_metros": location.get("length"),
            "lat": lat,
            "lng": lng,
            "jamFactor": current_flow.get("jamFactor"),
            "speed": converter_ms_para_kmh(speed_ms),
            "freeFlow": converter_ms_para_kmh(free_flow_ms),
            "confidence": current_flow.get("confidence"),
            "traversability": current_flow.get("traversability")
        }
        trechos.append(trecho)
        
    return trechos

def sanitizar_incidentes_here(incidents_raw):
    """
    Sanitiza os incidentes de trânsito:
    Extrai criticidade, bloqueio de via, resumo e centroide (lat, lng).
    """
    incidentes = []
    for item in incidents_raw.get("results", []):
        location = item.get("location", {})
        detalhes = item.get("incidentDetails", {})
        
        lat, lng = extrair_centroide_shape(location.get("shape"))
        
        incidente = {
            "id": detalhes.get("id"),
            "via": location.get("description"),
            "comprimento_metros": location.get("length"),
            "lat": lat,
            "lng": lng,
            "type": detalhes.get("type"),
            "criticality": detalhes.get("criticality"),
            "roadClosed": detalhes.get("roadClosed", False),
            "startTime": detalhes.get("startTime"),
            "endTime": detalhes.get("endTime"),
            "typeDescription": extrair_texto(detalhes.get("typeDescription")),
            "summary": extrair_texto(detalhes.get("summary")),
            "description": extrair_texto(detalhes.get("description"))
        }
        incidentes.append(incidente)
        
    return incidentes

def coletar_trafego_here(api_key, bbox):
    """
    Coleta dados viários e de incidentes da HERE Traffic API v7
    e retorna o payload estruturado e sanitizado para o RAW.
    """
    if not api_key:
        return {
            "status": "fallback_ativo",
            "mensagem": "Chave HERE_API_KEY não configurada",
            "trafego": {
                "quantidade_trechos": 1,
                "trechos": [{
                    "via": "Média Cidade São Paulo",
                    "lat": -23.55052,
                    "lng": -46.633308,
                    "jamFactor": 3.0,
                    "speed": 22.5,
                    "freeFlow": 45.0,
                    "confidence": 0.85
                }]
            },
            "incidentes": {
                "quantidade_incidentes": 0,
                "dados": []
            }
        }
        
    session = requests.Session()
    session.headers.update({
        "User-Agent": "BusFlow-Lambda-Ingestion/3.0",
        "Accept-Encoding": "gzip"
    })
    try:
        # 1. Flow
        params = {
            "in": bbox,
            "locationReferencing": "shape",
            "apiKey": api_key
        }
        resp_flow = session.get(HERE_FLOW_URL, params=params, timeout=30)
        resp_flow.raise_for_status()
        flow_raw = resp_flow.json()
        
        # 2. Incidents
        resp_inc = session.get(HERE_INCIDENTS_URL, params=params, timeout=30)
        resp_inc.raise_for_status()
        inc_raw = resp_inc.json()
        
        # Sanitização
        trechos = sanitizar_fluxo_here(flow_raw)
        incidentes = sanitizar_incidentes_here(inc_raw)
        
        return {
            "status": "sucesso",
            "source_updated_flow": flow_raw.get("sourceUpdated"),
            "source_updated_incidents": inc_raw.get("sourceUpdated"),
            "trafego": {
                "quantidade_trechos": len(trechos),
                "trechos": trechos
            },
            "incidentes": {
                "quantidade_incidentes": len(incidentes),
                "dados": incidentes
            }
        }
    except Exception as e:
        print(f"Erro na coleta HERE Traffic: {e}")
        return {
            "status": "erro_coleta",
            "erro": str(e),
            "trafego": {
                "quantidade_trechos": 1,
                "trechos": [{
                    "via": "Média Cidade São Paulo (Fallback Erro)",
                    "lat": -23.55052,
                    "lng": -46.633308,
                    "jamFactor": 3.0,
                    "speed": 22.5,
                    "freeFlow": 45.0,
                    "confidence": 0.85
                }]
            },
            "incidentes": {
                "quantidade_incidentes": 0,
                "dados": []
            }
        }
    finally:
        session.close()

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
        session.close()
        
        # 2. Coletar Clima
        dados_clima = coletar_clima(OPENWEATHER_KEY, CITY_NAME)
        
        # 3. Coletar Tráfego HERE (Sanitizado)
        dados_trafego = coletar_trafego_here(HERE_API_KEY, BBOX_SAO_PAULO)
        
        # 4. Consolidar Payload RAW
        payload_raw = {
            "metadata": {
                "projeto": "BusFlow",
                "versao": "3.0",
                "timestamp_extracao_utc": agora.isoformat(),
                "ano": agora.year,
                "mes": agora.month,
                "dia": agora.day,
                "bbox_here": BBOX_SAO_PAULO
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
                'linhas_coletadas': len(dados_sptrans.get('l', [])),
                'trechos_here': dados_trafego.get('trafego', {}).get('quantidade_trechos', 0),
                'incidentes_here': dados_trafego.get('incidentes', {}).get('quantidade_incidentes', 0)
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
