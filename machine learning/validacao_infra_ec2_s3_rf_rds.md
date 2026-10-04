# BusFlow — Registro de validação da infraestrutura para o Random Forest

**Projeto:** BusFlow — Automação Inteligente de Despacho de Frota de Ônibus via Machine Learning e Dados Climáticos  
**Objetivo deste registro:** documentar os testes básicos de acesso e comunicação entre Amazon S3 (Trusted), Amazon EC2, Random Forest e Amazon RDS PostgreSQL, antes do treinamento oficial na EC2.  
**Ambiente:** AWS Academy / Learner Lab, com infraestrutura provisionada por Terraform.  
**Data de referência dos testes:** 04/10/2026 (a inserção de teste no RDS foi registrada às `03:02:53 UTC`).  
**Situação:** testes de conectividade e execução local concluídos; integração com dados oficiais e persistência definitiva ainda pendentes.

> **Escopo:** os resultados abaixo são aqueles observados nos terminais durante o teste. O exemplo de ML usa dados sintéticos e não comprova a capacidade preditiva real para `t + 30 minutos`.

---

## 1. Arquitetura validada e objetivo do teste

```text
       Dados operacionais e climáticos (futuramente)
                         |
                         v
           S3 Trusted — bucket do BusFlow
                         |
              listagem confirmada
              leitura de CSV pendente
                         |
                         v
          EC2 — Python + scikit-learn
             |              |
      acesso por SSM   Random Forest
                          executado
                             |
                 GO sintético = 0,6466
                             |
                             v
           RDS PostgreSQL (conexão TLS)
             conexão, INSERT e SELECT
                      validados
                  (teste revertido)
```

### Componentes e identificação

| Componente | Identificação observada | Observação |
|---|---|---|
| EC2 | Hostname `ip-10-0-0-42.ec2.internal` | Acesso pelo Session Manager como `ssm-user`; IP privado indicado no hostname: `10.0.0.42`. |
| Sistema/Python | Amazon Linux 2023; Python `3.9.25` | Ambiente da EC2 utilizado nos testes. |
| AWS CLI | `aws-cli/2.36.47` | Funcionou após reparar a dependência `python3-dateutil`. |
| Bucket S3 Trusted | `trusted-busflow-2026-0d02809a` | Bucket acessível para listagem; vazio durante o teste. |
| RDS | `db-busflow.ci8ie0gc4upm.us-east-1.rds.amazonaws.com` | Endereço de rede privada resolvido durante o teste: `10.0.0.180`; porta `5432`. |
| Banco PostgreSQL | `busflowdb` | Usuário utilizado na sessão de teste: `postgres`. |
| Cliente/servidor PostgreSQL | `psql` `15.19` / servidor `14.22` | Sessão SQL estabelecida por TLS. |

**Observação de segurança:** nenhuma senha, chave privada ou credencial estática é registrada neste documento.

---

## 2. Teste 1 — Acesso à EC2 pelo Session Manager

O acesso ao terminal da EC2 foi realizado pelo AWS Systems Manager Session Manager; não foi necessário usar a chave `.pem` para esta sessão.

### Comandos

```bash
whoami
hostname
python3 --version
aws --version
```

### Resultados observados

```text
ssm-user
ip-10-0-0-42.ec2.internal
Python 3.9.25
```

**Status:** acesso à EC2 e execução do Python confirmados. O primeiro teste do `aws --version` falhou por uma dependência ausente, conforme detalhado a seguir.

---

## 3. Correção de ambiente — AWS CLI e `python3-dateutil`

### 3.1 Erro encontrado

O AWS CLI inicialmente falhou com:

```text
ModuleNotFoundError: No module named 'dateutil'
```

Uma tentativa de instalação simples não corrigiu o problema:

```bash
sudo dnf install -y python3-dateutil
```

O gerenciador informou que `python3-dateutil` já estava instalado, mas o comando `aws --version` continuava falhando.

### 3.2 Diagnóstico

```bash
head -n 1 /usr/bin/aws
python3 -c 'import sys; print("Python:", sys.executable); print("Caminhos:", sys.path); import dateutil; print("Dateutil:", dateutil.__file__)'
rpm -ql python3-dateutil | grep '/dateutil/__init__.py'
/usr/bin/python3 -s -c 'import dateutil; from dateutil.tz import tzlocal; print("Importação OK")'
/usr/bin/python3 -s -c 'import sys; print("\n".join(sys.path))'
rpm -V python3-dateutil
```

