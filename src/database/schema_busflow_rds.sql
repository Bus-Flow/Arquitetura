-- ============================================================================
-- SCRIPT DE CRIAÇÃO DO BANCO DE DADOS RDS POSTGRESQL — PROJETO BUSFLOW
-- Banco: busflowdb | Engine: PostgreSQL 14+
-- Objetivo: Servir como Fonte da Verdade Operacional para o Grafana e Machine Learning
-- ============================================================================

-- 1. EXTENSÕES ÚTEIS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 2. TABELAS DIMENSÃO (CADASTRO ESTÁTICO GTFS)
-- ============================================================================

-- Cadastro de Linhas
CREATE TABLE IF NOT EXISTS dim_linha (
    linha_codigo VARCHAR(20) NOT NULL,
    sentido INT NOT NULL,              -- 1: Ida (Principal), 2: Volta (Secundário)
    letreiro_origem VARCHAR(100),
    letreiro_destino VARCHAR(100),
    corredor_principal VARCHAR(100),
    PRIMARY KEY (linha_codigo, sentido)
);

-- Cadastro Sequencial de Paradas da Linha (Para desenhar a régua 1 a N no Grafana)
CREATE TABLE IF NOT EXISTS dim_linha_parada (
    linha_codigo VARCHAR(20) NOT NULL,
    sentido INT NOT NULL,
    ponto_parada_seq INT NOT NULL,     -- 1, 2, 3, ..., N
    nome_parada VARCHAR(150),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    PRIMARY KEY (linha_codigo, sentido, ponto_parada_seq),
    FOREIGN KEY (linha_codigo, sentido) REFERENCES dim_linha(linha_codigo, sentido) ON DELETE CASCADE
);

-- ============================================================================
-- 3. TABELAS FATO OPERACIONAIS (INGESTÃO CONTÍNUA)
-- ============================================================================

-- Histórico de Linha (Alimenta os Donuts, Frota x Demanda e Aderência)
CREATE TABLE IF NOT EXISTS fato_linha_operacao (
    id BIGSERIAL PRIMARY KEY,
    timestamp_registro TIMESTAMP WITH TIME ZONE NOT NULL,
    linha_codigo VARCHAR(20) NOT NULL,
    sentido INT NOT NULL,
    frota_ativa_real INT NOT NULL,          -- Demanda Real (Curva Azul no Grafana)
    frota_necessaria_dfi INT NOT NULL,      -- Demanda Ideal (Curva Vermelha no Grafana)
    frota_planejada INT NOT NULL,
    headway_real_min FLOAT NOT NULL,        -- Intervalo Real
    headway_planejado_min FLOAT NOT NULL,    -- Intervalo Previsto
    aderencia_cronograma_pct FLOAT NOT NULL,-- Percentual de Aderência (0 a 100% no Gráfico de Barras)
    status_linha VARCHAR(30) NOT NULL,      -- 'Estabilizado', 'Risco de Gargalo', 'Gargalo'
    iac_clima FLOAT,
    gt_trafego FLOAT,
    go_operacional FLOAT,
    FOREIGN KEY (linha_codigo, sentido) REFERENCES dim_linha(linha_codigo, sentido)
);

CREATE INDEX IF NOT EXISTS idx_linha_op_tempo ON fato_linha_operacao (linha_codigo, timestamp_registro DESC);
CREATE INDEX IF NOT EXISTS idx_linha_op_status ON fato_linha_operacao (status_linha, timestamp_registro DESC);

-- Posição Individual dos Carros (Alimenta a Régua "Circulação da Frota" e Donut por Carro)
CREATE TABLE IF NOT EXISTS fato_veiculo_posicao (
    id BIGSERIAL PRIMARY KEY,
    timestamp_coleta TIMESTAMP WITH TIME ZONE NOT NULL,
    linha_codigo VARCHAR(20) NOT NULL,
    sentido INT NOT NULL,
    prefixo_carro VARCHAR(20) NOT NULL,     -- "Carro 03", "Carro 09"
    ponto_parada_seq INT NOT NULL,          -- Posição na régua de paradas (1 a N)
    latitude FLOAT,
    longitude FLOAT,
    status_carro VARCHAR(30) NOT NULL,      -- 'Estabilizado' (Verde), 'Risco de Gargalo' (Amarelo), 'Gargalo' (Vermelho)
    aderencia_individual FLOAT,
    distancia_proximo_carro_km FLOAT,       -- Para detecção de comboio (bus bunching)
    FOREIGN KEY (linha_codigo, sentido) REFERENCES dim_linha(linha_codigo, sentido)
);

CREATE INDEX IF NOT EXISTS idx_veiculo_linha_recente ON fato_veiculo_posicao (linha_codigo, timestamp_coleta DESC);
CREATE INDEX IF NOT EXISTS idx_veiculo_carro ON fato_veiculo_posicao (prefixo_carro, timestamp_coleta DESC);

-- ============================================================================
-- 4. PREVISÕES DE MACHINE LEARNING & AUDITORIA TEMPORAL
-- ============================================================================

