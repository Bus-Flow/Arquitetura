# Relatório Explicativo: Estrutura e Origem dos Valores do Fluxo de Caixa (Business Case BusFlow)

**Projeto:** BusFlow – Automação Inteligente de Despacho de Frota de Ônibus  
**Documento de Referência:** `BC_grupo_06.xlsx` e `Template_Fluxo_de_Caixa_Business_Case.xlsx`  
**Destinatários:** Membros do Grupo 06 / Orientador  
**Data de Atualização:** Março/2027 (Ano 1 do Projeto)

---

## 1. Contexto e Motivação da Atualização

### Por que o Fluxo de Caixa mudou?
O professor substituiu a planilha anterior de fluxo de caixa por um **novo molde oficial** (`Template_Fluxo_de_Caixa_Business_Case.xlsx`), muito mais rigoroso e alinhado aos padrões de avaliação de Business Cases executivos.

* **No modelo antigo do grupo:** Havia apenas uma tabela simples de 16 linhas agregadas, dividida em 6 colunas anuais (*Ano 0 a Ano 5*), sem detalhamento de contas e sem abertura mensal.
* **No novo modelo do professor:** 
  1. O projeto não utiliza uma coluna genérica "Ano 0"; o cronograma começa diretamente no **Ano 1**.
  2. O **Ano 1 é aberto mês a mês (M1 a M12)** para demonstrar o momento de *go-live*, a sazonalidade e a **maior necessidade de capital de giro** (*cash trough*).
  3. Há abertura analítica em **4 tipos de Entradas**, **5 categorias de CAPEX**, **7 contas de OPEX** e **Itens Não Caixa**.
  4. A **Visão Consolidada (Anos 1 a 5)** é vinculada dinamicamente: o Ano 1 puxa automaticamente da soma dos 12 meses (`=O10`, `=O19`, `=O25`...).
  5. O professor exige duas validações mandatórias:
     * *Validação 1:* Total de CAPEX deve reconciliar 100% com a aba `Resumo Investimentos`.
     * *Validação 2:* Total de Entradas deve reconciliar 100% com a aba `Projeção Receitas`.

---

## 2. Entradas de Caixa (Receitas)

### De onde vem o valor das Assinaturas?
A fonte é a aba **`Projeção Receitas`** (linhas 6 a 20):
* **Modelo de Negócio:** 100% B2B SaaS (Software as a Service) por assinatura mensal cobrada de operadores de transporte coletivo e concessionárias.
* **Ticket Médio:** **R$ 10.000,00 / mês por cliente**.
* **Meta do Ano 1:** Conquistar 4 clientes (1 contrato piloto inicial + 3 novos clientes ao longo do ano).

### Por que não usamos uma média reta de R$ 31.200/mês?
Se dividíssemos a meta anual por 12, daria R$ 31.200/mês. Porém, no Mês 1 (M1), a empresa tem apenas **1 cliente** e não pode faturar R$ 31.200 logo de cara. Adotamos o **Ramp-up Realista Trimestral**:

| Período | Clientes Ativos | Faturamento Mensal | Faturamento no Trimestre |
| :--- | :---: | :---: | :---: |
| **M1 a M3 (1º Tri)** | 1 cliente (Piloto) | R$ 10.000,00 / mês | R$ 30.000,00 |
| **M4 a M6 (2º Tri)** | 2 clientes | R$ 20.000,00 / mês | R$ 60.000,00 |
| **M7 a M9 (3º Tri)** | 3 clientes | R$ 30.000,00 / mês | R$ 90.000,00 |
| **M10 a M12 (4º Tri)** | 4 clientes | R$ 40.000,00 / mês | R$ 120.000,00 |
| **Total Ano 1** | **Média: 2,5 clientes** | — | **R$ 300.000,00** |

