# Matriz de riscos

Probabilidade e impacto vão de 1 (baixo) a 3 (alto). O nível é o produto dos dois. De 1 a 2 o risco é baixo, de 3 a 4 é médio e de 6 a 9 é alto. Cada risco tem um controle já existente na solução e um responsável.

## Dados

| Id | Risco | Causa | P | I | Nível | Controle na solução | Responsável |
|---|---|---|---|---|---|---|---|
| D1 | Fonte muda o formato sem aviso | A ANEEL mudou o esquema das interrupções em 2026 e a EPE publica a planilha fora do próprio dicionário | 3 | 2 | Alto (6) | Padronização de nomes entre esquemas, leitor que não depende da posição das células, validação de entrada e registro em `governanca/incidentes.csv` | TI e Dados |
| D2 | Fonte atrasa ou deixa de publicar | EPE com 10 meses de atraso e ANEEL com 3 na data do monitoramento | 3 | 2 | Alto (6) | Indicador de atualidade das fontes. O modelo em produção depende só de ONS e temperatura | TI e Dados |
| D3 | Download corrompido ou incompleto | Arquivos grandes cortados na transferência | 2 | 2 | Médio (4) | Conferência de integridade, novas tentativas e hash SHA-256 de cada arquivo | TI e Dados |
| D4 | Dado errado entra no modelo | Erro de medição, lacuna lida como zero ou registro duplicado | 2 | 3 | Alto (6) | Validação de faixas, unicidade e continuidade. Meses com lacuna na ANEEL são marcados | TI e Dados |
| D5 | Vazamento de informação do futuro | Uso de coluna que só existe depois do dia previsto | 1 | 3 | Médio (3) | Barreira que consulta o dicionário de dados e bloqueia a variável. Bases mensais entram com 2 meses de atraso | Responsável pelo modelo |
| D6 | Dados revisados pela fonte depois do uso | O ONS revisa a carga após a publicação | 2 | 2 | Médio (4) | Manifesto com hash por versão. Um arquivo diferente interrompe o pipeline até a nova versão ser registrada | TI e Dados |
| D7 | Perda de linhagem | Relatórios da execução que gerou um arquivo não são guardados | 2 | 2 | Médio (4) | Manifesto de dados com fontes brutas e hashes. Incidente INC-09 aberto com a ação definida | Governança |

## Modelo

| Id | Risco | Causa | P | I | Nível | Controle na solução | Responsável |
|---|---|---|---|---|---|---|---|
| M1 | Subestimar a carga em dias críticos | Ondas de calor e semanas após feriados prolongados | 3 | 3 | Alto (9) | Indicador de dias com subestimação acima de 5%, limitação descrita no Model Card e margem de segurança do planejamento | Planejamento energético |
| M2 | Erro maior em operação do que no teste | A temperatura do treino é a observada e em produção é a prevista | 3 | 2 | Alto (6) | Limitação declarada no Model Card. Monitoramento mensal do erro real | Responsável pelo modelo |
| M3 | Degradação com o tempo | Mudança no padrão de consumo ou no clima | 2 | 3 | Alto (6) | Limites de MAPE e de degradação, PSI das variáveis e gatilho de retreino | Responsável pelo modelo |
| M4 | Modelo deixa de superar a regra simples | Períodos de carga estável, como julho e agosto de 2026 | 2 | 2 | Médio (4) | Indicador de ganho sobre a regra simples por mês | Planejamento energético |
| M5 | Erro de desenho não percebido | Variável mal especificada, como o indicador de regime da run R04 | 2 | 3 | Alto (6) | Registro de experimentos com comparação entre runs, viés como métrica e regra de escolha definida antes do teste | Responsável pelo modelo |
| M6 | Resultado não reproduzível | Versões diferentes de bibliotecas ou de dados | 2 | 2 | Médio (4) | Versões fixas em `requirements.txt`, semente fixa e hashes de dados, código e configuração em cada run | TI e Dados |
| M7 | Evento extremo fora do que o modelo conhece | Ciclone, apagão de grande porte ou paralisação | 2 | 3 | Alto (6) | Uso como apoio à decisão, com revisão humana. Eventos conhecidos ficam fora do treino | Planejamento energético |

