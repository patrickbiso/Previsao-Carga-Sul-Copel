# Resumo dos resultados — Etapa 2

Execução: 08/10/2026 02:43

## Inventário
- Base bruta: **39.105 registros** em 27 arquivos anuais (01/01/2000 a 06/10/2026), 4 subsistemas.
- Subsistema Sul: 9.777 registros brutos.

## Qualidade (evidências)
- **Completude** — Valores ausentes em 'id_subsistema': 0 de 39.105 (0,00%).
- **Completude** — Valores ausentes em 'nom_subsistema': 0 de 39.105 (0,00%).
- **Completude** — Valores ausentes em 'din_instante': 0 de 39.105 (0,00%).
- **Completude** — Valores ausentes em 'val_cargaenergiamwmed': 13 de 39.105 (0,03%).
- **Completude** — Dias sem registro no calendário — subsistema N: 0 de 9.776 (0,00%). 01/01/2000–06/10/2026
- **Completude** — Dias sem registro no calendário — subsistema NE: 0 de 9.776 (0,00%). 01/01/2000–06/10/2026
- **Completude** — Dias sem registro no calendário — subsistema S: 0 de 9.776 (0,00%). 01/01/2000–06/10/2026
- **Completude** — Dias sem registro no calendário — subsistema SE: 0 de 9.776 (0,00%). 01/01/2000–06/10/2026
- **Validade** — Carga não numérica (texto não convertível): 0 de 39.092 (0,00%).
- **Validade** — Carga menor ou igual a zero: 0 de 39.092 (0,00%). fisicamente impossível
- **Validade** — Data não reconhecível: 0 de 39.105 (0,00%).
- **Validade** — Data no futuro (após a data de execução): 0 de 39.105 (0,00%).
- **Validade** — Código de subsistema fora de {N, NE, S, SE}: 0 de 39.105 (0,00%). códigos encontrados: N, NE, S, SE
- **Unicidade** — Registros duplicados idênticos (subsistema + data + valor): 0 de 39.105 (0,00%).
- **Unicidade** — Chaves (subsistema + data) com valores diferentes: 0 de 39.104 (0,00%). duplicata conflitante
- **Unicidade** — Chaves repetidas em que uma linha tem valor e outra está vazia: 1 de 39.104 (0,00%). S em 02/02/2013
- **Consistência** — Arquivos anuais com colunas diferentes do padrão: 0 de 27 (0,00%).
- **Consistência** — Arquivos anuais com formato de data diferente do padrão: 1 de 27 (3,70%). padrão '%Y-%m-%d'; diferente em: 2013 ('%Y-%m-%d %H:%M:%S')
- **Consistência** — Códigos de subsistema com mais de um nome: 0 de 4 (0,00%). N=Norte; NE=Nordeste; S=Sul; SE=Sudeste/Centro-Oeste
- **Consistência** — Registros com data fora do ano do arquivo de origem: 0 de 39.105 (0,00%).
- **Consistência** — Degrau na série — Inclusão de usinas não despachadas (mar/2021): variação de +2,11% entre as 4 semanas antes e depois do marco, contra -4,42% nas mesmas datas de 2019, 2018, 2017: efeito estimado de +6,52 p.p.
- **Consistência** — Degrau na série — Inclusão de MMGD (abr/2023): variação de +2,59% entre as 4 semanas antes e depois do marco, contra -3,37% nas mesmas datas de 2022, 2021, 2019: efeito estimado de +5,96 p.p.
- **Atualidade** — Defasagem do último dado — subsistema N: último dia: 06/10/2026; defasagem de 2 dia(s).
- **Atualidade** — Defasagem do último dado — subsistema NE: último dia: 06/10/2026; defasagem de 2 dia(s).
- **Atualidade** — Defasagem do último dado — subsistema S: último dia: 06/10/2026; defasagem de 2 dia(s).
- **Atualidade** — Defasagem do último dado — subsistema SE: último dia: 06/10/2026; defasagem de 2 dia(s).
- **Acurácia** — Dias atípicos (|z robusto| > 3.5) — mantidos e sinalizados: 834 de 9.773 (8,53%).
- **Acurácia** — Evento conhecido: início da pandemia (23/03–31/05/2020 vs 2019): carga média -6,51% em relação às mesmas datas de 2019 (queda esperada).
- **Acurácia** — Evento conhecido: apagão de 15/08/2023 (vs mesmo dia da semana nas 4 semanas anteriores): carga do dia -7,32% em relação à mediana do mesmo dia da semana nas 4 semanas anteriores.
- **Acurácia** — Dias atípicos com causa conhecida (feriado, fim de ano ou evento): 439 de 834 (52,64%). outros (ex.: ondas de calor/frio, pontes de feriado): 395; feriado nacional / Carnaval: 255; período de Natal e Ano-Novo (20/12–07/01): 176; evento conhecido: 8

## Tratamento
- 13 transformações registradas (ver `log_transformacoes.csv`).
- Dataset final: **4.297 dias** (2015-01-01 a 2026-10-06), 18 colunas.
- Dias sem valor válido na origem (ausentes, nulos ou inválidos): 1; imputados por interpolação: 1; sem valor após tratamento: 0.
- Dias sinalizados como atípicos: 303 (7,05%), mantidos na base.

## Rastreabilidade
- Hash SHA-256 e data de obtenção de cada arquivo em `registro_downloads.csv`.
- Ambiente: Python 3.13.16, pandas 2.2.3, numpy 2.1.3.
- Parâmetros: janela a partir de 2015-01-01; lacuna máxima imputável 3 dias; limiar de outlier |z| > 3.5.