import json
import boto3
import pandas as pd
import numpy as np
import os
import io
import math
import zipfile
import urllib.parse
from datetime import datetime

try:
    from scipy.spatial import cKDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

s3 = boto3.client('s3')
sns = boto3.client('sns')

# Fator de conversão aproximado: 1 grau de latitude em SP (~ -23.5°) ≈ 111 km, 1 grau longitude ≈ 102 km
KM_PER_DEGREE_LAT = 111.0
KM_PER_DEGREE_LNG = 102.0
RAIO_BUSCA_KM = 1.0

def classificar_horario_pico(hora_min):
    """
    Classifica o período do dia para o índice de Horário de Pico (HP)
    PICO: 06:30 - 09:00 e 17:00 - 20:00 (Peso: 0.8)
    EXAUSTIVO: 09:00 - 17:00 (Peso: 0.5)
    TRANQUILO: 20:00 - 06:30 (Peso: 0.2)
    """
    try:
        hora, minuto = map(int, hora_min.split(':'))
        minutos_totais = hora * 60 + minuto
        
        # Pico Manhã (06:30 às 09:00) e Pico Tarde (17:00 às 20:00)
        if (390 <= minutos_totais <= 540) or (1020 <= minutos_totais <= 1200):
            return 0.8, "Pico"
        # Entrepico Comercial (09:00 às 17:00)
        elif 540 < minutos_totais < 1020:
            return 0.5, "Exaustivo"
        else:
            return 0.2, "Tranquilo"
    except:
        return 0.5, "Exaustivo"

def calcular_indice_climatico(clima_raw):
    """
    Calcula o Gargalo Climático (GC / IAC)
    Fórmula: IAC = (Chuva * 0.35) + (Visib. * 0.20) + (Vento * 0.20) + (Temp. * 0.15) + (Evento * 0.10)
    Retorna valor de 0 a 100
    """
    main = clima_raw.get('main', {})
    wind = clima_raw.get('wind', {})
    rain = clima_raw.get('rain', {})
    weather = clima_raw.get('weather', [{}])[0]
    
    # 1. Chuva (0 a 100): 0 mm = 0, >= 20 mm/h = 100
    rain_mm = rain.get('1h', 0.0) if isinstance(rain, dict) else 0.0
    sev_chuva = min(100.0, (rain_mm / 15.0) * 100.0)
    
    # 2. Visibilidade (0 a 100): 10.000m = 0, <= 1.000m = 100
    visib_m = clima_raw.get('visibility', 10000)
    sev_visib = max(0.0, min(100.0, (1.0 - (visib_m / 10000.0)) * 100.0))
    
    # 3. Vento (0 a 100): 0 m/s = 0, >= 20 m/s = 100
    wind_speed = wind.get('speed', 0.0)
    sev_vento = min(100.0, (wind_speed / 20.0) * 100.0)
    
    # 4. Desconforto Térmico (feels_like): Ideal 22°C.
    feels_like = main.get('feels_like', 22.0)
    temp_c = main.get('temp', 22.0)
    if feels_like >= 35.0 or feels_like <= 5.0:
        sev_temp = 90.0
    elif feels_like >= 30.0 or feels_like <= 10.0:
        sev_temp = 60.0
    elif feels_like >= 26.0 or feels_like <= 15.0:
        sev_temp = 30.0
    else:
        sev_temp = 10.0
        
    # 5. Evento Climático (código weather.id)
    weather_id = weather.get('id', 800)
    if weather_id < 300: # Tempestade
        sev_evento = 90.0
    elif weather_id < 600: # Chuva forte / moderada
        sev_evento = 60.0
    elif weather_id < 700: # Neve / Granizo
        sev_evento = 80.0
    elif weather_id < 800: # Névoa / Fumaça
        sev_evento = 50.0
    else:
        sev_evento = 10.0
        
    iac = (sev_chuva * 0.35) + (sev_visib * 0.20) + (sev_vento * 0.20) + (sev_temp * 0.15) + (sev_evento * 0.10)
    return round(iac, 2), {
        'temp_c': temp_c,
        'feels_like_c': feels_like,
        'rain_mm': rain_mm,
        'visib_m': visib_m,
        'wind_speed_ms': wind_speed,
        'weather_id': weather_id
    }

