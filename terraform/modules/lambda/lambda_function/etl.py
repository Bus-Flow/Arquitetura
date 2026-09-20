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

# Fator de conversao aproximado: 1 grau de latitude em SP (~ -23.5°) ≈ 111 km, 1 grau longitude ≈ 102 km
KM_PER_DEGREE_LAT = 111.0
KM_PER_DEGREE_LNG = 102.0
RAIO_BUSCA_KM = 1.0

def classificar_horario_pico(hora_min):
    """
    Classifica o periodo do dia para o indice de Horario de Pico (HP)
    PICO: 06:30 - 09:00 e 17:00 - 20:00 (Peso: 0.8)
    EXAUSTIVO: 09:00 - 17:00 (Peso: 0.5)
    TRANQUILO: 20:00 - 06:30 (Peso: 0.2)
    """
    try:
        hora, minuto = map(int, hora_min.split(':'))
        minutos_totais = hora * 60 + minuto
        
        # Pico Manha (06:30 as 09:00) e Pico Tarde (17:00 as 20:00)
        if (390 <= minutos_totais <= 540) or (1020 <= minutos_totais <= 1200):
            return 0.8, "Pico"
        # Entrepico Comercial (09:00 as 17:00)
        elif 540 < minutos_totais < 1020:
            return 0.5, "Exaustivo"
        else:
            return 0.2, "Tranquilo"
    except:
        return 0.5, "Exaustivo"

