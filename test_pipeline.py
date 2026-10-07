#!/usr/bin/env python3
"""
BusFlow — Teste End-to-End do Pipeline ETL
Verifica S3 RAW, Lambda ETL, S3 TRUSTED e confirmação via CloudWatch Logs.
"""

import boto3
import json
import sys
import time
from datetime import datetime

# ── Configuração ─────────────────────────────────────────────────────────────
REGION          = 'us-east-1'
FUNCTION_NAME   = 'a1f6a839-etl'
BUCKET_RAW      = 'raw-busflow-2026-0d02809a'
BUCKET_TRUSTED  = 'trusted-busflow-2026-0d02809a'
TEST_KEY        = 'realtime/ano=2026/mes=08/dia=22/raw_busflow_exemplo.json'
LOG_GROUP       = '/aws/lambda/a1f6a839-etl'
SLA_SEGUNDOS    = 60.0   # SLA de processamento definido no TCC

# ── Cores ANSI ────────────────────────────────────────────────────────────────
G  = '\033[92m'   # verde
R  = '\033[91m'   # vermelho
Y  = '\033[93m'   # amarelo
B  = '\033[94m'   # azul
W  = '\033[97m'   # branco
BD = '\033[1m'    # negrito
RS = '\033[0m'    # reset

passed = 0
failed = 0

def ok(label, detail=''):
    global passed
    passed += 1
    sfx = f'  {W}({detail}){RS}' if detail else ''
    print(f'  {G}✓{RS}  {label}{sfx}')

def fail(label, detail=''):
    global failed
    failed += 1
    sfx = f'  {R}({detail}){RS}' if detail else ''
    print(f'  {R}✗{RS}  {label}{sfx}')

def warn(label, detail=''):
    sfx = f'  {Y}({detail}){RS}' if detail else ''
    print(f'  {Y}!{RS}  {label}{sfx}')

def section(title):
    print(f'\n{BD}{B}── {title} {"─" * (44 - len(title))}{RS}')

# ── Clientes AWS ──────────────────────────────────────────────────────────────
s3   = boto3.client('s3',     region_name=REGION)
lam  = boto3.client('lambda', region_name=REGION)
logs = boto3.client('logs',   region_name=REGION)

