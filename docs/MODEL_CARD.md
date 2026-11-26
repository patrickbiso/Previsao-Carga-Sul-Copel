# Model Card do modelo previsao-carga-sul

| Item | Descrição |
|---|---|
| Nome e versão | previsao-carga-sul, versão 1 |
| Situação | Em produção desde 16/11/2026, revalidado na mesma data com os dados de 2026 |
| Tipo de modelo | Regressão linear múltipla com 32 variáveis |
| Responsável | [Nome 1] e [Nome 2], grupo do projeto na disciplina Governança de TI e de Dados (UEL) |
| Última revisão deste documento | 16/11/2026 |
| Próxima revisão | Até maio de 2027, ou antes se o monitoramento pedir retreino |

## Objetivo

Prever a carga diária de energia do subsistema Sul, em MWmed, com 7 dias de antecedência. A previsão apoia a gerência de planejamento energético da Copel na programação semanal de capacidade, de contratação e de equipes.

O modelo é um apoio à decisão. A decisão continua com o planejamento, que pode ajustar a previsão quando souber de algo que o modelo não vê.

## Dados utilizados

| Fonte | Uso no modelo | Período |
|---|---|---|
| ONS, carga diária do subsistema Sul | Variável prevista e histórico de 7, 14, 21 e 364 dias antes | 2015 a 2026 |
| Open-Meteo (reanálise ERA5), temperatura de Curitiba, Florianópolis e Porto Alegre | Variáveis de temperatura | 2015 a 2026 |
| Calendário e feriados nacionais | Dia da semana, época do ano, feriado, véspera e dia seguinte | 2015 a 2026 |
| ANEEL, interrupções da Copel | Só para tirar do treino os dias de grande interrupção | 2017 a 2026 |

O treino usou 2.703 dias entre 01/01/2017 e 31/12/2024. Ficaram fora 42 dias de transição de metodologia do ONS, 97 dias de grande interrupção e 80 dias de eventos conhecidos, como a greve de 2018 e o início da pandemia.

Todos os dados são públicos e agregados. Não há dado pessoal nem dado de consumidor individual. A versão dos dados é a v1, com hash `4ea3eb86cad8`, descrita em `docs/DATASET.md`.

## População e contexto

- O modelo representa a carga agregada do subsistema Sul do Sistema Interligado Nacional, que reúne Paraná, Santa Catarina e Rio Grande do Sul.
- A Copel atende o Paraná. A carga do Sul é usada como aproximação da demanda da região em que a Copel opera, porque é o dado público diário disponível.
- A unidade é o dia. O modelo não prevê a curva horária nem o pico dentro do dia.
- O horizonte é de 7 dias. Para cada dia previsto, o modelo usa só o que se sabe 7 dias antes, mais a temperatura do próprio dia.

## Como o modelo funciona

O modelo prevê a razão entre a carga do dia e a carga média da semana mais recente conhecida, e depois multiplica pela média dessa semana. Assim ele acompanha o crescimento do consumo sem precisar ser treinado de novo a cada mês.

As 32 variáveis formam três grupos.

- Calendário, com dia da semana, época do ano, feriado, véspera, dia seguinte e fim de ano.
- Histórico relativo da carga, com 7, 14, 21 e 364 dias antes.
- Temperatura, com média, máxima e mínima, graus acima de 20 °C e abaixo de 15 °C e a diferença para a semana de referência.

## Métricas

| Métrica | Teste 2025 | Monitoramento jan a out de 2026 | Regra simples no teste 2025 |
|---|---|---|---|
| MAE (MWmed) | 555 | 523 | 879 |
| MAPE (%) | 4,06 | 3,73 | 6,37 |
| RMSE (MWmed) | 718 | não calculado | não calculado |
| Viés (MWmed) | +123 | varia de -653 a +510 por mês | não calculado |
| MAE nos dias de pico (MWmed) | 497 | não calculado | 1.068 |

O MAE é a métrica principal porque mostra o erro na unidade do planejamento. O teste de 2025 e os meses de 2026 não participaram do treino nem da escolha do modelo. A regra simples repete a carga do mesmo dia da semana anterior.