CREATE TABLE IF NOT EXISTS fato_previsao_ml (
    id BIGSERIAL PRIMARY KEY,
    timestamp_previsao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Momento da inferência (ex: 18:00)
    linha_codigo VARCHAR(20) NOT NULL,
    sentido INT NOT NULL,
    horizonte_minutos INT NOT NULL,           -- 10 ou 40 minutos
    timestamp_alvo TIMESTAMP WITH TIME ZONE NOT NULL, -- Quando deve ocorrer (ex: 18:10 ou 18:40)
    
    -- Diagnóstico Preditivo
    status_previsto VARCHAR(30) NOT NULL,     -- 'Estabilizado', 'Risco de Gargalo', 'Gargalo'
    deficit_veiculos INT NOT NULL,            -- "2"
    probabilidade_gargalo FLOAT NOT NULL,     -- 0.0 a 1.0
    
    -- Textos Formatados Diretamente para os Cards do Grafana
    acao_necessaria VARCHAR(255) NOT NULL,    -- "Necessário: Disponibilização de 2 onibus saindo do terminal."
    justificativa VARCHAR(255) NOT NULL,      -- "Justificativa: Atraso devido a gargalo entre as paradas 12 e 17."
    parada_inicio_gargalo INT,                -- 12
    parada_fim_gargalo INT,                   -- 17
    
    alerta_ativo BOOLEAN DEFAULT TRUE,
    versao_modelo VARCHAR(50) DEFAULT 'xgboost-busflow-v1',
    FOREIGN KEY (linha_codigo, sentido) REFERENCES dim_linha(linha_codigo, sentido)
);

CREATE INDEX IF NOT EXISTS idx_ml_alvo ON fato_previsao_ml (linha_codigo, timestamp_alvo DESC);
CREATE INDEX IF NOT EXISTS idx_ml_ativos ON fato_previsao_ml (alerta_ativo, timestamp_previsao DESC);

-- ============================================================================
-- 5. HISTÓRICO DE ALERTAS DISPARADOS (Tela 2 do Figma & Auditoria SNS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fato_alerta (
    id BIGSERIAL PRIMARY KEY,
    timestamp_disparo TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    linha_codigo VARCHAR(20) NOT NULL,
    sentido INT NOT NULL,
    titulo VARCHAR(100) NOT NULL,             -- "Gargalo Crítico"
    status_criticidade VARCHAR(30) NOT NULL,  -- 'Gargalo', 'Risco'
    deficit_sugerido INT NOT NULL,
    mensagem_acao TEXT NOT NULL,
    justificativa TEXT NOT NULL,
    enviado_sns BOOLEAN DEFAULT FALSE,
    sns_message_id VARCHAR(100),
    FOREIGN KEY (linha_codigo, sentido) REFERENCES dim_linha(linha_codigo, sentido)
);

CREATE INDEX IF NOT EXISTS idx_alerta_historico ON fato_alerta (timestamp_disparo DESC);

-- ============================================================================
-- 6. VIEWS OTIMIZADAS PARA O GRAFANA (QUERIES PRONTAS)
-- ============================================================================

-- View 1: Painel Geral - Status Atual por Linha
CREATE OR REPLACE VIEW v_grafana_status_linhas AS
SELECT DISTINCT ON (l.linha_codigo, l.sentido)
    l.linha_codigo,
    l.sentido,
    l.letreiro_origem || ' -> ' || l.letreiro_destino AS itinerario,
    op.status_linha,
    op.frota_ativa_real,
    op.frota_necessaria_dfi,
    op.aderencia_cronograma_pct,
    op.headway_real_min,
    op.headway_planejado_min,
    op.timestamp_registro
FROM dim_linha l
JOIN fato_linha_operacao op ON op.linha_codigo = l.linha_codigo AND op.sentido = l.sentido
ORDER BY l.linha_codigo, l.sentido, op.timestamp_registro DESC;

-- View 2: Painel de Linha - Circulação dos Carros na Régua de Paradas
CREATE OR REPLACE VIEW v_grafana_circulacao_carros AS
SELECT DISTINCT ON (p.linha_codigo, p.sentido, p.prefixo_carro)
    p.linha_codigo,
    p.sentido,
    p.prefixo_carro,
    p.ponto_parada_seq,
    p.status_carro,
    p.aderencia_individual,
    p.timestamp_coleta
FROM fato_veiculo_posicao p
ORDER BY p.linha_codigo, p.sentido, p.prefixo_carro, p.timestamp_coleta DESC;

-- View Dinamica: Tolera qualquer cadencia de coleta 
CREATE OR REPLACE VIEW v_grafana_validacao_ml AS
SELECT 
    ml.id AS predicao_id,
    ml.linha_codigo,
    ml.horizonte_minutos,
    ml.timestamp_previsao,
    ml.timestamp_alvo,
    ml.status_previsto,
    op.status_linha AS status_real_confirmado,
    CASE 
        WHEN ml.status_previsto = op.status_linha THEN 'ACERTO (TP)'
        WHEN ml.status_previsto IN ('Gargalo', 'Risco de Gargalo') AND op.status_linha = 'Estabilizado' THEN 'FALSO ALARME (FP)'
        WHEN ml.status_previsto = 'Estabilizado' AND op.status_linha IN ('Gargalo', 'Risco de Gargalo') THEN 'OMISSAO (FN)'
        ELSE 'OUTRO'
    END AS resultado_validacao,
    ml.deficit_veiculos AS deficit_previsto,
    (op.frota_necessaria_dfi - op.frota_ativa_real) AS deficit_real
FROM fato_previsao_ml ml
JOIN LATERAL (
    -- Busca a coleta real mais proxima do momento em que a previsao venceu
    SELECT o.status_linha, o.frota_necessaria_dfi, o.frota_ativa_real, o.timestamp_registro
    FROM fato_linha_operacao o
    WHERE o.linha_codigo = ml.linha_codigo 
      AND o.sentido = ml.sentido
      AND o.timestamp_registro >= ml.timestamp_alvo - INTERVAL '15 minutes'
    ORDER BY ABS(EXTRACT(EPOCH FROM (o.timestamp_registro - ml.timestamp_alvo))) ASC
    LIMIT 1
) op ON true;