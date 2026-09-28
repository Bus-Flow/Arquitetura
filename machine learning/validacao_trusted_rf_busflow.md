# Registro Final de Validação — Random Forest BusFlow

## 1. Objetivo

Validar a capacidade do Random Forest de **antecipar em 30 minutos o indicador de gargalo operacional (GO)** do BusFlow, utilizando dados da camada TRUSTED e evitando que o modelo apenas reproduza a classificação do instante atual.

A formulação utilizada foi:

**X(t) → GO(t+30 min)**

O alvo do modelo é `target_30min`, correspondente ao `go_gargalo_operacional` observado 30 minutos após o instante de origem.

---

## 2. Base de dados e recorte temporal

- TRUSTED consolidado: **35.698 registros**.
- Pares válidos para previsão t+30: **8.362 registros**.
- Treino: **4.174 registros**.
  - origem 17:00: 2.082 registros;
  - origem 17:30: 2.092 registros.
- Validação temporal: **4.188 registros**.
  - origem 18:00: 2.096 registros;
  - origem 18:30: 2.092 registros.
- Alvo: `go_gargalo_operacional` futuro, armazenado como `target_30min`.
- Regra operacional observada: **GO >= 0,60 → Risco**.

O split foi temporal, e não aleatório, para aproximar a situação real de previsão: o modelo aprende com períodos anteriores e é avaliado em períodos posteriores.

### Desbalanceamento

No conjunto de treino:

- Estabilizado: **4.107** registros;
- Risco: **67** registros;
- proporção de Risco: **1,61%**.

Na validação:

- Estabilizado: **4.098** registros;
- Risco: **90** registros.

Esse forte desbalanceamento torna a acurácia global inadequada como métrica principal. Um modelo que previsse todos os registros como Estabilizado teria aproximadamente 98% de acurácia, mas recall igual a zero para Risco.

---

## 3. Configuração base do Random Forest

Os experimentos mantiveram, salvo indicação explícita, a seguinte configuração:

```python
RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
```

As variáveis categóricas `linha_codigo` e `hora_minuto` foram transformadas com `OneHotEncoder(handle_unknown="ignore")`.

---

## 4. Auditoria das features e risco de leakage

Como o `go_gargalo_operacional` é um indicador composto calculado na camada TRUSTED, foi necessário separar variáveis primitivas/observáveis de subíndices derivados.

### Features primitivas/observáveis

- `linha_codigo`
- `sentido`
- `dia_semana`
- `hora_minuto`
- `frota_ativa_real`
- `headway_real_min`
- `frota_planejada`
- `headway_planejado_min`
- `temperatura_c`
- `sensacao_termica_c`
- `chuva_1h_mm`
- `visibilidade_m`
- `vento_velocidade_ms`
- `jam_factor`
- `velocidade_via_kmh`
- `velocidade_freeflow_kmh`
- `incidente_critico`

### Features derivadas/subíndices

- `iac_gargalo_climatico`
- `gt_gargalo_trafego`
- `hp_horario_pico`
- `ac_aderencia_cronograma`
- `dfi_demanda_frota_ideal`

`status_classificacao` e `acao_recomendada` não foram utilizados como features, pois são informações posteriores/associadas à decisão operacional.

A auditoria é importante porque os subíndices participam da construção do GO. Assim, uma importância elevada dessas variáveis pode refletir a fórmula do próprio alvo, e não uma relação preditiva independente.

---

## 5. Modelo A — primitivas + subíndices

O Modelo A utilizou **22 features**, incluindo os cinco subíndices derivados.

Dimensões após pré-processamento:

- treino: `(4174, 1102)`;
- validação: `(4188, 1102)`.

### Métricas de regressão

- MAE: **0,039091**;
- RMSE: **0,049574**;
- R²: **0,272463**.

### Classificação usando GO previsto >= 0,60

Matriz de confusão:

```text
[[4098,    0],
 [  90,    0]]
```

- Riscos reais: **90**;
- riscos previstos: **0**;
- recall de Risco: **0%**.

A acurácia aproximada de 98% é enganosa devido ao desbalanceamento.

### Comportamento nos casos de Risco

