# BusFlow — Exemplo de Output da Machine Learning em Produção

## 1. Objetivo deste documento

Este documento exemplifica **como seria a saída da Machine Learning do BusFlow quando o modelo estivesse integrado ao fluxo operacional e realizando previsões em produção**.

O cenário considerado é o modelo de previsão com horizonte de **30 minutos**, utilizando os dados disponíveis no instante atual (`t`) para estimar o nível futuro de gargalo operacional em `t + 30 min`.

> **Importante:** os valores apresentados abaixo são exemplos ilustrativos de saída. Eles demonstram o formato esperado do sistema, e não representam novas medições reais do dataset.

---

## 2. O que a ML prevê

A principal saída do modelo é uma estimativa do indicador futuro de gargalo operacional:

```text
Dados atuais da linha em t
        ↓
Random Forest
        ↓
GO previsto para t + 30 min
        ↓
Regra de alerta preventivo
        ↓
Status + alerta + recomendação operacional
```

Durante a validação, o BusFlow utilizou:

- **Horizonte de previsão:** 30 minutos;
- **Modelo:** Random Forest Regressor;
- **Configuração candidata:** peso 5× para registros de risco;
- **Limiar de alerta preditivo estudado:** `0.53`;
- **Referência do estado real de risco no histórico:** `GO >= 0.60`.

O valor `0.53` não redefine o que é um risco real. Ele funciona como um **limiar preventivo do modelo**, usado para antecipar situações que podem evoluir para risco nos próximos 30 minutos.

---

## 3. Estrutura esperada do output

A saída de cada previsão pode conter os seguintes campos:

| Campo | Descrição |
|---|---|
| `timestamp_predicao` | Momento em que a previsão foi executada |
| `linha_codigo` | Código da linha analisada |
| `sentido` | Sentido operacional da linha |
| `horario_referencia` | Horário dos dados usados como entrada |
| `horario_previsto` | Horário para o qual a previsão foi gerada |
| `go_previsto_30min` | Valor de GO estimado pelo modelo para daqui a 30 minutos |
| `limiar_alerta` | Limiar preditivo usado pelo BusFlow |
| `status_previsto` | Situação prevista pela camada de decisão |
| `nivel_alerta` | Nível interpretável para operação |
| `confianca_operacional` | Indicador complementar de proximidade do score ao limiar |
| `acao_sugerida` | Recomendação gerada pela regra operacional após a previsão |
| `modelo` | Identificação da versão do modelo utilizada |

---

## 4. Exemplo simplificado de previsões

| Linha | Sentido | Agora | Previsão para | GO previsto | Status | Alerta | Ação sugerida |
|---|---|---:|---:|---:|---|---|---|
| 675A-10 | 1 | 18:00 | 18:30 | 0.472 | Estabilizado | Baixo | Manter operação |
| 477P-10 | 2 | 18:00 | 18:30 | 0.518 | Atenção | Moderado | Monitorar headway e frota |
| 875A-10 | 1 | 18:00 | 18:30 | 0.537 | Alerta preventivo | Alto | Avaliar reforço de frota |
| 509M-10 | 2 | 18:00 | 18:30 | 0.568 | Alerta preventivo | Alto | Preparar intervenção operacional |
| 675K-10 | 1 | 18:00 | 18:30 | 0.603 | Alerta crítico previsto | Crítico | Priorizar ação imediata |

---

## 5. Interpretação do score previsto

Uma possível camada de interpretação do BusFlow poderia utilizar faixas como:

| GO previsto | Interpretação do sistema |
|---:|---|
| `< 0.50` | Operação estável |
| `0.50 – 0.5299` | Atenção / monitoramento |
| `0.53 – 0.5999` | Alerta preventivo de risco |
| `>= 0.60` | Forte indicação de gargalo futuro |

Essas faixas representam uma **regra de negócio aplicada sobre a previsão da ML**. O modelo em si produz um número contínuo; a classificação textual ocorre posteriormente.

---

## 6. Exemplo de output em JSON