def calcular_indice_climatico(clima_raw):
    """
    Calcula o Gargalo Climatico (GC / IAC)
    Formula: IAC = (Chuva * 0.35) + (Visib. * 0.20) + (Vento * 0.20) + (Temp. * 0.15) + (Evento * 0.10)
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
    
    # 4. Desconforto Termico (feels_like): Ideal 22°C.
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
        
    # 5. Evento Climatico (codigo weather.id)
    weather_id = weather.get('id', 800)
    if weather_id < 300: # Tempestade
        sev_evento = 90.0
    elif weather_id < 600: # Chuva forte / moderada
        sev_evento = 60.0
    elif weather_id < 700: # Neve / Granizo
        sev_evento = 80.0
    elif weather_id < 800: # Nevoa / Fumaca
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
    Estrutura de Indexacao Espacial com cKDTree e IDW para cruzar
    onibus da SPTrans com trechos de fluxo e incidentes da HERE.
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
        # 1. Trechos de trafego
        dados_trafego = trafego_raw.get('trafego', {}).get('trechos', [])
        validos_trechos = []
        coords_tr = []
        
        for t in dados_trafego:
            lat = t.get('lat')
            lng = t.get('lng')
            if lat is not None and lng is not None:
                y = lat * KM_PER_DEGREE_LAT
                x = lng * KM_PER_DEGREE_LNG
                coords_tr.append([y, x])
                validos_trechos.append(t)
                
        self.trechos = validos_trechos
        if coords_tr:
            self.coords_trechos = np.array(coords_tr)
            if HAS_SCIPY:
                self.tree_trechos = cKDTree(self.coords_trechos)
                
        # 2. Incidentes de trafego
        dados_incidentes = trafego_raw.get('incidentes', {}).get('incidentes', [])
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

    def consultar_linha(self, veiculos):
        """
        Calcula as metricas viarias consolidadas para os onibus ativos da linha
        usando Inverse Distance Weighting (IDW) no raio de 1 km.
        """
        if not veiculos or not self.trechos or self.tree_trechos is None:
            return self._retorno_padrao()
            
        coords_onibus = []
        for v in veiculos:
            lat = v.get('py')
            lng = v.get('px')
            if lat is not None and lng is not None:
                coords_onibus.append([lat * KM_PER_DEGREE_LAT, lng * KM_PER_DEGREE_LNG])
                
        if not coords_onibus:
            return self._retorno_padrao()
            
        vizinhos_por_onibus = self.tree_trechos.query_ball_point(coords_onibus, r=RAIO_BUSCA_KM)
        
        indices_trechos_encontrados = set()
        pesos_totais = []
        jam_fatores = []
        speeds = []
        free_flows = []
        
        epsilon = 0.01 # 10 metros para evitar divisao por zero
        power = 2      # Decaimento quadratico IDW (1 / d^2)
        
        for i, idx_list in enumerate(vizinhos_por_onibus):
            if not idx_list:
                continue
            ponto_onibus = coords_onibus[i]
            for idx_tr in idx_list:
                indices_trechos_encontrados.add(idx_tr)
                ponto_tr = self.coords_trechos[idx_tr]
                dist_km = math.sqrt((ponto_onibus[0] - ponto_tr[0])**2 + (ponto_onibus[1] - ponto_tr[1])**2)
                
                peso = 1.0 / ((dist_km + epsilon) ** power)
                tr = self.trechos[idx_tr]
                
                pesos_totais.append(peso)
                jam_fatores.append(tr.get('jamFactor', 3.0) * peso)
                speeds.append((tr.get('speed') or 20.0) * peso)
                free_flows.append((tr.get('freeFlow') or 40.0) * peso)
                
        if not pesos_totais or sum(pesos_totais) == 0:
            return self._retorno_padrao()
            
        soma_pesos = sum(pesos_totais)
        jam_ponderado = round(sum(jam_fatores) / soma_pesos, 2)
        speed_ponderado = round(sum(speeds) / soma_pesos, 2)
        free_flow_ponderado = round(sum(free_flows) / soma_pesos, 2)
        
        incidente_critico = 0
        if self.tree_incidentes is not None and len(self.coords_incidentes) > 0:
            vizinhos_inc = self.tree_incidentes.query_ball_point(coords_onibus, r=RAIO_BUSCA_KM)
            for idx_list in vizinhos_inc:
                for idx_inc in idx_list:
                    inc = self.incidentes[idx_inc]
                    if inc.get('roadClosed') or inc.get('criticality') in ['critical', 'major']:
                        incidente_critico = 1
                        break
                if incidente_critico == 1:
                    break
                    
        flow_score = min(100.0, jam_ponderado * 10.0)
        inc_score = 100.0 if incidente_critico == 1 else 0.0
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
    Carrega o GTFS de referencia da pasta gtfs/latest/ do S3 RAW,
    incluindo paradas ordenadas por linha para localizacao dinamica dos carros.
    """
    referencias = {'headway_padrao_min': 10.0, 'paradas_por_linha': {}}
    try:
        obj = s3.get_object(Bucket=bucket_raw, Key="gtfs/latest/gtfs_atual.zip")
        with zipfile.ZipFile(io.BytesIO(obj['Body'].read())) as z:
            if 'frequencies.txt' in z.namelist():
                df_freq = pd.read_csv(z.open('frequencies.txt'))
                headway_medio = df_freq['headway_secs'].median() / 60.0 if not df_freq.empty else 10.0
                referencias['headway_padrao_min'] = headway_medio
                
            if 'stops.txt' in z.namelist() and 'stop_times.txt' in z.namelist() and 'trips.txt' in z.namelist():
                df_stops = pd.read_csv(z.open('stops.txt'), usecols=['stop_id', 'stop_lat', 'stop_lon'])
                df_st = pd.read_csv(z.open('stop_times.txt'), usecols=['trip_id', 'stop_id', 'stop_sequence'])
                df_trips = pd.read_csv(z.open('trips.txt'), usecols=['trip_id', 'route_id', 'direction_id'])
                
                df_merged = df_trips.merge(df_st, on='trip_id').merge(df_stops, on='stop_id')
                df_unique = df_merged.drop_duplicates(subset=['route_id', 'direction_id', 'stop_sequence']).sort_values('stop_sequence')
                
                for (r_id, d_id), group in df_unique.groupby(['route_id', 'direction_id']):
                    coords = group[['stop_lat', 'stop_lon']].values
                    seqs = group['stop_sequence'].values
                    referencias['paradas_por_linha'][(str(r_id), int(d_id))] = {
                        'coords': coords,
                        'seqs': seqs,
                        'total_paradas': len(seqs),
                        'tree': cKDTree(coords * np.array([KM_PER_DEGREE_LAT, KM_PER_DEGREE_LNG])) if HAS_SCIPY and len(coords) > 0 else None
                    }
    except Exception as e:
        print(f"Aviso ao carregar GTFS: {e}. Utilizando parametros operacionais de referencia padrao.")
        
    return referencias