| Faixa de GO real | Registros | GO real médio | Previsto médio | Erro médio |
|---|---:|---:|---:|---:|
| 0,60–0,62 | 36 | 0,608908 | 0,506140 | 0,102768 |
| 0,62–0,65 | 36 | 0,631667 | 0,510741 | 0,120926 |
| 0,65–0,70 | 18 | 0,664111 | 0,527548 | 0,136563 |
| >= 0,70 | 0 | — | — | — |

O modelo apresentou **subestimação sistemática dos casos de maior risco**, com aumento do erro conforme a severidade do GO real.

### Importância de features — observação

A maior importância foi observada em `dfi_demanda_frota_ideal` (~0,366), seguida por `incidente_critico` (~0,100). Como DFI e outros subíndices participam da construção do GO, essas importâncias não devem ser interpretadas como causalidade nem como descoberta independente.

---

## 6. Modelo B — somente features primitivas

Para reduzir a dependência dos componentes derivados do próprio GO, o Modelo B removeu:

- `iac_gargalo_climatico`;
- `gt_gargalo_trafego`;
- `hp_horario_pico`;
- `ac_aderencia_cronograma`;
- `dfi_demanda_frota_ideal`.

O modelo ficou com **17 features**.

Dimensões após pré-processamento:

- treino: `(4174, 1097)`;
- validação: `(4188, 1097)`.

### Métricas

- MAE: **0,039028**;
- RMSE: **0,049504**;
- R²: **0,274513**.

O Modelo B apresentou melhora pequena em relação ao Modelo A nas três métricas de regressão. A diferença é pequena e não deve ser superinterpretada, mas mostra que a retirada dos subíndices não prejudicou o modelo.

### Classificação com limiar 0,60

```text
[[4098,    0],
 [  90,    0]]
```

Novamente:

- riscos reais: **90**;
- riscos previstos: **0**;
- recall de Risco: **0%**.

### Casos reais de Risco

- registros: **90**;
- GO real médio: **0,629052**;
- previsão média: **0,515214**;
- maior GO real: **0,6942**;
- maior previsão entre os riscos reais: **0,593205**;
- MAE apenas nos riscos: **0,113839**.

| Faixa de GO real | Registros | GO real médio | Previsto médio | Erro médio |
|---|---:|---:|---:|---:|
| 0,60–0,62 | 36 | 0,608908 | 0,507181 | 0,101728 |
| 0,62–0,65 | 36 | 0,631667 | 0,514222 | 0,117445 |
| 0,65–0,70 | 18 | 0,664111 | 0,533263 | 0,130848 |

O Modelo B reduziu ligeiramente os erros nas três faixas de risco em relação ao Modelo A, mas manteve a tendência de subestimar os casos críticos.

### Principais importâncias no Modelo B

1. `incidente_critico`: ~0,2564
2. `headway_real_min`: ~0,1539
3. `jam_factor`: ~0,0791
4. `frota_planejada`: ~0,0689
5. `frota_ativa_real`: ~0,0667
6. `velocidade_freeflow_kmh`: ~0,0436
7. `velocidade_via_kmh`: ~0,0380

As importâncias indicam contribuição preditiva no Random Forest, não causalidade operacional.

---

## 7. Comparação consolidada — Modelo A × Modelo B

| Métrica | Modelo A | Modelo B |
|---|---:|---:|
| MAE | 0,039091 | **0,039028** |
| RMSE | 0,049574 | **0,049504** |
| R² | 0,272463 | **0,274513** |
| Riscos reais | 90 | 90 |
| Riscos previstos em 0,60 | 0 | 0 |
| Recall Risco em 0,60 | 0% | 0% |

Tempos de execução variaram entre execuções e dependem do ambiente. Em uma execução consolidada, o Modelo A treinou em ~3,90 s e o Modelo B em ~3,00 s, com predição em ~0,049 s para ambos. Esses tempos são indicativos e não devem ser tratados como benchmark de infraestrutura.

O Modelo B foi mantido como base dos experimentos seguintes por apresentar regressão ligeiramente melhor e reduzir a dependência de subíndices derivados do alvo.

---

## 8. Modelo B2 — ponderação dos registros de Risco

