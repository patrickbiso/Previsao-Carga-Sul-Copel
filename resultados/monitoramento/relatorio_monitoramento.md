# Relatório de monitoramento

Execução 20261116_200319. Modelo previsao-carga-sul versão 1, treinado com 2017-01-01 a 2024-12-31. Dados v1@4ea3eb86cad8.

A simulação trata cada mês de 2026-01 a 2026-10 como um lote novo de dados que chega depois do treino. O modelo em produção fica congelado e prevê cada dia com 7 dias de antecedência. Os limites vêm de `config/config.yaml`.

## Resumo

- No período o modelo teve MAE de 523 MWmed, contra 864 da regra simples. No teste de 2025 o MAE foi de 555 MWmed.
- Foram avaliados 120 pares de indicador e mês. 11 ficaram em alerta e 13 em atenção.
- Decisão do último mês, 2026-10, manter e acompanhar.

## Situação por mês

| Mês | MAE (MWmed) | MAPE (%) | Viés (MWmed) | Ganho sobre a regra simples (%) | Dias com subestimação acima de 5% (%) | Situação | Decisão |
|---|---|---|---|---|---|---|---|
| 2026-01 | 834 | 5,46 | -653 | 53,0 | 38,7 | ALERTA | investigar o modelo |
| 2026-02 | 599 | 3,75 | 510 | 28,4 | 0,0 | ALERTA | investigar o modelo |
| 2026-03 | 487 | 2,98 | 253 | 54,9 | 6,5 | ATENÇÃO | manter e acompanhar |
| 2026-04 | 398 | 2,75 | 151 | 61,3 | 0,0 | ATENÇÃO | manter e acompanhar |
| 2026-05 | 711 | 5,73 | 161 | 24,3 | 19,4 | ALERTA | investigar o modelo, drift com piora do erro |
| 2026-06 | 524 | 3,90 | -230 | 18,2 | 23,3 | ALERTA | investigar o modelo |
| 2026-07 | 406 | 3,10 | 349 | 2,8 | 0,0 | ALERTA | investigar o modelo |
| 2026-08 | 463 | 3,46 | -172 | -16,4 | 19,4 | ALERTA | investigar o modelo |
| 2026-09 | 548 | 4,23 | 101 | 42,9 | 10,0 | OK | manter |
| 2026-10 | 265 | 1,97 | -85 | 52,9 | 3,2 | ATENÇÃO | manter e acompanhar |

## Indicadores fora do limite

| Mês | Dimensão | Indicador | Valor | Atenção | Alerta | Situação | Ação do plano |
|---|---|---|---|---|---|---|---|
| 2026-01 | Modelo | MAPE (%) | 5,46 | 5 | 6,40 | ATENÇÃO | investigar os dias de maior erro e avaliar retreino |
| 2026-01 | Modelo | MAE do mês sobre o MAE do teste | 1,50 | 1,25 | 1,50 | ALERTA | comparar com o modelo retreinado e avaliar troca |
| 2026-01 | Modelo | Viés (% da carga) | 4,33 | 1,50 | 3 | ALERTA | verificar erro sistemático e avaliar retreino |
| 2026-01 | Negócio | Dias com subestimação acima de 5% (%) | 38,71 | 10 | 20 | ALERTA | avisar o planejamento e usar margem de segurança |
| 2026-01 | Dados | PSI da carga relativa de 7 dias antes | 0,13 | 0,10 | 0,25 | ATENÇÃO | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-02 | Modelo | Viés (% da carga) | 3,17 | 1,50 | 3 | ALERTA | verificar erro sistemático e avaliar retreino |
| 2026-03 | Modelo | Viés (% da carga) | 1,57 | 1,50 | 3 | ATENÇÃO | verificar erro sistemático e avaliar retreino |
| 2026-04 | Dados | PSI da temperatura média | 0,11 | 0,10 | 0,25 | ATENÇÃO | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-05 | Modelo | MAPE (%) | 5,73 | 5 | 6,40 | ATENÇÃO | investigar os dias de maior erro e avaliar retreino |
| 2026-05 | Modelo | MAE do mês sobre o MAE do teste | 1,28 | 1,25 | 1,50 | ATENÇÃO | comparar com o modelo retreinado e avaliar troca |
| 2026-05 | Negócio | Dias com subestimação acima de 5% (%) | 19,35 | 10 | 20 | ATENÇÃO | avisar o planejamento e usar margem de segurança |
| 2026-05 | Dados | PSI da temperatura média | 0,33 | 0,10 | 0,25 | ALERTA | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-05 | Dados | PSI da carga relativa de 7 dias antes | 0,20 | 0,10 | 0,25 | ATENÇÃO | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-06 | Modelo | Viés (% da carga) | 1,73 | 1,50 | 3 | ATENÇÃO | verificar erro sistemático e avaliar retreino |
| 2026-06 | Negócio | Ganho sobre a regra simples (%) | 18,19 | 20 | 10 | ATENÇÃO | rever se o modelo ainda se justifica frente à regra simples |
| 2026-06 | Negócio | Dias com subestimação acima de 5% (%) | 23,33 | 10 | 20 | ALERTA | avisar o planejamento e usar margem de segurança |
| 2026-06 | Dados | PSI da temperatura média | 0,41 | 0,10 | 0,25 | ALERTA | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-06 | Dados | PSI da diferença de temperatura | 0,25 | 0,10 | 0,25 | ALERTA | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-07 | Modelo | Viés (% da carga) | 2,63 | 1,50 | 3 | ATENÇÃO | verificar erro sistemático e avaliar retreino |
| 2026-07 | Negócio | Ganho sobre a regra simples (%) | 2,81 | 20 | 10 | ALERTA | rever se o modelo ainda se justifica frente à regra simples |
| 2026-07 | Dados | PSI da temperatura média | 0,40 | 0,10 | 0,25 | ALERTA | conferir se o erro subiu no mesmo período e avaliar retreino |
| 2026-08 | Negócio | Ganho sobre a regra simples (%) | -16,45 | 20 | 10 | ALERTA | rever se o modelo ainda se justifica frente à regra simples |
| 2026-08 | Negócio | Dias com subestimação acima de 5% (%) | 19,35 | 10 | 20 | ATENÇÃO | avisar o planejamento e usar margem de segurança |
| 2026-10 | Dados | PSI da temperatura média | 0,12 | 0,10 | 0,25 | ATENÇÃO | conferir se o erro subiu no mesmo período e avaliar retreino |