class IndexadorEspacialTrafego:
    """
    Estrutura de Indexação Espacial com cKDTree e IDW para cruzar
    ônibus da SPTrans com trechos de fluxo e incidentes da HERE.
    """
    def __init__(self, trafego_raw):
        self.trechos = []
        self.incidentes = []
        self.tree_trechos = None
        self.tree_incidentes = None
        self.coords_trechos = []
        self.coords_incidentes = []
        
        self._construir_indices(trafego_raw)

    def _construir_indices(self, trafego_raw):
        # 1. Trechos de tráfego
        dados_trafego = trafego_raw.get('trafego', {}).get('trechos', [])
        validos_trechos = []
        coords_tr = []
        
        for t in dados_trafego:
            lat = t.get('lat')
            lng = t.get('lng')
            if lat is not None and lng is not None:
                # Converte em coordenadas normalizadas em km para busca euclidiana rápida
                y = lat * KM_PER_DEGREE_LAT
                x = lng * KM_PER_DEGREE_LNG
                coords_tr.append([y, x])
                validos_trechos.append(t)
                
        self.trechos = validos_trechos
        if coords_tr:
            self.coords_trechos = np.array(coords_tr)
            if HAS_SCIPY:
                self.tree_trechos = cKDTree(self.coords_trechos)
                
        # 2. Incidentes de tráfego
        dados_incidentes = trafego_raw.get('incidentes', {}).get('dados', [])
        validos_inc = []
        coords_inc = []
        
        for inc in dados_incidentes:
            lat = inc.get('lat')
            lng = inc.get('lng')
            if lat is not None and lng is not None:
                y = lat * KM_PER_DEGREE_LAT
                x = lng * KM_PER_DEGREE_LNG
                coords_inc.append([y, x])
                validos_inc.append(inc)
                
        self.incidentes = validos_inc
        if coords_inc:
            self.coords_incidentes = np.array(coords_inc)
            if HAS_SCIPY:
                self.tree_incidentes = cKDTree(self.coords_incidentes)

    def consultar_linha(self, veiculos_linha):
        """
        Calcula o jam_factor, velocidades e incidentes críticos ponderados por IDW
        no raio de 1 km para os veículos ativos de uma linha.
        """
        # Se não há trechos ou veículos válidos, retorna valores de referência seguros
        if not self.trechos or not veiculos_linha:
            return self._retorno_padrao()
            
        coords_veiculos = []
        for v in veiculos_linha:
            py = v.get('py')
            px = v.get('px')
            if py is not None and px is not None:
                coords_veiculos.append([py * KM_PER_DEGREE_LAT, px * KM_PER_DEGREE_LNG])
                
        if not coords_veiculos:
            return self._retorno_padrao()
            
        coords_v = np.array(coords_veiculos)
        indices_vizinhos = []
        distancias_vizinhos = []
        
        if HAS_SCIPY and self.tree_trechos is not None:
            # Busca todos os vizinhos no raio de 1.0 km para todos os veículos da linha
            vizinhos_por_veiculo = self.tree_trechos.query_ball_point(coords_v, r=RAIO_BUSCA_KM)
            for idx_v, vizinhos in enumerate(vizinhos_por_veiculo):
                if vizinhos:
                    pt_v = coords_v[idx_v]
                    pts_t = self.coords_trechos[vizinhos]
                    dists = np.linalg.norm(pts_t - pt_v, axis=1)
                    indices_vizinhos.extend(vizinhos)
                    distancias_vizinhos.extend(dists)
        else:
            # Fallback puro NumPy caso SciPy não esteja instalado
            for pt_v in coords_v:
                dists = np.linalg.norm(self.coords_trechos - pt_v, axis=1)
                mask = dists <= RAIO_BUSCA_KM
                viz_idx = np.where(mask)[0]
                if len(viz_idx) > 0:
                    indices_vizinhos.extend(viz_idx)
                    distancias_vizinhos.extend(dists[viz_idx])
                    
        if not indices_vizinhos:
            return self._retorno_padrao()
            
        # IDW (Inverse Distance Weighting) com fator de suavização epsilon = 0.01 km (10m)
        dists_arr = np.array(distancias_vizinhos)
        weights = 1.0 / np.power(dists_arr + 0.01, 2)
        total_weight = np.sum(weights)
        
        jam_factors = np.array([self.trechos[i].get('jamFactor') or 3.0 for i in indices_vizinhos])
        speeds = np.array([self.trechos[i].get('speed') or 22.5 for i in indices_vizinhos])
        free_flows = np.array([self.trechos[i].get('freeFlow') or 45.0 for i in indices_vizinhos])
        
        jam_ponderado = round(float(np.sum(jam_factors * weights) / total_weight), 2)
        speed_ponderado = round(float(np.sum(speeds * weights) / total_weight), 2)
        free_flow_ponderado = round(float(np.sum(free_flows * weights) / total_weight), 2)
        
        # 2. Avaliação de Incidentes Críticos no Raio de 1 km
        incidente_critico = 0
        bloqueio_total = False
        
        if len(self.incidentes) > 0:
            if HAS_SCIPY and self.tree_incidentes is not None:
                inc_vizinhos = self.tree_incidentes.query_ball_point(coords_v, r=RAIO_BUSCA_KM)
                for viz in inc_vizinhos:
                    for i_idx in viz:
                        inc = self.incidentes[i_idx]
                        if inc.get('roadClosed') or str(inc.get('criticality')).lower() in ['critical', 'major', 'high']:
                            incidente_critico = 1
                            if inc.get('roadClosed'):
                                bloqueio_total = True
            else:
                for pt_v in coords_v:
                    dists_inc = np.linalg.norm(self.coords_incidentes - pt_v, axis=1)
                    mask_inc = dists_inc <= RAIO_BUSCA_KM
                    for i_idx in np.where(mask_inc)[0]:
                        inc = self.incidentes[i_idx]
                        if inc.get('roadClosed') or str(inc.get('criticality')).lower() in ['critical', 'major', 'high']:
                            incidente_critico = 1
                            if inc.get('roadClosed'):
                                bloqueio_total = True
                                
        # Cálculo do Sub-Índice GT (Gargalo de Tráfego: 0 a 100)
        flow_score = min(100.0, jam_ponderado * 10.0)
        inc_score = 100.0 if (incidente_critico == 1 and bloqueio_total) else (60.0 if incidente_critico == 1 else 0.0)
        tend_score = 50.0
        
        gt_score = round((0.70 * flow_score) + (0.25 * inc_score) + (0.05 * tend_score), 2)
        
        return {
            'jam_factor': jam_ponderado,
            'speed_kmh': speed_ponderado,
            'free_flow_kmh': free_flow_ponderado,
            'incidente_critico': incidente_critico,
            'gt_score': gt_score
        }
        
    def _retorno_padrao(self):
        return {
            'jam_factor': 3.0,
            'speed_kmh': 22.5,
            'free_flow_kmh': 45.0,
            'incidente_critico': 0,
            'gt_score': 23.5
        }