Como apenas 67 dos 4.174 registros de treino eram Risco, foi testada ponderação via `sample_weight` para aumentar a influência desses registros no treinamento.

Primeiro experimento:

```python
pesos_treino_b2 = np.where(
    y_treino_b >= 0.60,
    5.0,
    1.0
)
```

- peso 1: **4.107 registros**;
- peso 5: **67 registros**;
- peso médio: **1,064207**.

### Resultado B2 — peso 5×

- MAE: **0,039341**;
- RMSE: **0,049892**;
- R²: **0,263084**;
- previsão mínima: **0,419992**;
- previsão média: **0,474374**;
- previsão máxima: **0,606251**.

Usando limiar 0,60:

```text
[[4097,    1],
 [  90,    0]]
```

O único registro classificado como Risco foi falso positivo. Os 90 riscos reais continuaram não detectados nesse limiar.

### Distribuição dos scores por classe real

| Classe real | N | Mínimo | Média | Mediana | Máximo |
|---|---:|---:|---:|---:|---:|
| Estabilizado | 4098 | 0,419992 | 0,473341 | 0,480219 | 0,606251 |
| Risco | 90 | 0,445911 | **0,521434** | **0,524525** | 0,596913 |

Percentis das previsões dos riscos:

- P10: 0,487787
- P25: 0,496006
- P50: 0,524525
- P75: 0,543380
- P90: 0,560195
- P95: 0,568282
- P99: 0,594583

Percentis dos estabilizados:

- P10: 0,435622
- P25: 0,443443
- P50: 0,480219
- P75: 0,499355
- P90: 0,509587
- P95: 0,526671
- P99: 0,553908

Apesar da sobreposição entre as classes, os riscos apresentam scores médios e medianos maiores. Isso mostra que há **separação parcial**, mesmo que as previsões estejam comprimidas abaixo de 0,60.

---

## 9. Limiar operacional × limiar preditivo

Foi mantida a definição real:

**GO real >= 0,60 → Risco.**

Entretanto, o score produzido pelo ML pode usar um **limiar preditivo de alerta antecipado** diferente. Isso não redefine a regra operacional; apenas permite emitir um alerta preventivo 30 minutos antes.

No B2 com peso 5×, o maior F1 entre os limiares testados ocorreu em **0,53**:

- TP: **42**;
- FP: **186**;
- FN: **48**;
- TN: **3.912**;
- recall: **46,67%**;
- precisão: **18,42%**;
- especificidade: **95,46%**;
- F1: **0,2642**.

No limiar 0,60, o recall continuou em 0%.

---

## 10. Comparação B × B2 nos limiares

A comparação mostrou que a ponderação altera principalmente a região intermediária dos scores.

Exemplo no limiar 0,53:

| Métrica | B (1×) | B2 (5×) |
|---|---:|---:|
| TP | 21 | **42** |
| FP | **100** | 186 |
| FN | 69 | **48** |
| Recall | 23,33% | **46,67%** |
| Precisão | 17,36% | **18,42%** |
| Especificidade | **97,56%** | 95,46% |
| F1 | 0,1991 | **0,2642** |

No mesmo limiar, o peso 5× dobrou os riscos detectados, porém aumentou os falsos alertas.

Ao comparar o melhor limiar observado de cada um:

- B 1× / 0,52: 43 TP, 216 FP, recall 47,78%, precisão 16,60%, F1 0,2464.
- B2 5× / 0,53: 42 TP, 186 FP, recall 46,67%, precisão 18,42%, F1 0,2642.

Os dois detectam quantidade semelhante de riscos, mas o B2 5×/0,53 gerou 30 falsos alertas a menos nesse recorte.

---

## 11. Experimento controlado de pesos

Foram testados os pesos **1×, 2×, 3×, 5×, 7× e 10×**, mantendo constantes as features, split temporal, hiperparâmetros e conjunto de validação.

### Métricas de regressão por peso