Constatações:

- O executável `/usr/bin/aws` utilizava `#!/usr/bin/python3 -s`.
- O Python sem `-s` encontrava uma cópia de `dateutil` em `/usr/local/lib/python3.9/site-packages/dateutil/`.
- O pacote RPM declarava arquivos em `/usr/lib/python3.9/site-packages/dateutil/`, mas eles não existiam fisicamente nesse local.
- `rpm -V python3-dateutil` listou vários arquivos como `missing`.

### 3.3 Correção aplicada

```bash
sudo dnf reinstall -y python3-dateutil
```

Retorno:

```text
Reinstalled:
  python3-dateutil-1:2.8.1-3.amzn2023.0.2.noarch
Complete!
```

### 3.4 Verificações depois do reparo

```bash
rpm -V python3-dateutil
/usr/bin/python3 -s -c 'from dateutil.tz import tzlocal; print("Dateutil OK")'
aws --version
```

Retornos:

```text
# rpm -V python3-dateutil: sem saída (nenhuma divergência reportada)
Dateutil OK
aws-cli/2.36.47 Python/3.9.25 Linux/6.18.51-120.163.amzn2023.x86_64 source/x86_64.amzn.2023
```

**Status:** dependência reparada e AWS CLI funcional.

---

## 4. Teste 2 — Comunicação EC2 → S3 Trusted

O bucket utilizado **nesta infraestrutura** é `trusted-busflow-2026-0d02809a`. Ele é diferente do bucket usado em etapas anteriores de validação da PoC.

### Comandos

```bash
aws s3 ls s3://trusted-busflow-2026-0d02809a/

aws s3api list-objects-v2 \
  --bucket trusted-busflow-2026-0d02809a \
  --max-keys 1 \
  --query 'KeyCount' \
  --output text
```

### Resultado observado

```text
# aws s3 ls: terminou sem erro e sem listar arquivos
0
```

**Interpretação:** a EC2 conseguiu consultar/listar o bucket; ele estava vazio no momento do teste.

**O que ainda não foi validado:** leitura de um objeto via `GetObject`, download de um CSV e permissões para leitura efetiva dos dados Trusted. A ausência de objetos impede esse teste por enquanto. Não é necessário conceder escrita ao consumidor de ML apenas para validar a comunicação.

---

## 5. Teste 3 — Disponibilidade do Python e execução do Random Forest

### 5.1 Verificação das bibliotecas

```bash
python3 -c "import numpy, pandas, sklearn; print('Bibliotecas OK')"
```

Resultado:

```text
Bibliotecas OK
```

### 5.2 Script de teste executado na EC2

O teste abaixo usa seis registros **sintéticos**; suas entradas representam, na ordem: frota, chuva, indicador de tráfego e horário de pico. O alvo representa valores ilustrativos de GO.

> Para copiar em um terminal Shell, a última linha `PY` precisa aparecer isolada, sem indentação. O script não depende de arquivos do S3.

```bash
python3 - <<'PY'
from sklearn.ensemble import RandomForestRegressor

# Dados sintéticos: frota, chuva, tráfego e horário de pico
X = [
    [10, 0, 1, 0],
    [10, 5, 3, 0],
    [8, 10, 6, 1],
    [6, 15, 8, 1],
    [12, 0, 2, 0],
    [7, 12, 7, 1]
]

# Valores fictícios de GO
y = [0.25, 0.35, 0.62, 0.78, 0.28, 0.70]

modelo = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)

modelo.fit(X, y)

entrada = [[8, 10, 6, 1]]
previsao = modelo.predict(entrada)[0]

print("Random Forest executado com sucesso!")
print(f"GO previsto no teste: {previsao:.4f}")
PY
```

### Resultado observado

```text
Random Forest executado com sucesso!
GO previsto no teste: 0.6466
```

**Interpretação:** `numpy`, `pandas` e `scikit-learn` estão importáveis; o treinamento e a inferência de um Random Forest funcionaram dentro da EC2.

**Limitação:** foi prevista uma linha também presente no treinamento, sem divisão temporal nem dados reais. O valor `0,6466` é um *smoke test* técnico e **não** é uma previsão validada para 30 minutos, nem uma métrica de qualidade do modelo final.

---

## 6. Teste 4 — Conectividade privada EC2 → RDS PostgreSQL