def carregar_referencias_gtfs(bucket_raw):
    """
    Carrega o GTFS de referência da pasta gtfs/latest/ do S3 RAW
    """
    referencias = {}
    try:
        obj = s3.get_object(Bucket=bucket_raw, Key="gtfs/latest/gtfs_atual.zip")
        with zipfile.ZipFile(io.BytesIO(obj['Body'].read())) as z:
            if 'frequencies.txt' in z.namelist():
                df_freq = pd.read_csv(z.open('frequencies.txt'))
                headway_medio = df_freq['headway_secs'].median() / 60.0 if not df_freq.empty else 10.0
                referencias['headway_padrao_min'] = headway_medio
    except Exception as e:
        print(f"Aviso ao carregar GTFS: {e}. Utilizando parâmetros operacionais de referência padrão.")
        referencias['headway_padrao_min'] = 10.0
        
    return referencias

def lambda_handler(event, context):
    """
    Lambda ETL BusFlow (Arquitetura V3)
    Processa o payload do RAW, cruza com inteligência espacial HERE (cKDTree + IDW),
    calcula os índices operacionais e grava a tabela formatada no TRUSTED Bucket.
    """
    try:
        bucket_raw = os.environ['BUCKET_RAW']
        bucket_trusted = os.environ['BUCKET_TRUSTED']
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        
        # 1. Identificar arquivo no S3 RAW
        if 'Records' in event:
            key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
            bucket = event['Records'][0]['s3']['bucket']['name']
        else:
            # Fallback para teste manual
            key = 'realtime/ano=2026/mes=08/dia=22/raw_busflow_exemplo.json'
            bucket = bucket_raw
            
        print(f"Iniciando processamento ETL para: s3://{bucket}/{key}")
        
        # 2. Ler Payload RAW
        obj = s3.get_object(Bucket=bucket, Key=key)
        raw_data = json.loads(obj['Body'].read().decode('utf-8'))
        
        sptrans_data = raw_data.get('sptrans', {})
        clima_data = raw_data.get('clima', {})
        trafego_data = raw_data.get('trafego', {})
        
        hora_coleta = sptrans_data.get('hr', datetime.utcnow().strftime("%H:%M"))
        linhas = sptrans_data.get('l', [])
        
        # 3. Construir Indexador Espacial HERE e Sub-índices Globais
        indexador_trafego = IndexadorEspacialTrafego(trafego_data)
        iac_score, clima_vars = calcular_indice_climatico(clima_data)
        hp_score, periodo_pico = classificar_horario_pico(hora_coleta)
        gtfs_ref = carregar_referencias_gtfs(bucket_raw)
        
        # 4. Processar Cada Linha Operacional com Inteligência Espacial
        registros_trusted = []
        agora = datetime.utcnow()
        alertas_risco = []
        
        for l in linhas:
            codigo_linha = l.get('c', 'DESCONHECIDO')
            linha_id = l.get('cl', 0)
            sentido = l.get('sl', 1)
            letreiro_origem = l.get('lt0', '')
            letreiro_destino = l.get('lt1', '')
            frota_ativa_real = l.get('qv', 0)
            veiculos = l.get('vs', [])
            
            # Cruzamento Espacial HERE por Linha (IDW no raio de 1 km)
            metricas_trafego = indexador_trafego.consultar_linha(veiculos)
            iiv_score = metricas_trafego['gt_score']
            
            # Dimensionamento GTFS e Estimativas
            frota_planejada = max(1, int(frota_ativa_real * 1.1)) if frota_ativa_real > 0 else 5
            headway_planejado = gtfs_ref.get('headway_padrao_min', 8.0)
            
            # Headway real estimado baseado na distribuição de veículos
            headway_real = round(max(3.0, (60.0 / frota_ativa_real)) if frota_ativa_real > 0 else 30.0, 1)
            
            # Aderência ao Cronograma (AC)
            ac_score = round(min(1.0, headway_planejado / headway_real), 3)
            
            # Demanda de Frota Ideal (DFI) e Déficit
            fator_demanda = 1.0 + ((iac_score + iiv_score) / 200.0)
            frota_necessaria = math.ceil(frota_planejada * fator_demanda)
            deficit_operacional = max(0, frota_necessaria - frota_ativa_real)
            
            # Risco Congestionamento Frota (DFI % de 0 a 100)
            dfi_score = round(min(100.0, (frota_necessaria / max(1, frota_ativa_real)) * 50.0), 2)
            
            # Gargalo Operacional Geral (GO: 0.0 a 1.0)
            go_score = round(
                (0.15 * hp_score) +
                (0.25 * (iac_score / 100.0)) +
                (0.25 * (iiv_score / 100.0)) +
                (0.25 * (dfi_score / 100.0)) +
                (0.10 * (1.0 - ac_score)),
                4
            )
            
            # Classificação de Risco
            if go_score <= 0.60:
                status_classificacao = "Estabilizado"
                acao_recomendada = "Operação Normal"
            elif go_score <= 0.80:
                status_classificacao = "Risco"
                acao_recomendada = "Monitorar Linha em Alerta"
            elif go_score <= 0.95:
                status_classificacao = "Alto Risco"
                acao_recomendada = f"Disponibilizar {max(1, deficit_operacional)} ônibus"
                alertas_risco.append((codigo_linha, status_classificacao, deficit_operacional))
            else:
                status_classificacao = "Congestionamento"
                acao_recomendada = f"Disponibilizar {max(2, deficit_operacional)} ônibus"
                alertas_risco.append((codigo_linha, status_classificacao, deficit_operacional))
                
            # Montar Registro Tabular Completo
            registro = {
                'timestamp_processamento': agora.isoformat(),
                'linha_codigo': codigo_linha,
                'linha_id': linha_id,
                'sentido': sentido,
                'letreiro_origem': letreiro_origem,
                'letreiro_destino': letreiro_destino,
                'dia_semana': agora.weekday(),
                'hora_minuto': hora_coleta,
                # Variáveis Reais
                'frota_ativa_real': frota_ativa_real,
                'headway_real_min': headway_real,
                # Variáveis Planejadas (GTFS)
                'frota_planejada': frota_planejada,
                'headway_planejado_min': headway_planejado,
                # Variáveis Clima
                'temperatura_c': clima_vars['temp_c'],
                'sensacao_termica_c': clima_vars['feels_like_c'],
                'chuva_1h_mm': clima_vars['rain_mm'],
                'visibilidade_m': clima_vars['visib_m'],
                'vento_velocidade_ms': clima_vars['wind_speed_ms'],
                'clima_evento_id': clima_vars['weather_id'],
                # Variáveis Tráfego HERE (Ponderadas por Linha)
                'jam_factor': metricas_trafego['jam_factor'],
                'velocidade_via_kmh': metricas_trafego['speed_kmh'],
                'velocidade_freeflow_kmh': metricas_trafego['free_flow_kmh'],
                'incidente_critico': metricas_trafego['incidente_critico'],
                # Sub-índices Calculados
                'iac_gargalo_climatico': iac_score,
                'gt_gargalo_trafego': iiv_score,
                'hp_horario_pico': hp_score,
                'ac_aderencia_cronograma': ac_score,
                'dfi_demanda_frota_ideal': dfi_score,
                # Targets e Saídas
                'frota_necessaria_estimada': frota_necessaria,
                'deficit_operacional': deficit_operacional,
                'go_gargalo_operacional': go_score,
                'status_classificacao': status_classificacao,
                'acao_recomendada': acao_recomendada
            }
            registros_trusted.append(registro)
            
        # 5. Salvar Dataset no Bucket TRUSTED
        df_trusted = pd.DataFrame(registros_trusted)
        timestamp_str = agora.strftime("%Y%m%d_%H%M%S")
        trusted_key = f"fato_operacao_frota/ano={agora.year}/mes={agora.month:02d}/dia={agora.day:02d}/fato_operacao_{timestamp_str}.csv"
        
        csv_buffer = io.StringIO()
        df_trusted.to_csv(csv_buffer, index=False)
        
        s3.put_object(
            Bucket=bucket_trusted,
            Key=trusted_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        print(f"Sucesso! Dataset com {len(df_trusted)} linhas gravado em s3://{bucket_trusted}/{trusted_key}")
        
        # 6. Notificar via SNS se houver linhas em alto risco / congestionamento
        if alertas_risco and topic_arn:
            linhas_msg = "\n".join([f"- Linha {c}: Status {s}, Déficit {d} veículos" for c, s, d in alertas_risco[:10]])
            msg = f"Alertas Operacionais BusFlow ({agora.strftime('%d/%m/%Y %H:%M')}):\n\nLinhas Críticas Detectadas:\n{linhas_msg}\n\nDataset TRUSTED: s3://{bucket_trusted}/{trusted_key}"
            try:
                sns.publish(TopicArn=topic_arn, Subject='[BusFlow] Alerta de Gargalo Operacional', Message=msg)
            except:
                pass
                
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensagem': 'ETL executado com sucesso',
                'linhas_processadas': len(df_trusted),
                'trusted_key': trusted_key,
                'alertas_gerados': len(alertas_risco)
            })
        }
        
    except Exception as e:
        print(f"Erro crítico no ETL: {str(e)}")
        if topic_arn:
            try:
                sns.publish(
                    TopicArn=os.environ.get('SNS_TOPIC_ARN'),
                    Subject='[BusFlow] Erro Crítico no ETL',
                    Message=f'Falha durante a execução do ETL: {str(e)}'
                )
            except:
                pass
        return {
            'statusCode': 500,
            'body': json.dumps({'erro': str(e)})
        }