## Privacidade

| Id | Risco | Causa | P | I | Nível | Controle na solução | Responsável |
|---|---|---|---|---|---|---|---|
| P1 | Tratamento de dado pessoal | Inclusão futura de dados de consumidores ou de medidores individuais | 1 | 3 | Médio (3) | Hoje só há dados públicos e agregados. Qualquer base nova passa pela Governança, com avaliação pela LGPD antes de entrar | Governança |
| P2 | Reidentificação por cruzamento | Conjuntos elétricos pequenos na base de interrupções | 1 | 2 | Baixo (2) | A solução usa só o total diário da distribuidora, sem detalhe por conjunto | Governança |
| P3 | Exposição de dados no repositório | Envio de arquivos internos ou credenciais ao GitHub | 1 | 3 | Médio (3) | O repositório contém só dados públicos. O `.gitignore` deixa de fora os dados brutos e o banco do MLflow | TI e Dados |

## Segurança

| Id | Risco | Causa | P | I | Nível | Controle na solução | Responsável |
|---|---|---|---|---|---|---|---|
| S1 | Troca do modelo sem autorização | Alteração direta do arquivo ou do registro | 1 | 3 | Médio (3) | Promoção só pelo comando com aprovador registrado, histórico em `governanca/historico_modelo.csv` e hash do arquivo do modelo | Governança |
| S2 | Arquivo de modelo malicioso | Arquivos de modelo podem executar código ao serem abertos | 1 | 3 | Médio (3) | O modelo registrado usa formato que só carrega tipos autorizados. Arquivos são conferidos pelo hash | TI e Dados |
| S3 | Dependência comprometida ou alterada | Biblioteca atualizada com falha ou código malicioso | 1 | 3 | Médio (3) | Versões fixas em `requirements.txt` e revisão antes de atualizar | TI e Dados |
| S4 | Adulteração dos dados de entrada | Arquivo alterado entre o download e o treino | 1 | 3 | Médio (3) | Hash SHA-256 de cada download e do dataset integrado, conferido a cada execução | TI e Dados |
| S5 | Perda do histórico de experimentos | O banco do MLflow fica fora do Git | 2 | 2 | Médio (4) | Exportação dos registros para `resultados/experimentos` a cada treino. Em produção o banco fica em servidor com cópia de segurança | TI e Dados |

## Ética

| Id | Risco | Causa | P | I | Nível | Controle na solução | Responsável |
|---|---|---|---|---|---|---|---|
| E1 | Confiança excessiva na previsão | O gestor deixa de questionar o número | 2 | 3 | Alto (6) | Model Card com limitações e usos não recomendados. Decisão final humana | Planejamento energético |
| E2 | Falta de transparência | O gestor não entende por que o modelo previu um valor | 1 | 2 | Baixo (2) | Modelo linear e explicação por grupo de variáveis na seção 8 do notebook da Etapa 3 | Responsável pelo modelo |
| E3 | Erro desigual entre situações | O modelo erra mais em feriados e em alguns meses | 2 | 2 | Médio (4) | Erro por tipo de dia e por estação no monitoramento, com limite próprio | Governança |
| E4 | Impacto na população | Capacidade programada abaixo da necessária afeta o fornecimento | 2 | 3 | Alto (6) | Subestimação tratada como o erro mais grave, com indicador próprio e margem de segurança | Diretoria de operações |
| E5 | Responsabilidade indefinida | Ninguém responde pelo modelo depois da entrega | 1 | 3 | Médio (3) | Responsável nomeado no Model Card e aprovação registrada a cada versão | Governança |

## Resumo

| Nível | Riscos |
|---|---|
| Alto | D1, D2, D4, M1, M2, M3, M5, M7, E1, E4 |
| Médio | D3, D5, D6, D7, M4, M6, P1, P3, S1, S2, S3, S4, S5, E3, E5 |
| Baixo | P2, E2 |

Os riscos altos são revistos todo mês junto com o relatório de monitoramento. Os demais são revistos a cada seis meses com o Model Card.
