# 📊 Especificação Técnica: Recalibração de Métricas e Lógica de Alertas — Bus-Flow

**Repositório:** Bus-Flow (Arquitetura de Dados & ETL Serverless)  
**Componentes Impactados:** AWS Lambda (`etl.py`), Terraform (`modules/lambda`), S3 Trusted, AWS SNS Alerts, Tabelas de Análise / Athena.  
**Data:** 29/08/2026  
**Dataset de Referência:** `fato_operacao_20260827_210052.csv` (Snapshot de 2.120 linhas/sentidos no pico das 18:00 em São Paulo)

---

## 1. Sumário Executivo & Diagnóstico da Arquitetura

O **Bus-Flow** é uma plataforma de engenharia de dados orientada a eventos na AWS, responsável por ingerir dados de telemetria GTFS/SPTrans em tempo real, enriquecê-los com dados climáticos e de tráfego (HERE Traffic API) e persistir a camada analítica (`fato_operacao`) no **Amazon S3 Trusted**.

Após inspeção aprofundada dos scripts Lambda (`src/lambdas/etl.py`), módulos Terraform e datasets de validação, identificou-se que o algoritmo de classificação de risco operacional operava com **limiares descalibrados**, gerando falsos negativos no disparo de notificações **AWS SNS** e na classificação tabular.

Este documento formaliza:
1. O diagnóstico exato do cenário atual e as causas matemáticas da rigidez anterior.
2. A memória de cálculo de cada indicador do pipeline.
3. A nova matriz de 4 níveis de risco operacional.
4. O plano de alteração de código nos Lambdas e Terraform.

---

## 2. Diagnóstico do Cenário Atual nos Lambdas e Dados

### 2.1 Código Atual do Lambda ETL (`src/lambdas/etl.py:375-388`)
No código em execução, as regras de classificação e envio de alertas estavam definidas assim:

```python
# LÓGICA ATUAL NO LAMBDA:
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
```

### 2.2 O "Efeito Penhasco" e a Ausência de Notificações SNS
No snapshot de horário de pico das 18:00 (2.120 linhas processadas), o score máximo de $GO$ gerado foi **`0.6421`**:

* **Estabilizado ($GO \le 0.60$):** **2.106 linhas (99,34%)**
* **Risco ($0.60 < GO \le 0.80$):** **14 linhas (0,66%)**
* **Alto Risco ($GO > 0.80$):** **0 linhas (0,00%)**
* **Congestionamento ($GO > 0.95$):** **0 linhas (0,00%)**

> [!WARNING]
> **Impacto no AWS SNS:** Como o código só alimenta a lista `alertas_risco` e dispara o tópico **SNS** para $GO > 0.80$ (Alto Risco / Congestionamento), **nenhum alerta operacional era enviado via SNS**, mesmo para linhas com **1 hora de atraso, acidentes na via e trânsito a 5 km/h**.

---

## 3. Memória de Cálculo e Engenharia de Features

O cálculo executado a cada ciclo de 5 minutos pelo Lambda ETL segue as seguintes equações:

### 3.1 `iac_gargalo_climatico` ($IAC$)
* **Conceito:** Peso meteorológico sobre a tração e velocidade do ônibus.
* **Comportamento no Snapshot:** Fixo em **`4.74`** para as 2.120 linhas.
* **Explicação:** Trata-se de uma variável **macroambiental**. Como a medição do tempo (OpenWeather) é capturada por lote para a cidade de São Paulo naquele minuto (25.65°C, sem chuva, visibilidade 10 km), todas as linhas recebem o mesmo valor como contexto comum de contorno.

### 3.2 `ac_aderencia_cronograma` ($AC$)
* **Conceito:** Proporção entre intervalo planejado e tempo real de espera.
* **Fórmula:**
  $$AC = \min\left(1.0, \frac{\text{Headway Planejado (min)}}{\text{Headway Real (min)}}\right)$$
* **No Cluster de 1 Carro Retido:** Headway planejado = 20 min; Headway real = 60 min.
  $$AC = \frac{20.0}{60.0} = \frac{1}{3} \approx \mathbf{0.333}$$

### 3.3 `dfi_demanda_frota_ideal` ($DFI$)
* **Conceito:** Sobrecarga percentual de veículos necessários na linha.
* **Fórmula:**
  $$\text{fator\_demanda} = 1.0 + \frac{IAC + GT}{200.0}$$
  $$\text{frota\_necessaria} = \lceil\text{frota\_planejada} \times \text{fator\_demanda}\rceil$$
  $$DFI = \min\left(100.0, \left(\frac{\text{frota\_necessaria}}{\text{frota\_ativa\_real}}\right) \times 50.0\right)$$