### 6.1 Tentativa inicial e correção

O primeiro teste de socket tentou usar `input()` dentro de um *heredoc*:

```bash
python3 - <<'PY'
import socket

host = input("Endpoint do RDS: ").strip()
porta = int(input("Porta do RDS: ").strip())

try:
    with socket.create_connection((host, porta), timeout=5):
        print("Comunicação EC2 → RDS: OK!")
except Exception as erro:
    print("Falha na conexão:", erro)
PY
```

Resultado:

```text
Endpoint do RDS: Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
EOFError: EOF when reading a line
```

**Causa:** o *heredoc* já consome a entrada padrão do processo Python; o `input()` não tem outra entrada interativa disponível. Esse erro **não** indicava falha de conexão com o RDS.

### 6.2 Teste de socket corrigido

```bash
python3 - <<'PY'
import socket

host = "db-busflow.ci8ie0gc4upm.us-east-1.rds.amazonaws.com"
porta = 5432

print("Testando comunicação EC2 → RDS...")

try:
    with socket.create_connection((host, porta), timeout=5):
        print("SUCESSO: comunicação EC2 → RDS funcionando!")
except Exception as erro:
    print("ERRO:", erro)
PY
```

Resultado:

```text
Testando comunicação EC2 → RDS...
SUCESSO: comunicação EC2 → RDS funcionando!
```

**Interpretação:** nome DNS, roteamento, controles de rede e abertura de conexão TCP até a porta `5432` do RDS funcionaram nesse teste. A autenticação no PostgreSQL foi testada separadamente, na etapa seguinte.

---

## 7. Teste 5 — Autenticação TLS e operações SQL no RDS

### 7.1 Versão do cliente

```bash
psql --version
```

Resultado:

```text
psql (PostgreSQL) 15.19
```

### 7.2 Tentativa com nome de banco incorreto

```bash
psql "host=db-busflow.ci8ie0gc4upm.us-east-1.rds.amazonaws.com port=5432 dbname=db-busflow user=postgres sslmode=require" -W
```

Resultado:

```text
psql: error: connection to server at
"db-busflow.ci8ie0gc4upm.us-east-1.rds.amazonaws.com" (10.0.0.180),
port 5432 failed: FATAL: database "db-busflow" does not exist
```

**Causa:** `db-busflow` não era o nome do banco de dados; o nome correto era `busflowdb`. O erro não demonstrava uma falha de rede.

### 7.3 Autenticação bem-sucedida

```bash
psql "host=db-busflow.ci8ie0gc4upm.us-east-1.rds.amazonaws.com port=5432 dbname=busflowdb user=postgres sslmode=require" -W
```

Resultado observado:

```text
psql (15.19, server 14.22)
SSL connection (protocol: TLSv1.2, cipher: ECDHE-RSA-AES256-GCM-SHA384, compression: off)
Type "help" for help.

busflowdb=>
```

**Interpretação:** conexão autenticada com o PostgreSQL e canal TLS estabelecido. A opção `sslmode=require` exige criptografia; a implantação definitiva deve avaliar também a verificação do certificado/identidade do servidor (`verify-full` com a CA adequada).

### 7.4 INSERT e SELECT em tabela temporária

O teste ocorreu dentro de uma transação, em tabela temporária, para não modificar permanentemente as tabelas operacionais.

```sql
BEGIN;

CREATE TEMP TABLE busflow_ml_smoke_test (
    linha_codigo TEXT,
    go_previsto NUMERIC(7,4),
    tipo_teste TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO busflow_ml_smoke_test (
    linha_codigo,
    go_previsto,
    tipo_teste
)
VALUES (
    'LINHA_TESTE',
    0.6466,
    'Previsao sintetica do Random Forest'
);

SELECT * FROM busflow_ml_smoke_test;

ROLLBACK;
```

Retorno observado:

```text
BEGIN
CREATE TABLE
INSERT 0 1
 linha_codigo | go_previsto |             tipo_teste              |           criado_em
--------------+-------------+-------------------------------------+-------------------------------
 LINHA_TESTE  |      0.6466 | Previsao sintetica do Random Forest | 2026-10-04 03:02:53.198086+00
(1 row)

ROLLBACK
```

**Interpretação:** foi possível criar tabela temporária, inserir um registro e consultá-lo. O `ROLLBACK` desfez a transação; o registro **não permaneceu gravado no banco**. Isso valida as operações SQL na sessão, mas a persistência definitiva deverá ser testada posteriormente com `COMMIT` em uma tabela própria da aplicação.