```json
{
  "timestamp_predicao": "2026-09-14T18:00:12",
  "linha_codigo": "875A-10",
  "sentido": 1,
  "horario_referencia": "18:00",
  "horario_previsto": "18:30",
  "go_previsto_30min": 0.5372,
  "limiar_alerta": 0.53,
  "status_previsto": "Alerta preventivo",
  "nivel_alerta": "Alto",
  "confianca_operacional": "Moderada",
  "acao_sugerida": "Avaliar reforco de frota e monitorar headway",
  "modelo": "random_forest_busflow_v1"
}
```

---

## 7. Exemplo com múltiplas linhas

```json
{
  "timestamp_processamento": "2026-09-14T18:00:12",
  "horizonte_previsao_min": 30,
  "modelo": "random_forest_busflow_v1",
  "limiar_alerta": 0.53,
  "predicoes": [
    {
      "linha_codigo": "675A-10",
      "sentido": 1,
      "horario_previsto": "18:30",
      "go_previsto_30min": 0.4721,
      "status_previsto": "Estabilizado",
      "acao_sugerida": "Manter operacao"
    },
    {
      "linha_codigo": "477P-10",
      "sentido": 2,
      "horario_previsto": "18:30",
      "go_previsto_30min": 0.5184,
      "status_previsto": "Atencao",
      "acao_sugerida": "Monitorar headway e frota"
    },
    {
      "linha_codigo": "875A-10",
      "sentido": 1,
      "horario_previsto": "18:30",
      "go_previsto_30min": 0.5372,
      "status_previsto": "Alerta preventivo",
      "acao_sugerida": "Avaliar reforco de frota"
    },
    {
      "linha_codigo": "509M-10",
      "sentido": 2,
      "horario_previsto": "18:30",
      "go_previsto_30min": 0.5681,
      "status_previsto": "Alerta preventivo",
      "acao_sugerida": "Preparar intervencao operacional"
    }
  ]
}
```

---

## 8. Exemplo de output para dashboard

No dashboard, a equipe do Centro de Controle Operacional poderia visualizar algo semelhante a:

```text
BUSFLOW — PREVISÃO PARA 18:30

Linhas analisadas: 2.096
Alertas preventivos: 42
Linhas em atenção: 137
Linhas estabilizadas: 1.917

------------------------------------------------------------
LINHA      SENTIDO    GO PREVISTO    NÍVEL       AÇÃO
------------------------------------------------------------
875A-10    1          0.537          ALTO        Avaliar reforço
509M-10    2          0.568          ALTO        Preparar intervenção
675K-10    1          0.603          CRÍTICO     Priorizar operação
------------------------------------------------------------
```

Os números agregados acima são apenas um exemplo visual de como a aplicação poderia apresentar os resultados.

---

## 9. Exemplo de alerta enviado ao operador

```text
ALERTA BUSFLOW

Linha: 875A-10
Sentido: 1
Horário atual: 18:00
Previsão: 18:30
GO previsto: 0.537
Nível: ALTO

Possível aumento de gargalo operacional nos próximos 30 minutos.

Ação sugerida:
Avaliar disponibilidade de frota adicional e acompanhar evolução do headway.
```

---

## 10. Separação entre ML e regra de negócio

É importante separar o que é gerado diretamente pelo modelo do que é interpretado pelo sistema.

### Saída direta da Machine Learning

```text
go_previsto_30min = 0.5372
```

### Pós-processamento do BusFlow

```text
0.5372 >= 0.53
        ↓
Alerta preventivo
        ↓
Nível: Alto
        ↓
Ação sugerida: avaliar reforço de frota
```

Portanto, a **Machine Learning não precisa decidir sozinha quantos ônibus devem ser enviados**. Ela antecipa o comportamento esperado do indicador operacional. A camada de regras do BusFlow transforma essa previsão em uma informação acionável para o operador.

---

## 11. Exemplo de payload para uma API do BusFlow

### Requisição

