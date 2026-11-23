# Resumo da integração (Etapa 3)

Execução em 03/11/2026 21:58 (horário UTC do Colab)

## Fontes
- ONS (Etapa 2) com 4.322 dias, de 01/01/2015 a 31/10/2026.
- ANEEL interrupções da Copel com 5.755.000 interrupções em 3.469 dias, de 01/01/2017 a 31/07/2026.
- ANEEL DEC/FEC da Copel com 79 meses, de 01/2020 a 07/2026.
- EPE consumo por classe no PR, de 01/2004 a 12/2025.
- Open-Meteo com 4.322 dias de temperatura.

## Qualidade e validação
- ONS, Dias sem carga no dataset da Etapa 2, 0 de 4.322 (0,00%).
- ONS, Datas repetidas, 0 de 4.322 (0,00%).
- ANEEL interr., Início não reconhecível como data, 0 de 5.859.255 (0,00%).
- ANEEL interr., Fim não reconhecível como data, 0 de 5.859.255 (0,00%).
- ANEEL interr., Fim anterior ao início, 0 de 5.859.255 (0,00%).
- ANEEL interr., Duração maior que 72 h (mantidas), 11.291 de 5.859.255 (0,19%).
- ANEEL interr., Consumidores afetados ausentes, 0 de 5.859.255 (0,00%).
- ANEEL interr., Consumidores afetados menor ou igual a zero, 0 de 5.859.255 (0,00%).
- ANEEL interr., Início fora do ano do arquivo, 0 de 5.859.255 (0,00%).
- ANEEL interr., Interrupções repetidas (conjunto, início, fim, afetados), 104.255 de 5.859.255 (1,78%).
- ANEEL interr., Dias com expurgo por dia crítico, esquema até 2025 (código numérico), 0 de 3.257 (0,00%). dia crítico é definido por conjunto, não para a distribuidora inteira
- ANEEL interr., Dias com expurgo por dia crítico, esquema 2026 (texto), 193 de 212 (91,04%). dia crítico é definido por conjunto, não para a distribuidora inteira
- ANEEL interr., Meses sem registros da Copel dentro do período coberto, 1 de 115 (0,87%). 06/2025
- ANEEL interr., Comparabilidade entre esquemas (mediana diária de consumidores afetados e duração média), afetados por dia 281.777 até 2025 contra 147.878 em 2026 (52%), duração média de 0,62 h contra 1,09 h. Diferença grande indica mudança na forma de contar e não no serviço
- ANEEL DEC/FEC, Indicadores e períodos presentes (Copel), indicadores FECIPC=12331, DECIPC=12331, DECINE=12331, DEC=12331, FECXP=12331, FEC=12331, FECIND=12331, FECINC=12331 e períodos 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
- ANEEL DEC/FEC, Valores de indicador ausentes (Copel), 0 de 249.073 (0,00%).
- ANEEL DEC/FEC, Valores negativos (Copel), 0 de 249.073 (0,00%).
- EPE, Abas por UF esperadas e não encontradas, 0 de 5 (0,00%).
- EPE, Formato da planilha x dicionário de dados da EPE, planilha em formato largo (uma aba por classe, meses em colunas), diferente do formato longo descrito no dicionário
- EPE, Meses em que a soma das classes difere do total do PR em mais de 1%, 0 de 264 (0,00%).
- EPE, Meses do PR com alguma classe ausente, 0 de 264 (0,00%).
- Open-Meteo, Dias sem temperatura média (curitiba), 0 de 4.322 (0,00%).
- Open-Meteo, Dias sem temperatura média (florianopolis), 0 de 4.322 (0,00%).
- Open-Meteo, Dias sem temperatura média (porto_alegre), 0 de 4.322 (0,00%).
- Validação, Consumo EPE / carga ONS (Sul, mensal), razão média 0,895 em 132 meses e correlação das variações em 12 meses de 0,63
- Validação, DEC oficial x extrato de interrupções (mensal, Spearman), 0,26 com o CHI e 0,50 com os consumidores afetados, em 78 meses. A concordância parcial é esperada porque o DEC oficial exclui os expurgos (grandes temporais) e aqui é média simples entre conjuntos, sem peso de consumidores
- Validação, Carga registrada em dias de grande interrupção (sem feriados), desvio mediano 0,25% nos dias de grande interrupção contra 0,22% nos demais, -3,62% nos 10 dias de maior CHI e Spearman CHI x desvio de 0,10
- Validação, Os 5 dias de maior CHI e o desvio da carga, 30/06/2020 (-8,3%), 23/10/2021 (-0,8%), 23/04/2022 (-4,3%), 22/09/2025 (-2,9%), 14/10/2021 (-4,4%)
- Validação, Carga em dias de grande interrupção, descontando a temperatura, -1,70% nos dias marcados contra -0,02% nos demais (sem descontar, 0,25% contra 0,22%)
- Validação, Regressão do desvio da carga = a + b x anomalia de temperatura + c x log10(CHI), b = 1,09 (erro padrão 0,04) pontos percentuais por °C e c = 0,49 (erro padrão 0,27)