* A aba `Projeção Receitas` foi calibrada para refletir essa média de 2,5 clientes ativos no Ano 1 ($2,5 \times \text{R\$} 10.000 \times 12 = \text{R\$} 300.000$).
* **Anos 2 a 5:** Puxam exatamente as projeções de expansão da aba `Projeção Receitas`:
  * Ano 2: R$ 813.960,00
  * Ano 3: R$ 1.571.724,00
  * Ano 4: R$ 2.718.566,55
  * Ano 5: R$ 4.129.316,98
  * **Total em 5 Anos:** **R$ 9.533.567,53** (100% conciliado entre as duas abas).

### Por que Subsídios, Aportes e Receitas Adicionais estão zerados (R$ 0,00)?
* O BusFlow é uma startup de tecnologia privada. Não temos subsídios a fundo perdido, incentivos governamentais nem taxas de implantação/setup cobradas à parte.
* **Por que manter a linha com R$ 0,00 em vez de deletar?**  
  A instrução da célula D4 do professor orienta explicitamente: *"substitua, inclua ou zere conforme o projeto"*. Manter a linha com valor `0` comprova para a banca que o grupo analisou essas opções e concluiu conscientemente que não se aplicam ao modelo, além de **evitar que fórmulas quebrem com erro `#REF!`** no consolidado.

---

## 3. Investimentos (CAPEX)

A fonte é a aba **`Resumo Investimentos`** (linha 17):

1. **Equipamentos / Hardware:**
   * **Mês 1 (M1):** **R$ 29.495,00** $\rightarrow$ Compra inicial de 5 notebooks corporativos Dell/Lenovo (R$ 5.899,00/unidade) para equipar os desenvolvedores e analistas.
   * **M2 a M12 (e Anos 2, 4 e 5):** **R$ 0,00** $\rightarrow$ Não há novas compras nesses períodos.
   * **Ano 3:** **R$ 34.144,15** $\rightarrow$ Ciclo de reposição e renovação tecnológica integral dos 5 notebooks corporativos após 3 anos de uso, corrigido pela inflação acumulada de 5% a.a. ($1,1576 \times 29.495$).
   * **Total CAPEX em 5 Anos:** **R$ 63.639,15** $\rightarrow$ Reconciliação exata de 100% com a célula H10 de `Resumo Investimentos`.

2. **Por que o Desenvolvimento de Software está zerado no CAPEX?**
   * Na aba `Resumo Investimentos`, o grupo optou por classificar a folha dos programadores como despesa operacional de pessoal (OPEX). Portanto, para não duplicar custos, a linha de CAPEX de desenvolvimento fica zerada e todo o valor é apropriado na linha de Pessoal do OPEX.

---

## 4. Despesas Operacionais (OPEX) – Detalhamento das 7 Contas

A fonte é a tabela detalhada da aba **`Resumo Investimentos`** (linhas 15 a 27). Todas as despesas possuem reajuste anual de 5% a.a. (premissa macroeconômica de inflação):