print(f'\n{BD}BusFlow Pipeline Test{RS}  —  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# ══════════════════════════════════════════════════════════════════════════════
# 1. S3 RAW
# ══════════════════════════════════════════════════════════════════════════════
section('1  S3 RAW Bucket')

try:
    s3.head_bucket(Bucket=BUCKET_RAW)
    ok('Bucket RAW acessível', BUCKET_RAW)
except Exception as e:
    fail('Bucket RAW acessível', str(e))

try:
    s3.head_object(Bucket=BUCKET_RAW, Key=TEST_KEY)
    ok('Arquivo de teste presente', TEST_KEY.split('/')[-1])
except Exception as e:
    fail('Arquivo de teste presente', str(e))

resp  = s3.list_objects_v2(Bucket=BUCKET_RAW, Prefix='realtime/', MaxKeys=200)
count = resp.get('KeyCount', 0)
if count > 0:
    ok('Arquivos realtime no RAW', f'{count} arquivos')
else:
    fail('Arquivos realtime no RAW', '0 arquivos encontrados')

gtfs = s3.list_objects_v2(Bucket=BUCKET_RAW, Prefix='gtfs/', MaxKeys=10)
if gtfs.get('KeyCount', 0) > 0:
    ok('Dados GTFS presentes', f'{gtfs["KeyCount"]} arquivos')
else:
    warn('Dados GTFS ausentes', 'opcional para enriquecimento de paradas')

# ══════════════════════════════════════════════════════════════════════════════
# 2. Invocação da Lambda ETL
# ══════════════════════════════════════════════════════════════════════════════
section('2  Lambda ETL — Invocação')

t0   = time.time()
resp = lam.invoke(
    FunctionName=FUNCTION_NAME,
    InvocationType='RequestResponse',
    Payload=b'{}'
)
elapsed_total = time.time() - t0

http_status = resp['StatusCode']
if http_status == 200:
    ok('Lambda invocada (HTTP)', f'status {http_status}')
else:
    fail('Lambda invocada (HTTP)', f'status {http_status}')

raw_payload = resp['Payload'].read()
outer = json.loads(raw_payload)
body  = json.loads(outer['body']) if isinstance(outer.get('body'), str) else outer.get('body', {})

if outer.get('statusCode') == 200:
    ok('ETL retornou sucesso', outer.get('statusCode'))
else:
    fail('ETL retornou sucesso', outer.get('body', raw_payload.decode())[:100])

linhas   = body.get('linhas_processadas',  0)
veiculos = body.get('veiculos_processados', 0)
duracao  = body.get('duracao_segundos',    0)
alertas  = body.get('alertas_gerados',     0)
trusted  = body.get('trusted_key',         '')

if linhas > 0:
    ok('Linhas processadas', f'{linhas} linhas de operação')
else:
    fail('Linhas processadas', '0 linhas')

if veiculos > 0:
    ok('Veículos processados', f'{veiculos} posições GPS')
else:
    fail('Veículos processados', '0 veículos')

if duracao <= SLA_SEGUNDOS:
    ok(f'SLA de processamento (≤{SLA_SEGUNDOS:.0f}s)', f'{duracao:.1f}s')
else:
    warn(f'SLA de processamento (≤{SLA_SEGUNDOS:.0f}s)', f'{duracao:.1f}s — acima do alvo mas funcional')

print(f'      Alertas gerados: {alertas}')

# ══════════════════════════════════════════════════════════════════════════════
# 3. S3 TRUSTED
# ══════════════════════════════════════════════════════════════════════════════
section('3  S3 TRUSTED Bucket')

try:
    s3.head_bucket(Bucket=BUCKET_TRUSTED)
    ok('Bucket TRUSTED acessível', BUCKET_TRUSTED)
except Exception as e:
    fail('Bucket TRUSTED acessível', str(e))

if trusted:
    try:
        meta  = s3.head_object(Bucket=BUCKET_TRUSTED, Key=trusted)
        tamanho_kb = meta['ContentLength'] // 1024
        ok('Arquivo CSV criado no TRUSTED', f'{trusted.split("/")[-1]}  ({tamanho_kb} KB)')
    except Exception as e:
        fail('Arquivo CSV criado no TRUSTED', str(e))
else:
    fail('Chave do TRUSTED recebida', 'campo trusted_key ausente na resposta')

resp_t  = s3.list_objects_v2(Bucket=BUCKET_TRUSTED, Prefix='fato_operacao_frota/', MaxKeys=200)
total_t = resp_t.get('KeyCount', 0)
if total_t > 0:
    ok('Histórico de execuções no TRUSTED', f'{total_t} arquivos acumulados')
else:
    fail('Histórico de execuções no TRUSTED', '0 arquivos')

# ══════════════════════════════════════════════════════════════════════════════
# 4. CloudWatch Logs — última execução
# ══════════════════════════════════════════════════════════════════════════════
section('4  CloudWatch Logs — Verificação')

try:
    streams = logs.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    stream = streams['logStreams'][0]['logStreamName']
    events = logs.get_log_events(logGroupName=LOG_GROUP, logStreamName=stream)
    msgs   = [e['message'] for e in events['events']]
    ok('Log stream acessível', stream[-50:])

    rds_line = next((m for m in msgs if 'persistidos no RDS' in m), '')
    if rds_line:
        ok('Confirmação de inserção no RDS', rds_line.strip()[:80])
    else:
        fail('Confirmação de inserção no RDS', 'linha "persistidos no RDS" não encontrada')

    if not any('Erro critico' in m for m in msgs):
        ok('Nenhum erro crítico registrado')
    else:
        erro = next(m for m in msgs if 'Erro critico' in m)
        fail('Nenhum erro crítico registrado', erro.strip()[:80])

    report = next((m for m in msgs if 'Duration:' in m), '')
    if report:
        try:
            dur_ms  = float(report.split('Duration: ')[1].split(' ms')[0])
            mem_mb  = report.split('Max Memory Used: ')[1].split(' MB')[0] if 'Max Memory Used' in report else '?'
            ok('Métricas de execução', f'{dur_ms/1000:.1f}s  |  mem {mem_mb} MB')
        except Exception:
            pass

except Exception as e:
    fail('CloudWatch Logs', str(e))

# ══════════════════════════════════════════════════════════════════════════════
# 5. Resumo
# ══════════════════════════════════════════════════════════════════════════════
total = passed + failed
pct   = int(passed / total * 100) if total else 0
cor   = G if failed == 0 else (Y if pct >= 75 else R)

print(f'\n{BD}{"═"*52}{RS}')
print(f'{BD}  {cor}{passed}/{total}{RS}{BD} testes passaram  ({pct}%){RS}')
if failed == 0:
    print(f'{BD}  {G}Pipeline BusFlow operacional end-to-end ✓{RS}')
else:
    print(f'{BD}  {R}{failed} teste(s) falharam — verifique os itens acima{RS}')
print(f'{BD}{"═"*52}{RS}')

print(f"""
{BD}Para verificar o RDS:{RS}
  Conecte-se à EC2 via SSM Session Manager e execute:

  psql -h db-busflow.ci8ie0gc4upm.us-east-1.rds.amazonaws.com \\
       -U postgres -d busflowdb -c \\
  "SELECT
    (SELECT COUNT(*) FROM fato_linha_operacao)     AS linhas_op,
    (SELECT COUNT(*) FROM fato_veiculo_posicao)    AS veiculos,
    (SELECT COUNT(*) FROM fato_auditoria_pipeline) AS auditoria,
    (SELECT cumpre_sla FROM fato_auditoria_pipeline
     ORDER BY timestamp_inicio DESC LIMIT 1)       AS ultimo_sla;"
""")

sys.exit(0 if failed == 0 else 1)