Erro por segmento em 2026.

| Segmento | Dias | MAPE (%) |
|---|---|---|
| Dias úteis | 208 | 3,59 |
| Fins de semana | 87 | 3,85 |
| Feriados | 9 | 5,93 |
| Verão | 78 | 4,20 |
| Outono | 93 | 4,16 |
| Inverno | 93 | 3,54 |
| Primavera | 40 | 2,28 |

## Limitações

- A temperatura usada no treino e na avaliação é a observada. Em produção ela vem da previsão do tempo para 7 dias, que tem erro. O erro real em operação tende a ser maior que o medido aqui.
- Na semana seguinte a um feriado prolongado ou ao recesso de fim de ano a previsão erra mais, porque a semana de referência está baixa. Em 8 e 9 de janeiro de 2026 o modelo subestimou a carga em cerca de 2.400 MWmed.
- O erro em feriados é cerca de 1,7 vez o erro em dias úteis.
- Em julho e agosto de 2026 o modelo ficou no mesmo nível da regra simples. No inverno a carga varia pouco de uma semana para a outra e o ganho do modelo diminui.
- O modelo não antecipa eventos extremos, como ciclones, apagões de grande porte ou paralisações.
- Mudanças de metodologia do ONS alteram o nível da série. O modelo erra mais nas semanas seguintes a uma mudança desse tipo.
- A carga do Sul não é a carga da Copel. Decisões sobre uma área específica do Paraná precisam de dados dessa área.

## Usos recomendados

- Apoio à programação semanal de capacidade, de contratação de energia e de equipes de operação.
- Sinal de alerta para semanas com previsão de carga alta, sempre junto com a análise do planejamento.
- Linha de base para comparar modelos novos.

## Usos não recomendados

- Operação em tempo real ou despacho, que precisam de previsão horária.
- Decisões automáticas sem revisão humana.
- Previsão para horizontes acima de 7 dias, para os quais o modelo não foi avaliado.
- Faturamento, tarifas ou qualquer decisão sobre consumidores individuais.
- Planejamento de investimento de longo prazo, que depende de cenários econômicos fora do modelo.

## Riscos

| Risco | Efeito | Controle |
|---|---|---|
| Subestimar a carga em dias de calor ou após feriados | Capacidade programada abaixo da necessária, com risco de sobrecarga | Indicador de dias com subestimação acima de 5% e margem de segurança do planejamento |
| Queda de qualidade ou atraso de uma fonte de dados | Previsão errada ou ausente | Validação de entrada e monitoramento de dados e de atualidade das fontes |
| Modelo desatualizado | Erro crescente sem que ninguém perceba | Monitoramento mensal do erro e gatilho de retreino |
| Uso fora do contexto para o qual foi avaliado | Decisão com base em previsão sem validade | Usos descritos neste documento e revisão humana obrigatória |

A lista completa está em `docs/MATRIZ_RISCOS.md`.

## Aspectos éticos

- O modelo não usa dados pessoais e não toma decisões sobre pessoas.
- Um erro grande pode afetar a continuidade do fornecimento para a população. Por isso a subestimação é acompanhada como indicador próprio e a decisão final é humana.
- A previsão é explicável. A seção 8 do notebook da Etapa 3 mostra quanto o calendário, o histórico e a temperatura pesam em cada previsão.
- O erro é medido por tipo de dia e por estação para verificar se o modelo erra de forma desigual. As limitações conhecidas estão descritas acima, sem omitir os casos em que o modelo vai mal.

## Rastreabilidade

| Item | Versão |
|---|---|
| Dados | v1, hash `4ea3eb86cad8` |
| Código | hash de `src` `dc124bad9218` |
| Configuração | hash de `config.yaml` `183fdc4dc532` |
| Experimento de origem | run R12 do plano de 16 runs, registro no MLflow |
| Arquivo do modelo | `resultados/modelo/modelo_v1.joblib`, hash `ffac524933a6` |
| Histórico de aprovação | `governanca/historico_modelo.csv` |