```json
{
  "linha_codigo": "875A-10",
  "sentido": 1,
  "dia_semana": 1,
  "hora_minuto": "18:00",
  "frota_ativa_real": 12,
  "headway_real_min": 14.2,
  "frota_planejada": 14,
  "headway_planejado_min": 10.0,
  "temperatura_c": 19.4,
  "sensacao_termica_c": 18.8,
  "chuva_1h_mm": 3.1,
  "visibilidade_m": 7000,
  "vento_velocidade_ms": 2.8,
  "jam_factor": 7.2,
  "velocidade_via_kmh": 18.7,
  "velocidade_freeflow_kmh": 39.5,
  "incidente_critico": 1
}
```

### Resposta

```json
{
  "linha_codigo": "875A-10",
  "sentido": 1,
  "horizonte_min": 30,
  "go_previsto": 0.5372,
  "limiar_alerta": 0.53,
  "alerta": true,
  "nivel": "Alto",
  "status": "Alerta preventivo",
  "acao_sugerida": "Avaliar reforco de frota",
  "modelo": "random_forest_busflow_v1"
}
```

---

## 12. Informações que podem ser armazenadas para auditoria

Cada previsão também pode ser registrada para permitir comparação posterior entre previsão e realidade:

```text
ID da previsão
Timestamp
Linha
Sentido
Features utilizadas
Versão do modelo
GO previsto para t+30
Limiar utilizado
Alerta emitido
GO real observado em t+30
Erro da previsão
Ação tomada pelo operador
```

Isso permite avaliar continuamente se o modelo permanece confiável depois de colocado em operação.

---

## 13. Exemplo de avaliação posterior

Após os 30 minutos previstos, o sistema poderia comparar:

```text
Previsão realizada às 18:00
GO previsto para 18:30 = 0.537

Valor observado às 18:30
GO real = 0.628

Resultado:
O modelo emitiu alerta preventivo antes de o indicador real ultrapassar 0.60.
```

Outro cenário possível:

```text
GO previsto = 0.552
GO real após 30 min = 0.481

Resultado:
Falso positivo.
O alerta foi emitido, mas o risco não se confirmou.
```

Esses registros são importantes para calcular posteriormente métricas como precisão, recall, MAE, RMSE e taxa de falsos alertas em produção.

---

## 14. Fluxo operacional completo esperado

```text
1. Coleta dos dados atuais
        ↓
2. Tratamento / ETL
        ↓
3. Preparação das features
        ↓
4. Random Forest recebe X(t)
        ↓
5. Predição do GO em t+30
        ↓
6. Aplicação do limiar preventivo
        ↓
7. Geração do nível de alerta
        ↓
8. Regra de negócio sugere uma ação
        ↓
9. Dashboard / aplicativo recebe o alerta
        ↓
10. Operador avalia a decisão
        ↓
11. Após 30 min, previsão é comparada ao valor real
```

---

## 15. Exemplo resumido para apresentação do TCC

> O BusFlow recebe dados atuais da operação, do tráfego e das condições climáticas e utiliza um modelo Random Forest para estimar o nível de gargalo operacional de cada linha para os próximos 30 minutos. O output principal da ML é um score contínuo de GO previsto. A partir desse score, uma camada de regras identifica situações de atenção e gera alertas preventivos ao CCO. Assim, o sistema não substitui a decisão do operador, mas fornece uma antecipação baseada em dados para apoiar o despacho da frota.

---

## 16. Resumo do output esperado

A ML do BusFlow deve responder principalmente às seguintes perguntas:

```text
QUAL linha?
→ linha_codigo

EM QUAL sentido?
→ sentido

PARA QUANDO?
→ t + 30 minutos

QUAL o nível previsto de gargalo?
→ go_previsto_30min

PRECISA de atenção preventiva?
→ comparação com limiar de alerta

O QUE o operador deve observar?
→ status + regra operacional + ação sugerida
```

O output final do BusFlow transforma uma previsão numérica da Machine Learning em uma informação operacional compreensível e utilizável pelo Centro de Controle Operacional.
