# Análise Técnica do Arquivo Gerado: `fato_operacao_20260818_021718.csv`

**Arquivo de Referência:** [`fato_operacao_20260818_021718.csv`](./fato_operacao_20260818_021718.csv)  
**Origem:** Camada TRUSTED S3 (`s3://trusted-busflow-3f2ee255/fato_operacao_frota/ano=2026/mes=08/dia=18/`)  
**Data/Hora do Processamento:** 18/08/2026 02:17 UTC (`23:16` Horário de Brasília)

---

## 1. Resumo Executivo e Qualidade dos Dados

* **Total de Linhas Processadas:** ~1.975 linhas operacionais de ônibus em São Paulo.
* **Integridade dos Dados:** ✅ **100% íntegro**. Sem valores nulos (`NaN`), colunas bem tipadas e alinhadas.
* **Horário da Coleta:** `23:16` (Horário Noturno de São Paulo).
* **Classificação Global:** **Estabilizado** ($GO$ médio entre `0.24` e `0.42`), o que reflete com precisão a realidade de tráfego e clima da cidade às 23h.

---

## 2. Análise dos Fatores Externos (Clima, Tráfego e Horário)

| Fator | Medição no Arquivo | Sub-índice Calculado | Interpretação |
| :--- | :--- | :---: | :--- |
| **Clima (OpenWeather)** | Temp: `21.27°C`<br>Chuva: `0.0 mm`<br>Visibilidade: `10.000 m`<br>Vento: `2.06 m/s`<br>Evento ID: `800` (Céu limpo) | **$IAC = 4.56$** *(Normal)* | Condições meteorológicas excelentes. O clima não gerou impacto negativo na circulação viária. |
| **Tráfego (HERE/Fallback)** | Jam Factor: `3.0`<br>Velocidade: `22.5 km/h`<br>Freeflow: `45.0 km/h`<br>Incidentes: `0` | **$GT = 23.5$** *(Fluido)* | Vias livres, compatível com a fluidez normal do horário noturno. |
| **Horário de Pico** | `23:16` | **$HP = 0.20$** *(Tranquilo)* | O classificador identificou corretamente o período de vale/madrugada, reduzindo o peso de criticidade do modelo. |

---

## 3. Análise da Operação por Linha (Destaques Reais)

O pipeline identificou diferentes perfis de linhas da SPTrans operando às 23:16:

### A. Linhas Troncais de Alta Demanda (Exemplos):
* **Linha `3459-10` (Term. Pq. D. Pedro II $\leftrightarrow$ Itaim Paulista):**
  * **Frota Ativa Real:** `28 ônibus`
  * **Headway Real:** `3.0 minutos`
  * **Aderência ao Cronograma ($AC$):** `1.0` (Excelente)
  * **Gargalo Operacional ($GO$):** `0.2564` $\rightarrow$ **Estabilizado**
* **Linha `6000-10` (Term. Sto. Amaro $\leftrightarrow$ Term. Parelheiros):**
  * **Frota Ativa Real:** `14 a 15 ônibus`
  * **Headway Real:** `4.0 a 4.3 minutos`
  * **Gargalo Operacional ($GO$):** `0.2609` $\rightarrow$ **Estabilizado**
* **Linha `2290-10` (Term. Pq. D. Pedro II $\leftrightarrow$ Term. São Mateus):**
  * **Frota Ativa Real:** `15 ônibus` | **Headway:** `4.0 minutos` | **$GO$:** `0.2585`

### B. Linhas Locais / Alimentadoras (1 a 2 ônibus na madrugada):
* **Linhas como `6258-31`, `N301-11`, `4742-10`, `6063-41`:**
  * **Frota Ativa:** `1 ônibus` | **Headway Real:** `60 minutos`
  * **Aderência ($AC$):** `0.333` | **DFI (%):** `100.0%`
  * **Gargalo Operacional ($GO$):** `0.4168` $\rightarrow$ Permanece em **Estabilizado** (pois é esperado pouca frota às 23h e o $HP$ é $0.2$).

---

## 4. Coerência Matemática das Fórmulas

Podemos auditar o cálculo passo a passo através de uma linha real do arquivo:

**Exemplo Linha `519M-10` (São Mateus):**
$$IAC = 4.56 \quad | \quad IIV = 23.50 \quad | \quad HP = 0.20 \quad | \quad AC = 0.667 \quad | \quad DFI = 75.00$$

Aplicando a fórmula do **Gargalo Operacional Geral ($GO$)**:
$$GO = (0.15 \times 0.20) + (0.25 \times 0.0456) + (0.25 \times 0.235) + (0.25 \times 0.75) + (0.10 \times (1 - 0.667))$$
$$GO = 0.0300 + 0.0114 + 0.0587 + 0.1875 + 0.0333 = \mathbf{0.3209}$$

* **Resultado no CSV:** exatamente **`0.3209`**!
* **Status:** `Estabilizado` ($0.3209 \le 0.60$).
* **Ação:** `Operação Normal`.

---

## 5. Prontidão para a Camada de Machine Learning

O dataset gerado na camada TRUSTED está pronto para ser consumido pelo SageMaker Notebook ([test_pipeline.ipynb])

1. **Features Numéricas Contínuas (Inputs do Modelo):** `frota_ativa_real`, `headway_real_min`, `temperatura_c`, `sensacao_termica_c`, `chuva_1h_mm`, `visibilidade_m`, `vento_velocidade_ms`, `jam_factor`, `velocidade_via_kmh`.
2. **Features Categóricas e Temporais:** `linha_codigo`, `sentido`, `dia_semana`, `hora_minuto`.
3. **Sub-índices de Explicabilidade:** `iac_gargalo_climatico`, `gt_gargalo_trafego`, `hp_horario_pico`, `ac_aderencia_cronograma`, `dfi_demanda_frota_ideal`.
4. **Targets (Variáveis Alvo):**
   * **Regressão:** Previsão de `deficit_operacional` ou `go_gargalo_operacional`.
   * **Classificação:** Previsão de `status_classificacao` ou `acao_recomendada`.