* **No Cluster Crítico:** Linha com frota ativa de 1 veículo e frota necessária de 2 veículos resulta em $DFI = \left(\frac{2}{1}\right) \times 50\% = \mathbf{100.0\%}$ de sobrecarga.

### 3.4 `gt_gargalo_trafego` ($GT$)
* **Conceito:** Lentidão e bloqueios da via calculados a partir da API da HERE.
* **Entradas:** `jam_factor`, razão entre velocidade da via e velocidade freeflow, e `incidente_critico`.
* **Comportamento:** Varia de **$12,02\%$** a **$88,96\%$** (média de $41,79\%$), explicando o porquê do atraso de cada linha individualmente.

### 3.5 `go_gargalo_operacional` ($GO$)
* **Conceito:** Síntese ponderada das dimensões operacional, tráfego e clima:
  $$GO = (0.15 \times HP) + (0.25 \times \frac{IAC}{100}) + (0.25 \times \frac{GT}{100}) + (0.25 \times \frac{DFI}{100}) + (0.10 \times (1.0 - AC))$$
* **Comportamento Estatístico no Dataset (2.120 linhas):**
  * Mínimo: $0.3077$ | Média: $0.4249$ | Mediana: $0.4224$
  * P90: $0.5087$ | P95: $0.5328$ | Máximo: $0.6421$

---

## 4. Nova Lógica Proposta & Comparativo de Resultados

Com a nova matriz de 4 faixas alinhada aos percentis reais de operação:

| Faixa de $GO$ | Categoria Nova | Ação Recomendada | Qtd. Linhas | % da Malha | Comportamento no Pipeline |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **$0\% \text{ a } 45\%$** ($GO \le 0.45$) | 🟢 **Estabilizado** | *Operação Normal* | **1.446** | **$68,21\%$** | Linhas sem gargalo (dentro da média do pico). |
| **$46\% \text{ a } 55\%$** ($0.45 < GO \le 0.55$) | 🟡 **Risco** | *Monitorar Linha em Alerta* | **613** | **$28,92\%$** | Linhas com estresse moderado a alto (P75 a P95). |
| **$56\% \text{ a } 65\%$** ($0.55 < GO \le 0.65$) | 🟠 **Alto Risco** | *Disponibilizar {Déficit} ônibus* | **61** | **$2,88\%$** | **Alerta Crítico / Dispara SNS** (salto de 14 para 61). |
| **$66\% \text{ a } 100\%$** ($GO > 0.65$) | 🔴 **Congestionamento** | *Disponibilizar {Déficit} ônibus / Desvio* | **0** | **$0,00\%$** | **Alerta Máximo / Dispara SNS** (travamento severo). |

---

## 5. Implementação no Repositório (Passo a Passo)

### 5.1 Arquivos a serem modificados
1. `src/lambdas/etl.py` (código-fonte principal da Lambda).
2. `terraform/modules/lambda/lambda_function/etl.py` (cópia utilizada no deploy via Terraform).
3. `docs/pipeline_dados_arquitetura_v3.md` (atualização do dicionário de dados da tabela fato).

### 5.2 Alteração Exata no Código Python do Lambda

Substituir o bloco de classificação de risco em `etl.py` pelo código abaixo:

```python
            # =========================================================================
            # NOVA CLASSIFICAÇÃO DE RISCO OPERACIONAL (Matriz 4 Níveis Calibrada)
            # =========================================================================
            if go_score <= 0.45:
                status_classificacao = "Estabilizado"
                acao_recomendada = "Operação Normal"
            elif go_score <= 0.55:
                status_classificacao = "Risco"
                acao_recomendada = "Monitorar Linha em Alerta"
            elif go_score <= 0.65:
                status_classificacao = "Alto Risco"
                acao_recomendada = f"Disponibilizar {max(1, deficit_operacional)} ônibus"
                alertas_risco.append((codigo_linha, status_classificacao, deficit_operacional))
            else:
                status_classificacao = "Congestionamento"
                acao_recomendada = f"Disponibilizar {max(2, deficit_operacional)} ônibus"
                alertas_risco.append((codigo_linha, status_classificacao, deficit_operacional))
```

---

## 6. Conclusão

A implementação dessa nova lógica no Lambda de ETL:
1. **Corrige o disparo de alertas do AWS SNS**, que passará a notificar os operadores sobre as **61 linhas em Alto Risco** em tempo real.
2. **Garante a integridade do Data Lake Trusted (S3)**, permitindo que consultas SQL no Athena reflitam a real situação operacional do transporte público.
3. Prepara uma base de dados perfeitamente rotulada para o treinamento futuro de modelos preditivos e dashboards analíticos.
