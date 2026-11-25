# Documentação do dataset

O dataset da solução é o arquivo `dados/processado/dataset_integrado.csv`, com uma linha por dia e 59 colunas, de 01/01/2015 a 31/10/2026 (4.322 dias). Ele junta a carga diária do ONS com quatro bases públicas.

| Item | Onde está |
|---|---|
| Dicionário de dados com a origem e o uso de cada coluna | `dados/processado/dicionario_integrado.csv` |
| Versões do dataset, com hash e fontes brutas | `dados/manifesto_dados.json` |
| Qualidade, transformações e downloads da carga do ONS (Etapa 2) | `dados/documentacao/etapa2_ons/` |
| Qualidade, transformações e downloads da integração (Etapa 3) | `dados/documentacao/etapa3_integracao/` |
| Notebooks que geram os dados | `notebooks/Etapa2_Governanca_Qualidade_Dados.ipynb` e `notebooks/Etapa3_Integracao_Bases.ipynb` |

## Origem

| Fonte | Conteúdo | Granularidade | Período no dataset | Endereço |
|---|---|---|---|---|
| ONS, Portal de Dados Abertos | Carga de energia diária do subsistema Sul (MWmed) | diária | 2015 a 10/2026 | <https://dados.ons.org.br/dataset/carga-energia> |
| ANEEL, Dados Abertos | Interrupções nas redes de distribuição da Copel | evento | 2017 a 07/2026 | <https://dadosabertos.aneel.gov.br> |
| ANEEL, Dados Abertos | Indicadores coletivos de continuidade DEC e FEC | mensal por conjunto | 2020 a 07/2026 | <https://dadosabertos.aneel.gov.br> |
| EPE | Consumo mensal de energia por classe e UF | mensal | 2004 a 12/2025 | <https://www.epe.gov.br> |
| Open-Meteo, reanálise ERA5 | Temperatura diária de Curitiba, Florianópolis e Porto Alegre | diária | 2015 a 10/2026 | <https://open-meteo.com> |

Todas as fontes são públicas. O endereço exato e o hash SHA-256 de cada arquivo baixado estão nos registros de download.

## Dicionário de dados

O dicionário descreve as 59 colunas com fonte, significado, uso no modelo e percentual preenchido. As colunas se dividem assim.

| Grupo | Colunas | Uso |
|---|---|---|
| Carga e calendário do ONS (Etapa 2) | 18 | Variável prevista, histórico e calendário. As marcações de qualidade só filtram dias |
| Interrupções da ANEEL | 9 | Marcam dias de grande interrupção. Não entram como variável, porque não são conhecidas antes do dia |
| Temperatura | 7 | Variáveis do modelo |
| Consumo por classe da EPE | 17 | Análise. As versões com 2 meses de atraso podem ser variáveis |
| DEC e FEC | 5 | Validação cruzada |
| Colunas de análise | 3 | Desvio da carga e anomalia de temperatura, só para validação |

A coluna `uso_no_modelo` do dicionário é lida pelo pipeline. Uma coluna que não esteja marcada como preditora é bloqueada antes do treino.

## Qualidade

Principais verificações, com os números dos relatórios. Os números do ONS são da execução de 07/10/2026.

| Fonte | Dimensão | Resultado |
|---|---|---|
| ONS | Completude | 13 valores ausentes em 39.105 registros brutos. No Sul, 1 dia sem valor, imputado por interpolação e marcado |
| ONS | Unicidade | 1 registro repetido em 02/02/2013, tratado |
| ONS | Consistência | Formato de data diferente no arquivo de 2013. Dois degraus de metodologia, em mar/2021 e abr/2023, marcados na coluna `regime_metodologico` |
| ONS | Acurácia | 303 dias atípicos marcados e mantidos. Queda de 6,5% no início da pandemia e de 7,3% no apagão de 15/08/2023, como esperado |
| ANEEL interrupções | Validade e consistência | 5.859.255 interrupções da Copel sem datas inválidas e sem fim anterior ao início |
| ANEEL interrupções | Unicidade | 1,78% de registros repetidos, removidos |
| ANEEL interrupções | Completude | 1 mês sem registros dentro do período coberto (jun/2025), marcado como lacuna |
| ANEEL interrupções | Consistência | Esquema novo em 2026. Consumidores afetados por dia ficam em 52% do nível anterior |
| EPE | Consistência | Planilha em formato diferente do dicionário da própria EPE. Soma das classes confere com o total em todos os 264 meses |
| Open-Meteo | Completude | Nenhum dia sem temperatura nas três capitais |
| Entre fontes | Acurácia | Consumo da EPE equivale a 89,5% da carga do ONS no Sul, coerente com as perdas da rede e com a diferença entre consumo faturado e carga |

Os relatórios completos são `relatorio_qualidade.csv` (ONS) e `relatorio_qualidade_fontes.csv` (integração).

## Transformações

As 13 transformações da carga do ONS e as 10 da integração estão nos arquivos `log_transformacoes.csv` e `log_transformacoes_etapa3.csv`. Cada linha traz o dado original, o problema, a transformação, a justificativa e os registros afetados.

As principais são estas.

- Filtro do subsistema Sul e da janela a partir de 2015.
- Imputação de 1 dia por interpolação, com marcação.
- Marcação de dias atípicos, de eventos conhecidos e do regime de metodologia do ONS.
- Agregação das interrupções por dia e cálculo do CHI (consumidores afetados vezes duração em horas).
- Marcação de grande interrupção quando as afetações do dia chegam a 20% dos consumidores do Paraná.
- Média da temperatura das três capitais e graus-dia de calor e de frio.
- Atraso de 2 meses nas bases mensais para respeitar a data de publicação.

## Versão

A versão em uso é a v1, com hash `4ea3eb86cad81fc8…`. O manifesto guarda o hash, o período, a data de registro, a execução que gerou o arquivo e o hash de cada fonte bruta. O pipeline confere o hash a cada execução e para se o arquivo for diferente.

## Limitações conhecidas

- A documentação de qualidade do ONS neste repositório é da execução de 07/10/2026, com dados até 06/10/2026. O arquivo usado na integração foi gerado por uma execução posterior do mesmo notebook e vai até 31/10/2026. Os relatórios dessa execução não foram guardados (incidente INC-09).
- As interrupções só existem a partir de 2017 e a base tem esquema diferente em 2026.
- A EPE estava com dados só até 12/2025 na data do download.
- A temperatura é de reanálise, e não de estação meteorológica.