## Cobertura das colunas novas
- n_interrupcoes com 80,3% preenchido (01/01/2017 a 31/07/2026)
- n_interrupcoes_nao_prog com 80,3% preenchido (01/01/2017 a 31/07/2026)
- consumidores_afetados com 80,3% preenchido (01/01/2017 a 31/07/2026)
- chi_total com 80,3% preenchido (01/01/2017 a 31/07/2026)
- chi_nao_prog com 80,3% preenchido (01/01/2017 a 31/07/2026)
- tem_dados_interrupcao com 100,0% preenchido (01/01/2015 a 31/10/2026)
- temp_media_sul com 100,0% preenchido (01/01/2015 a 31/10/2026)
- temp_max_sul com 100,0% preenchido (01/01/2015 a 31/10/2026)
- temp_min_sul com 100,0% preenchido (01/01/2015 a 31/10/2026)
- temp_media_curitiba com 100,0% preenchido (01/01/2015 a 31/10/2026)
- graus_dia_calor com 100,0% preenchido (01/01/2015 a 31/10/2026)
- graus_dia_frio com 100,0% preenchido (01/01/2015 a 31/10/2026)
- consumo_pr_total_mwh_lag2m com 94,3% preenchido (01/01/2015 a 28/02/2026)
- consumidores_pr_lag2m com 94,3% preenchido (01/01/2015 a 28/02/2026)
- part_residencial_pr_lag2m com 94,3% preenchido (01/01/2015 a 28/02/2026)
- part_industrial_pr_lag2m com 94,3% preenchido (01/01/2015 a 28/02/2026)
- part_comercial_pr_lag2m com 94,3% preenchido (01/01/2015 a 28/02/2026)
- part_outros_pr_lag2m com 94,3% preenchido (01/01/2015 a 28/02/2026)
- dec_medio_conjuntos_lag2m com 55,6% preenchido (01/03/2020 a 30/09/2026)
- fec_medio_conjuntos_lag2m com 55,6% preenchido (01/03/2020 a 30/09/2026)
- consumo_pr_total_mwh com 93,0% preenchido (01/01/2015 a 31/12/2025)
- consumo_pr_residencial_mwh com 93,0% preenchido (01/01/2015 a 31/12/2025)
- consumo_pr_industrial_mwh com 93,0% preenchido (01/01/2015 a 31/12/2025)
- consumo_pr_comercial_mwh com 93,0% preenchido (01/01/2015 a 31/12/2025)
- consumo_pr_outros_mwh com 93,0% preenchido (01/01/2015 a 31/12/2025)
- consumidores_pr com 93,0% preenchido (01/01/2015 a 31/12/2025)
- part_residencial_pr com 93,0% preenchido (01/01/2015 a 31/12/2025)
- part_industrial_pr com 93,0% preenchido (01/01/2015 a 31/12/2025)
- part_comercial_pr com 93,0% preenchido (01/01/2015 a 31/12/2025)
- part_outros_pr com 93,0% preenchido (01/01/2015 a 31/12/2025)
- consumo_sul_epe_mwh com 93,0% preenchido (01/01/2015 a 31/12/2025)
- dec_medio_conjuntos com 55,6% preenchido (01/01/2020 a 31/07/2026)
- fec_medio_conjuntos com 55,6% preenchido (01/01/2020 a 31/07/2026)
- n_conjuntos com 55,6% preenchido (01/01/2020 a 31/07/2026)
- flag_chi_p99 com 100,0% preenchido (01/01/2015 a 31/10/2026)
- fracao_afetados com 80,3% preenchido (01/01/2017 a 31/07/2026)
- flag_grande_interrupcao com 100,0% preenchido (01/01/2015 a 31/10/2026)

## Carga x temperatura (dias úteis)
- Correlação por estação, inverno -0,01, outono 0,39, primavera 0,41, verao 0,35

## Dataset integrado
- 4.322 dias x 59 colunas e 10 transformações registradas.