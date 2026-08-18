# Registro de Mudança: Plano de Reorganização Estrutural do Repositório BusFlow

Este documento registra a reestruturação arquitetural e organizacional do repositório BusFlow para adequação às melhores práticas de Engenharia de Software e Data Lakehouse.

---

## 1. Motivação e Objetivos da Reorganização

1. **Eliminar dispersão de arquivos:** Diagramas BPMN e desenhos de arquitetura estavam soltos na raiz e em pastas redundantes.
2. **Centralizar dados de exemplo e amostras:** Amostras de dados brutos e datasets da camada TRUSTED agora estão organizados em `data/raw/` e `data/samples/`.
3. **Desacoplar código-fonte de infraestrutura:**
   * Código-fonte das funções Lambda e coletores locais agora residem em `src/`.
   * Toda a infraestrutura como código (IaC) foi unificada em `terraform/`.
4. **Incorporação dos artefatos acadêmicos:** Os arquivos de monografia/artigo (`BusFlow.docx`, `BusFlow.pdf`) e exportações gráficas de alta resolução foram integrados na pasta `Docs/tcc/` e `Docs/diagramas/`.

---

## 2. Mapa Comparativo: Antes vs. Depois

| Local Antigo | Novo Caminho Padronizado | Descrição |
| :--- | :--- | :--- |
| `..\BusFlow\BusFlow.docx`, `.pdf` | `Docs/tcc/` | Documentação oficial e monografia do TCC. |
| `..\BusFlow\*.bpmn`, `*.svg` e raiz | `Docs/diagramas/bpmn/` | Modelagem de processos de negócio As-Is e To-Be. |
| `Desenhos/` e `..\BusFlow\Arquitetura\` | `Docs/diagramas/arquitetura/` | Diagramas de arquitetura em `.drawio`, `.svg` e `.png`. |
| `Docs/fato_operacao_*.csv` | `data/samples/fato_operacao_exemplo.csv` | Dataset consolidado gerado na camada TRUSTED. |
| `Automacao/data/raw/gtfs/*.zip` | `data/raw/gtfs/` | Arquivos de dados estáticos GTFS da SPTrans. |
| `Exemplos/raw_busflow_*.json` | `data/raw/` | Amostras de payloads brutos capturados das APIs. |
| `APIS/` e `Automacao/*.py` | `src/collectors_local/` | Scripts de apoio para desenvolvimento e coleta local. |
| `Terraform/.../lambda_function/*.py` | `src/lambdas/` | Código-fonte modular das Lambdas AWS. |
| `Terraform/terraform-project/*` | `terraform/` | Módulos e infraestrutura Terraform (IaC). |

---

## 3. Estrutura Final do Repositório

```text
BusFlow/
├── Docs/                              # Documentações técnicas e acadêmicas
│   ├── pipeline_dados_arquitetura_v3.md   # Especificação da arquitetura e camadas RAW/TRUSTED
│   ├── seguranca_gatilhos_e_variaveis.md  # Variáveis centralizadas, segurança e EventBridge
│   ├── exemplo_dataset_trusted_analise.md # Análise matemática e auditoria da camada TRUSTED
│   ├── plano_reorganizacao_repositorio.md # Registro histórico da reorganização (este arquivo)
│   ├── diagramas/                     # Diagramas visuais organizados
│   │   ├── bpmn/                      # Processos As-Is e To-Be (.bpmn, .svg, .png)
│   │   └── arquitetura/               # Diagramas de arquitetura (.drawio, .svg, .xml)
│   └── tcc/                           # Monografia e relatórios (BusFlow.docx, BusFlow.pdf)
│
├── data/                              # Amostras e dados locais controlados
│   ├── raw/                           # Payloads brutos JSON e ZIPs GTFS
│   │   └── gtfs/                      # Arquivos GTFS SPTrans
│   └── samples/                       # Datasets tratados (fato_operacao_exemplo.csv)
│
├── src/                               # Código-fonte Python da aplicação
│   ├── lambdas/                       # Funções Lambda Serverless da AWS
│   │   ├── ingestion_realtime.py      # Ingestão tempo real (SPTrans + OpenWeather)
│   │   ├── ingestion_gtfs.py          # Ingestão inteligente do GTFS
│   │   └── etl.py                     # Motor ETL de cálculo de índices operacionais
│   └── collectors_local/              # Scripts auxiliares para execução local
│       ├── coletor_tempo_real.py      # Coletor local Olho Vivo + Clima
│       └── coletor_gtfs.py            # Coletor local GTFS
│
├── terraform/                         # Infraestrutura como Código (IaC)
│   ├── main.tf                        # Módulo raiz da arquitetura AWS
│   ├── variables.tf                   # Declaração centralizada de variáveis
│   ├── outputs.tf                     # Outputs de recursos provisionados
│   ├── terraform.tfvars.example       # Template seguro para credenciais
│   └── modules/                       # Módulos: ec2, lambda, network, rds, s3, sagemaker, sns
│
├── .env.example                       # Template de variáveis de ambiente locais
├── .gitignore                         # Regras rigorosas de proteção de segredos
└── README.md                          # Portal central de documentação e onboarding
```