| Linha do Fluxo de Caixa | Item Correspondente no `Resumo Investimentos` | Valor Ano 1 (Total) | Distribuição no Ano 1 (M1 a M12) |
| :--- | :--- | :---: | :--- |
| **1. Pessoas / Operação** | Equipe Dev / UX / DevOps (Linha 15) | **R$ 320.052,60** | **R$ 26.671,05 / mês** fixos (3 desenvolvedores plenos, ~R$ 8.890/mês por dev com encargos). |
| **2. Cloud / Infraestrutura** | Cloud AWS (Linha 18) | **R$ 46.872,00** | **R$ 3.906,00 / mês** fixos (servidores EC2, banco relacional RDS, cache Redis, S3 e rede). |
| **3. Licenças / Assinaturas** | Claude API + Observabilidade + Domínio (Linhas 19, 20 e 24) | **R$ 15.507,00** | **M1:** R$ 1.330,75 (inclui R$ 42 do Registro.br).<br>**M2 a M12:** R$ 1.288,75/mês (R$ 288,75 API Claude + R$ 1.000 SaaS Grafana Cloud Pro/Sentry). |
| **4. Suporte / Sustentação** | Equipe de Suporte Técnico (Linha 23) | **R$ 86.280,00** | **R$ 7.190,00 / mês** fixos (2 analistas plenos para atendimento técnico contínuo ao CCO das operadoras). |
| **5. Marketing / Aquisição** | Go-To-Market B2B Lançamento + Recorrente (Linhas 21 e 22) | **R$ 48.000,00** | **M1:** R$ 15.000,00 (R$ 12k de verba inicial de lançamento institucional + R$ 3k recorrente).<br>**M2 a M12:** R$ 3.000,00/mês para prospecção ativa outbound e eventos do setor. |
| **6. Serviços de Terceiros** | Contabilidade + Capacitação (Linhas 16 e 25) | **R$ 8.200,00** | **M1:** R$ 4.350,00 (R$ 4.000 de treinamento técnico inicial + R$ 350 de contabilidade).<br>**M2 a M12:** R$ 350,00/mês de honorários contábeis. |
| **7. Outro OPEX** | Reserva de Contingência Operacional (Linha 27) | **R$ 2.000,00** | **R$ 166,66 / mês** para eventuais despesas operacionais imprevistas. |
| **TOTAL OPEX ANO 1** | **Soma das 7 linhas de despesas** | **R$ 526.911,60** | **M1:** R$ 57.570,46<br>**M2 a M12:** R$ 42.667,38 / mês |

---

## 5. Dinâmica do Fluxo de Caixa e Indicadores de Viabilidade

### A Curva de Queima de Caixa (*Burn Rate*) no Ano 1
A grande virtude do modelo mensal é demonstrar a maturidade financeira do projeto:
* **Mês 1:** Há o desembolso mais pesado do ano (compra dos computadores de R$ 29,5k + lançamento de marketing de R$ 12k + treinamento de R$ 4k), com faturamento inicial de R$ 10k $\rightarrow$ **Resultado: -R$ 77.065,47**.
* **Mês 2 e 3:** O caixa estabiliza em **-R$ 32.667,38 / mês**.
* **Mês 4 a 6:** Entra o 2º cliente (R$ 20k/mês) $\rightarrow$ o déficit mensal cai para **-R$ 22.667,38 / mês**.
* **Mês 7 a 9:** Entra o 3º cliente (R$ 30k/mês) $\rightarrow$ o déficit mensal cai para **-R$ 12.667,38 / mês**.
* **Mês 10 a 12:** Entra o 4º cliente (R$ 40k/mês) $\rightarrow$ a queima de caixa quase zera, ficando em apenas **-R$ 2.667,38 / mês**!
* **Ano 2 (Mês 13 em diante):** A empresa atinge o *breakeven* operacional e passa a gerar caixa líquido positivo (+R$ 275.902,82 no ano).

### Principais Indicadores Calculados
1. **Maior Necessidade de Caixa (Capital de Giro no Ano 1):** **R$ 256.406,60**. É o valor total que a empresa precisa ter reservado no início para cobrir a operação do primeiro ano até que a receita atinja escala.
2. **Payback:** Ocorre no **Ano 2** (o saldo acumulado vira positivo em +R$ 19.496,22). O capital investido é recuperado em menos de 2 anos.
3. **VPL (Valor Presente Líquido a 12% a.a.):** **R$ 4.023.708,24** $\rightarrow$ Projeto altamente gerador de valor econômico.
4. **TIR (Taxa Interna de Retorno):** **172,3% a.a.** $\rightarrow$ Retorno muito superior à TMA (Taxa Mínima de Atratividade de 12% a.a.).
5. **Consistência do Arquivo:** **0 erros de referência (`#REF!`)** em todas as 9 abas do `BC_grupo_06.xlsx`.