| Peso Risco | MAE | RMSE | R² | Treino (s) | Predição (s) | Pred. média | Pred. máx. |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1× | **0,039028** | **0,049504** | **0,274513** | 4,163213 | 0,063463 | 0,472726 | 0,593205 |
| 2× | 0,039162 | 0,049657 | 0,270019 | 3,011357 | 0,045254 | 0,473447 | 0,603065 |
| 3× | 0,039163 | 0,049657 | 0,270032 | 3,773969 | 0,067781 | 0,473625 | 0,605427 |
| 5× | 0,039341 | 0,049892 | 0,263084 | 3,888397 | 0,044098 | 0,474374 | 0,606251 |
| 7× | 0,039334 | 0,049923 | 0,262172 | 2,881715 | 0,044370 | 0,474592 | 0,599575 |
| 10× | 0,039428 | 0,050018 | 0,259364 | 2,912460 | 0,045427 | 0,475378 | 0,598000 |

O aumento do peso deslocou levemente as previsões para cima, mas houve tendência de piora das métricas globais de regressão. O efeito não foi monotônico no valor máximo previsto: aumentar o peso não significa necessariamente produzir scores maiores ou melhor detecção.

---

## 12. Experimento final — peso × limiar

Foram avaliadas **90 combinações**: 6 pesos × 15 limiares de alerta.

A tabela abaixo mostra o limiar com maior F1 observado para cada peso:

| Peso | Limiar | TP | FP | FN | Recall | Precisão | Especificidade | F1 | MAE | RMSE | R² |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1× | 0,52 | 43 | 216 | 47 | 47,78% | 16,60% | 94,73% | 0,2464 | 0,0390 | 0,0495 | **0,2745** |
| 2× | 0,52 | 44 | 231 | 46 | 48,89% | 16,00% | 94,36% | 0,2411 | 0,0392 | 0,0497 | 0,2700 |
| 3× | 0,53 | 35 | 159 | 55 | 38,89% | 18,04% | 96,12% | 0,2465 | 0,0392 | 0,0497 | 0,2700 |
| **5×** | **0,53** | **42** | **186** | **48** | **46,67%** | **18,42%** | **95,46%** | **0,2642** | 0,0393 | 0,0499 | 0,2631 |
| 7× | 0,54 | 31 | **119** | 59 | 34,44% | **20,67%** | **97,10%** | 0,2583 | 0,0393 | 0,0499 | 0,2622 |
| 10× | 0,53 | **47** | 232 | **43** | **52,22%** | 16,85% | 94,34% | 0,2547 | 0,0394 | 0,0500 | 0,2594 |

### Interpretação

- **1×** preservou a melhor qualidade de regressão.
- **10×** obteve o maior recall entre os melhores limiares de cada peso (52,22%), mas com 232 falsos positivos e pior R².
- **7×** obteve a maior precisão (20,67%) e o menor número de falsos positivos (119), porém detectou apenas 31 dos 90 riscos.
- **5× / 0,53** apresentou o **maior F1 observado (0,2642)**, detectando 42 dos 90 riscos e produzindo 186 falsos alertas.

Portanto, para esta etapa experimental, **peso 5× e limiar preditivo 0,53 foram selecionados como configuração candidata pelo critério de maior F1 da classe Risco**, mantendo-se `GO >= 0,60` como definição real de Risco.

Essa seleção representa um compromisso entre recall e precisão; não significa que seja universalmente a melhor configuração operacional.

---

## 13. Configuração candidata resultante

### Modelo

Random Forest Regressor com features primitivas (Modelo B).

### Hiperparâmetros

- `n_estimators=100`;
- `max_depth=10`;
- `random_state=42`;
- `n_jobs=-1`.

### Ponderação

- registros Estabilizados: peso 1;
- registros de Risco no treino (`target_30min >= 0,60`): peso **5**.

### Regras distintas

**Regra de verdade operacional:**

```text
GO real >= 0,60 → Risco
```

**Configuração candidata para alerta antecipado do ML:**

```text
GO previsto >= 0,53 → Alerta preventivo de possível Risco em t+30
```

O limiar 0,53 não altera a classificação oficial do GO. Ele funciona somente como limiar preditivo para antecipação.

---

## 14. Conclusões da validação