## Retreino

| Modelo | MAE no período (MWmed) | MAPE (%) |
|---|---|---|
| Em produção (treino até 2024) | 523 | 3,73 |
| Candidato (treino até 2025) | 521 | 3,72 |
| Retreino mensal | 524 | 3,73 |
| Regra simples | 864 | 6,11 |

O candidato treinado com um ano a mais de dados muda o MAE em -0,3% em relação ao modelo em produção. O retreino mensal muda em 0,1%.

Recomendação. A diferença fica dentro da tolerância de 1%, então a versão em produção é mantida e a revalidação é registrada no histórico do modelo.

## Mudança nos dados

O PSI compara a distribuição dos últimos 3 meses com a dos mesmos meses no período de treino. O da carga em MWmed foi de 1,01 a 2,31, muito acima do limite, porque o consumo cresce todo ano. Esse indicador fica só como contexto. O modelo usa a carga em forma relativa, e o PSI dessa variável ficou entre 0,02 e 0,20.

## Atualidade das fontes

| Fonte | Último dado | Atraso (meses) | Uso | Situação |
|---|---|---|---|---|
| ONS, carga diária | 2026-10-31 | 0 | alvo e histórico do modelo | OK |
| Open-Meteo, temperatura | 2026-10-31 | 0 | variável do modelo | OK |
| ANEEL, interrupções | 2026-07-31 | 3 | escolha dos dias de treino | ATENÇÃO |
| ANEEL, DEC e FEC | 2026-07-31 | 3 | validação | ATENÇÃO |
| EPE, consumo por classe | 2025-12-31 | 10 | análise, fora do modelo em produção | ALERTA |

## Governança

| Indicador | Valor | Atenção | Alerta | Situação | Ação do plano |
|---|---|---|---|---|---|
| MAPE de feriados sobre o de dias úteis | 1,65 | 2 | 3 | OK |  |
| Meses desde o treino ou a última revalidação | 22 | 12 | 18 | ALERTA | treinar candidato com os dados mais recentes e comparar |
| Dias sem revisar o Model Card | 0 | 180 | 365 | OK |  |
| Incidentes abertos | 2 | 1 | 3 | ATENÇÃO | tratar os incidentes abertos e registrar a solução |

Erro por segmento no período, para verificar se o modelo erra de forma desigual.

| Segmento | Dias | MAPE (%) |
|---|---|---|
| dias úteis | 208 | 3,59 |
| fins de semana | 87 | 3,85 |
| feriados | 9 | 5,93 |
| inverno | 93 | 3,54 |
| outono | 93 | 4,16 |
| primavera | 40 | 2,28 |
| verao | 78 | 4,20 |

## Arquivos

- `indicadores_mensais.csv` tem todos os indicadores por mês.
- `avaliacao_limites.csv` tem a situação de cada indicador em cada mês e a ação prevista.
- `decisoes.csv` tem a decisão de cada mês.
- `comparacao_retreino.csv` tem o MAE mensal de cada alternativa de retreino.
- As figuras 1 a 4 mostram o erro mensal, a série prevista, o drift e o efeito do retreino.