def persistir_rds(df_linhas, df_veiculos):
    """
    Persiste diretamente no PostgreSQL RDS (busflowdb) sem intermediarios.
    Tabelas: fato_linha_operacao e fato_veiculo_posicao
    """
    db_host = os.environ.get('DB_HOST')
    if not db_host:
        print("Aviso: DB_HOST nao configurado no ambiente. Gravacao RDS ignorada.")
        return False

    db_name = os.environ.get('DB_NAME', 'busflowdb')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_port = int(os.environ.get('DB_PORT', '5432'))

    try:
        import psycopg2
        from psycopg2.extras import execute_values
        
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port,
            connect_timeout=5
        )
        cur = conn.cursor()

        # 1. Inserir Linhas Operacionais
        if not df_linhas.empty:
            sql_linhas = """
                INSERT INTO fato_linha_operacao (
                    timestamp_registro, linha_codigo, sentido, frota_ativa_real,
                    frota_necessaria_dfi, frota_planejada, headway_real_min,
                    headway_planejado_min, aderencia_cronograma_pct, status_linha,
                    iac_clima, gt_trafego, go_operacional
                ) VALUES %s
            """
            valores_linhas = [
                (
                    row['timestamp_processamento'], str(row['linha_codigo']), int(row['sentido']),
                    int(row['frota_ativa_real']), int(row['frota_necessaria_estimada']),
                    int(row['frota_planejada']), float(row['headway_real_min']),
                    float(row['headway_planejado_min']), float(row['ac_aderencia_cronograma'] * 100.0),
                    str(row['status_classificacao']), float(row['iac_gargalo_climatico']),
                    float(row['gt_gargalo_trafego']), float(row['go_gargalo_operacional'])
                )
                for _, row in df_linhas.iterrows()
            ]
            execute_values(cur, sql_linhas, valores_linhas, page_size=1000)

        # 2. Inserir Veiculos Individuais
        if not df_veiculos.empty:
            sql_veiculos = """
                INSERT INTO fato_veiculo_posicao (
                    timestamp_coleta, linha_codigo, sentido, prefixo_carro,
                    ponto_parada_seq, latitude, longitude, status_carro,
                    aderencia_individual, distancia_proximo_carro_km
                ) VALUES %s
            """
            valores_veiculos = [
                (
                    row['timestamp_coleta'], str(row['linha_codigo']), int(row['sentido']),
                    str(row['prefixo_carro']), int(row['ponto_parada_seq']),
                    float(row['latitude']) if pd.notnull(row['latitude']) else None,
                    float(row['longitude']) if pd.notnull(row['longitude']) else None,
                    str(row['status_carro']), float(row['aderencia_individual']),
                    float(row['distancia_proximo_carro_km']) if pd.notnull(row.get('distancia_proximo_carro_km')) else None
                )
                for _, row in df_veiculos.iterrows()
            ]
            execute_values(cur, sql_veiculos, valores_veiculos, page_size=2000)

        conn.commit()
        cur.close()
        conn.close()
        print(f"Sucesso: {len(df_linhas)} linhas e {len(df_veiculos)} veiculos persistidos diretamente no RDS.")
        return True
    except Exception as e:
        print(f"Aviso ao persistir no RDS (pipeline prossegue com S3): {e}")
        return False

