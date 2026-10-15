-- =============================================================================
-- test_db.sql — Validação completa do schema BusFlow no RDS
-- Executado via: psql -f test_db.sql
-- =============================================================================

\echo ''
\echo '=== [1] ROW COUNTS ==='
SELECT
  'dim_linha'            AS tabela, COUNT(*)::int AS total FROM dim_linha
UNION ALL SELECT 'dim_linha_parada',        COUNT(*)::int FROM dim_linha_parada
UNION ALL SELECT 'fato_linha_operacao',     COUNT(*)::int FROM fato_linha_operacao
UNION ALL SELECT 'fato_veiculo_posicao',    COUNT(*)::int FROM fato_veiculo_posicao
UNION ALL SELECT 'fato_previsao_ml',        COUNT(*)::int FROM fato_previsao_ml
UNION ALL SELECT 'fato_alerta',             COUNT(*)::int FROM fato_alerta
UNION ALL SELECT 'fato_auditoria_pipeline', COUNT(*)::int FROM fato_auditoria_pipeline
ORDER BY tabela;

\echo ''
\echo '=== [2] TABELAS E VIEWS ==='
SELECT tablename AS objeto, 'TABLE' AS tipo
FROM pg_tables WHERE schemaname = 'public'
UNION ALL
SELECT viewname, 'VIEW'
FROM pg_views  WHERE schemaname = 'public'
ORDER BY tipo, objeto;

\echo ''
\echo '=== [3] INDICES ==='
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

\echo ''
\echo '=== [4] FOREIGN KEYS ==='
SELECT
    tc.table_name    AS tabela,
    kcu.column_name  AS coluna,
    ccu.table_name   AS ref_tabela
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON kcu.constraint_name = tc.constraint_name
  AND kcu.table_schema   = tc.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema    = 'public'
ORDER BY tc.table_name;

\echo ''
\echo '=== [5] ULTIMAS 5 AUDITORIAS ==='
SELECT componente, status_execucao, cumpre_sla,
       ROUND(duracao_segundos::numeric, 2) AS dur_s,
       linhas_processadas,
       timestamp_inicio
FROM fato_auditoria_pipeline
ORDER BY timestamp_inicio DESC
LIMIT 5;

\echo ''
\echo '=== [6] FRESCOR DOS DADOS (5 linhas mais antigas) ==='
SELECT linha_codigo, sentido, atraso_minutos, status_frescor_sla
FROM v_auditoria_frescor_dados
ORDER BY atraso_minutos DESC NULLS LAST
LIMIT 5;

\echo ''
\echo '=== VALIDACAO CONCLUIDA ==='