1. O Random Forest apresentou capacidade moderada de explicar a variação futura do GO, com R² na faixa de aproximadamente **0,26–0,27** nos experimentos principais.
2. MAE e RMSE globais foram relativamente baixos em escala absoluta, mas isso não foi suficiente para garantir detecção dos eventos raros de Risco.
3. Usar diretamente `0,60` como limiar da previsão fez os modelos falharem na detecção dos 90 riscos da validação.
4. Os riscos reais receberam, em média, scores maiores que os casos estabilizados, indicando **separação parcial entre as classes**.
5. A retirada dos subíndices derivados no Modelo B não prejudicou a regressão e reduziu a dependência direta de componentes usados na construção do GO.
6. A ponderação dos registros raros alterou a distribuição das previsões e melhorou alguns compromissos entre recall e falsos positivos, mas piorou levemente as métricas globais de regressão.
7. Entre as combinações testadas, **peso 5× / limiar 0,53 apresentou o maior F1 observado para Risco (0,2642)**.
8. Mesmo nessa configuração, a precisão permaneceu baixa (**18,42%**) e 48 dos 90 riscos não foram detectados. Portanto, o modelo ainda não deve ser descrito como uma solução final de alta confiabilidade para decisão automática.
9. O resultado é mais adequado para uma **PoC de alerta preventivo/apoio à decisão**, na qual o score auxilia o operador, do que para despacho autônomo baseado exclusivamente na previsão atual.

---

## 15. Limitações metodológicas

### Poucos eventos de Risco

O treinamento possui apenas **67 registros de Risco**, o que limita a aprendizagem de padrões raros.

### Janela temporal restrita

A validação atual utiliza períodos do mesmo dia e poucas janelas consecutivas de 30 minutos. O comportamento pode mudar em outros dias, horários, condições climáticas, linhas e situações de trânsito.

### Ajuste e avaliação no mesmo conjunto de validação

Os pesos e os limiares foram comparados utilizando o mesmo conjunto de 4.188 registros. Portanto, o desempenho da configuração 5×/0,53 **não constitui validação independente final**.

Uma avaliação metodologicamente mais forte deve congelar a configuração selecionada e testá-la em dados temporais ainda não utilizados na escolha do peso e do limiar.

### Target engenheirado

O GO é um indicador calculado a partir de regras/subíndices do pipeline. Mesmo removendo os subíndices explícitos no Modelo B, várias features primitivas também alimentam esses cálculos. O alvo deve ser descrito como um indicador operacional engenheirado, e não como uma medição direta de demanda real de passageiros.

### Feature importance

Importância do Random Forest não implica causalidade. As variáveis mais importantes não devem ser descritas como causas dos gargalos sem análise causal adicional.

---

## 16. Próxima validação recomendada

Para transformar a configuração candidata em uma conclusão mais robusta:

1. congelar o Modelo B com peso **5×** e limiar preditivo **0,53**;
2. coletar dados de outros dias e diferentes condições operacionais/climáticas;
3. avaliar o modelo sem reajustar peso ou threshold nesse novo conjunto;
4. medir MAE, RMSE, R², recall, precisão, F1, falsos positivos e falsos negativos;
5. avaliar o custo operacional de falso alerta versus risco não detectado;
6. comparar, como experimento futuro, a regressão atual com um modelo de classificação específico para antecipação de Risco.

---

## 17. Síntese para apresentação do TCC

> O BusFlow foi estruturado para prever o indicador de gargalo operacional 30 minutos à frente. A auditoria mostrou que a alta acurácia global não representava boa detecção de riscos devido ao forte desbalanceamento dos dados. Após remover subíndices derivados do alvo e testar ponderações controladas para eventos raros, a configuração candidata Random Forest com peso 5× e limiar preventivo 0,53 apresentou o maior F1 observado para a classe Risco (0,2642), antecipando 42 dos 90 eventos de risco da validação. O limiar operacional de Risco permanece em GO >= 0,60; 0,53 é apenas um limiar de alerta antecipado do modelo. Os resultados sustentam a viabilidade da abordagem como PoC de apoio à decisão, mas indicam necessidade de validação temporal independente e maior volume de eventos críticos antes de uso operacional automatizado.

---

## 18. Status da análise

**Etapa experimental atual: concluída.**

Configuração candidata registrada para próxima validação independente:

**Modelo B (features primitivas) + Random Forest Regressor + peso de Risco 5× + limiar preditivo 0,53 + horizonte de 30 minutos.**