---

## 8. Resumo dos resultados

| Verificação | Situação | Evidência / observação |
|---|---|---|
| Acesso ao terminal da EC2 por Session Manager | **Aprovado** | Sessão como `ssm-user`; hostname `ip-10-0-0-42.ec2.internal`. |
| Python disponível na EC2 | **Aprovado** | Python `3.9.25`. |
| AWS CLI funcional | **Aprovado** | `aws-cli/2.36.47` após reinstalação do `python3-dateutil`. |
| Listagem do S3 Trusted | **Aprovado** | Consulta retornou `KeyCount = 0`, sem erro. |
| Leitura de dados reais do S3 (`GetObject`) | **Pendente** | Bucket estava vazio durante os testes. |
| Bibliotecas de ML disponíveis | **Aprovado** | Importação de `numpy`, `pandas` e `sklearn`. |
| Treinamento e inferência sintéticos do Random Forest | **Aprovado** | `GO previsto no teste: 0.6466`. |
| Comunicação TCP da EC2 com o RDS | **Aprovado** | Conexão estabelecida na porta `5432`. |
| Autenticação no PostgreSQL | **Aprovado** | Login no banco `busflowdb`, com TLSv1.2. |
| Execução de INSERT e SELECT | **Aprovado** | Registro sintético inserido e consultado em tabela temporária. |
| Persistência definitiva no RDS | **Pendente** | Teste transacional finalizou em `ROLLBACK`. |
| Treinamento oficial do modelo temporal | **Pendente** | Depende dos dados Trusted e do pipeline final. |
| Inferência operacional automática EC2 → RDS | **Pendente** | Integração definitiva ainda não implementada. |

### Conclusão técnica

Os resultados comprovam que os principais componentes estão **acessíveis e executáveis de forma individual**: a EC2 foi acessada, conseguiu consultar o bucket S3, executou um Random Forest de teste e estabeleceu comunicação autenticada com o RDS, incluindo operações SQL. Isso é suficiente para avançar à **integração e ao treinamento oficial da ML na EC2**, sem afirmar que o fluxo automatizado completo ou a qualidade preditiva já foram validados.

---

## 9. Próxima fase — Treinamento oficial e integração do BusFlow

Esta fase **não foi executada** neste registro. Sequência planejada:

1. **Popular o bucket Trusted e comprovar a leitura:** confirmar a estrutura de arquivos, listar os objetos, executar `GetObject` e carregar CSV/Parquet a partir da EC2. Verificar o esquema real e a qualidade dos registros.
2. **Reproduzir o dataset temporal:** preparar pares da mesma linha e sentido em `t` e `t+30 min`, evitando utilizar dados futuros como features; a variável-alvo será `go_gargalo_operacional` no instante futuro.
3. **Implantar o pipeline oficial do Random Forest:** utilizar as 17 features primitivas selecionadas na análise do Modelo B, o pré-processamento de categóricas e a configuração de `100` árvores, `max_depth=10` e `random_state=42`.
4. **Validar a configuração candidata:** testar o peso `5×` para registros de risco no treinamento e o limiar preditivo de alerta `0,53`, mantendo o risco real definido por `GO >= 0,60`. Esses hiperparâmetros foram selecionados na validação anterior e precisam de avaliação em um período temporal independente.
5. **Persistir os artefatos:** salvar o pipeline/modelo e metadados da versão, com procedimento de carregamento para inferência sem novo treinamento a cada chamada.
6. **Integrar a inferência ao PostgreSQL:** definir uma tabela definitiva de previsões com identificação da linha/sentido, horário de referência, horário previsto, GO previsto, status/alerta, versão do modelo e data da execução; autenticar a aplicação sem expor senhas em código.
7. **Validar persistência e operação:** fazer INSERT com `COMMIT` em uma tabela de testes autorizada, verificar o SELECT a partir de outra sessão e, depois, configurar a execução periódica, tratamento de erros, logs e eventual integração com alertas/dashboard.

**Critério de encerramento da próxima fase:** a EC2 deve conseguir ler dados oficiais do S3, executar o pipeline temporal treinado, produzir uma previsão para `t+30 min` e persistir o resultado no RDS de modo verificável, com logs e sem utilização de credenciais expostas.