def lambda_handler(event, context):
    """
    Lambda ETL BusFlow (Arquitetura V3)
    Processa o payload do RAW, cruza com inteligencia espacial HERE (cKDTree + IDW),
    calcula indices operacionais por linha e por veiculo, gravando no S3 TRUSTED e no RDS PostgreSQL.
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
        
        # 3. Construir Indexador Espacial HERE e Sub-indices Globais
        indexador_trafego = IndexadorEspacialTrafego(trafego_data)
        iac_score, clima_vars = calcular_indice_climatico(clima_data)
        hp_score, periodo_pico = classificar_horario_pico(hora_coleta)
        gtfs_ref = carregar_referencias_gtfs(bucket_raw)
        
        # 4. Processar Linhas e Veiculos com Inteligencia Espacial
        registros_trusted = []
        registros_veiculos = []
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
            
            # Headway real estimado baseado na distribuicao de veiculos
            headway_real = round(max(3.0, (60.0 / frota_ativa_real)) if frota_ativa_real > 0 else 30.0, 1)
            
            # Aderencia ao Cronograma (AC)
            ac_score = round(min(1.0, headway_planejado / headway_real), 3)
            
            # Demanda de Frota Ideal (DFI) e Deficit
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
            
            # Classificacao de Risco (Matriz Calibrada de 4 Niveis)
            if go_score <= 0.45:
                status_classificacao = "Estabilizado"
                acao_recomendada = "Operacao Normal"
            elif go_score <= 0.55:
                status_classificacao = "Risco de Gargalo"
                acao_recomendada = "Monitorar Linha em Alerta"
            elif go_score <= 0.65:
                status_classificacao = "Gargalo"
                acao_recomendada = f"Disponibilizacao de {max(1, deficit_operacional)} onibus saindo do terminal."
                alertas_risco.append((codigo_linha, status_classificacao, deficit_operacional))
            else:
                status_classificacao = "Gargalo"
                acao_recomendada = f"Disponibilizacao de {max(2, deficit_operacional)} onibus saindo do terminal."
                alertas_risco.append((codigo_linha, status_classificacao, deficit_operacional))
                
            # Montar Registro Tabular da Linha
            registro_linha = {
                'timestamp_processamento': agora.isoformat(),
                'linha_codigo': codigo_linha,
                'linha_id': linha_id,
                'sentido': sentido,
                'letreiro_origem': letreiro_origem,
                'letreiro_destino': letreiro_destino,
                'dia_semana': agora.weekday(),
                'hora_minuto': hora_coleta,
                'frota_ativa_real': frota_ativa_real,
                'headway_real_min': headway_real,
                'frota_planejada': frota_planejada,
                'headway_planejado_min': headway_planejado,
                'temperatura_c': clima_vars['temp_c'],
                'sensacao_termica_c': clima_vars['feels_like_c'],
                'chuva_1h_mm': clima_vars['rain_mm'],
                'visibilidade_m': clima_vars['visib_m'],
                'vento_velocidade_ms': clima_vars['wind_speed_ms'],
                'clima_evento_id': clima_vars['weather_id'],
                'jam_factor': metricas_trafego['jam_factor'],
                'velocidade_via_kmh': metricas_trafego['speed_kmh'],
                'velocidade_freeflow_kmh': metricas_trafego['free_flow_kmh'],
                'incidente_critico': metricas_trafego['incidente_critico'],
                'iac_gargalo_climatico': iac_score,
                'gt_gargalo_trafego': iiv_score,
                'hp_horario_pico': hp_score,
                'ac_aderencia_cronograma': ac_score,
                'dfi_demanda_frota_ideal': dfi_score,
                'frota_necessaria_estimada': frota_necessaria,
                'deficit_operacional': deficit_operacional,
                'go_gargalo_operacional': go_score,
                'status_classificacao': status_classificacao,
                'acao_recomendada': acao_recomendada
            }
            registros_trusted.append(registro_linha)
            
            # Processar Carros Individuais para Circulacao da Frota (Paradas 1 a N)
            gtfs_linha = gtfs_ref.get('paradas_por_linha', {}).get((str(codigo_linha), int(sentido)))
            coords_tree = gtfs_linha.get('tree') if gtfs_linha else None
            seqs_list = gtfs_linha.get('seqs') if gtfs_linha else None
            total_paradas = gtfs_linha.get('total_paradas', 18) if gtfs_linha else 18
            
            for idx, v in enumerate(veiculos):
                p_raw = str(v.get('p', f"{idx+1}"))
                prefixo_carro = f"Carro {p_raw[-2:] if len(p_raw) >= 2 else p_raw}"
                lat_v = v.get('py')
                lng_v = v.get('px')
                
                # Mapeamento Dinamico do Ponto de Parada (1 a N)
                if coords_tree is not None and lat_v is not None and lng_v is not None:
                    y_v = lat_v * KM_PER_DEGREE_LAT
                    x_v = lng_v * KM_PER_DEGREE_LNG
                    _, idx_stop = coords_tree.query([y_v, x_v])
                    parada_seq = int(seqs_list[idx_stop])
                else:
                    parada_seq = int((idx * (total_paradas / max(1, len(veiculos)))) % total_paradas) + 1
                    
                if status_classificacao == "Gargalo" and idx in [0, 1]:
                    status_carro = "Gargalo"
                    aderencia_carro = 0.35
                elif status_classificacao in ["Risco de Gargalo", "Gargalo"] and idx in [2, 3]:
                    status_carro = "Risco de Gargalo"
                    aderencia_carro = 0.65
                else:
                    status_carro = "Estabilizado"
                    aderencia_carro = 0.90
                    
                registros_veiculos.append({
                    'timestamp_coleta': agora.isoformat(),
                    'linha_codigo': codigo_linha,
                    'sentido': sentido,
                    'prefixo_carro': prefixo_carro,
                    'ponto_parada_seq': parada_seq,
                    'latitude': lat_v,
                    'longitude': lng_v,
                    'status_carro': status_carro,
                    'aderencia_individual': aderencia_carro,
                    'distancia_proximo_carro_km': round(max(0.2, (idx + 1) * 0.8), 2)
                })
            
        # 5. Salvar Datasets no Bucket TRUSTED (S3 Lakehouse)
        df_trusted = pd.DataFrame(registros_trusted)
        df_veiculos = pd.DataFrame(registros_veiculos)
        
        timestamp_str = agora.strftime("%Y%m%d_%H%M%S")
        trusted_key_linhas = f"fato_operacao_frota/ano={agora.year}/mes={agora.month:02d}/dia={agora.day:02d}/fato_operacao_{timestamp_str}.csv"
        trusted_key_veiculos = f"fato_veiculo_posicao/ano={agora.year}/mes={agora.month:02d}/dia={agora.day:02d}/fato_veiculo_{timestamp_str}.csv"
        
        csv_linhas_buf = io.StringIO()
        df_trusted.to_csv(csv_linhas_buf, index=False)
        s3.put_object(
            Bucket=bucket_trusted,
            Key=trusted_key_linhas,
            Body=csv_linhas_buf.getvalue(),
            ContentType='text/csv'
        )
        
        if not df_veiculos.empty:
            csv_veiculos_buf = io.StringIO()
            df_veiculos.to_csv(csv_veiculos_buf, index=False)
            s3.put_object(
                Bucket=bucket_trusted,
                Key=trusted_key_veiculos,
                Body=csv_veiculos_buf.getvalue(),
                ContentType='text/csv'
            )
            
        print(f"Sucesso: {len(df_trusted)} linhas e {len(df_veiculos)} veiculos gravados no S3 TRUSTED.")
        
        # 6. Persistir diretamente no RDS PostgreSQL (Fonte da Verdade)
        persistir_rds(df_trusted, df_veiculos)
        
        # 7. Notificar via SNS se houver linhas criticas
        if alertas_risco and topic_arn:
            linhas_msg = "\n".join([f"- Linha {c}: Status {s}, Deficit {d} veiculos" for c, s, d in alertas_risco[:10]])
            msg = f"Alertas Operacionais BusFlow ({agora.strftime('%d/%m/%Y %H:%M')}):\n\nLinhas Criticas Detectadas:\n{linhas_msg}\n\nDataset TRUSTED: s3://{bucket_trusted}/{trusted_key_linhas}"
            try:
                sns.publish(TopicArn=topic_arn, Subject='[BusFlow] Alerta de Gargalo Operacional', Message=msg)
            except:
                pass
                
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensagem': 'ETL executado com sucesso',
                'linhas_processadas': len(df_trusted),
                'veiculos_processados': len(df_veiculos),
                'trusted_key': trusted_key_linhas,
                'alertas_gerados': len(alertas_risco)
            })
        }
        
    except Exception as e:
        print(f"Erro critico no ETL: {str(e)}")
        if topic_arn:
            try:
                sns.publish(
                    TopicArn=os.environ.get('SNS_TOPIC_ARN'),
                    Subject='[BusFlow] Erro Critico no ETL',
                    Message=f'Falha durante a execucao do ETL: {str(e)}'
                )
            except:
                pass
        return {
            'statusCode': 500,
            'body': json.dumps({'erro': str(e)})
        }
