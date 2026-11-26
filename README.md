# Previsão da carga diária do subsistema Sul

Projeto final da disciplina Governança de TI e de Dados (UEL, Ciência de Dados e Inteligência Artificial). A solução prevê a carga diária de energia do subsistema Sul, em MWmed, com 7 dias de antecedência, para apoiar o planejamento de capacidade da Copel. Este repositório reúne o código, os dados versionados, o registro dos experimentos e os documentos de governança.

Integrantes: Patrick Mendes Bisolato, Heitor Oliveira Nunes.

## Resultado em uma tabela

| Item | Valor |
|---|---|
| Modelo em produção | Regressão linear múltipla com alvo relativo, versão 1 |
| Erro no teste de 2025 | MAE de 555 MWmed e MAPE de 4,06% |
| Regra simples no mesmo teste | MAE de 879 MWmed e MAPE de 6,37% |
| Erro no monitoramento de jan a out de 2026 | MAE de 523 MWmed e MAPE de 3,73% |
| Experimentos registrados | 16 runs e o modelo final, no MLflow |

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `config/` | `config.yaml`, com todos os parâmetros, o plano de experimentos e os limites do monitoramento |
| `src/` | Código do pipeline. Treino, promoção, previsão, monitoramento e versões |
| `dados/` | Dataset integrado, dicionário, manifesto de versões e documentação de qualidade |
| `notebooks/` | Notebooks das Etapas 2 e 3 e o notebook que roda a solução no Colab |
| `docs/` | Model Card, plano de monitoramento, matriz de riscos, documentação do dataset, versionamento e relatório executivo |
| `governanca/` | Histórico de aprovação do modelo e registro de incidentes |
| `resultados/` | Registro dos experimentos, ficha e arquivo do modelo e relatório de monitoramento da última execução |

## Entregas da Etapa 4

| Entrega | Onde está |
|---|---|
| Repositório da solução | Este repositório |
| Dataset documentado | [docs/DATASET.md](docs/DATASET.md) e a pasta `dados/` |
| Registro dos experimentos | MLflow, com exportação em [resultados/experimentos](resultados/experimentos) e telas em [docs/evidencias](docs/evidencias) |
| Model Card | [docs/MODEL_CARD.md](docs/MODEL_CARD.md) |
| Plano de monitoramento | [docs/PLANO_MONITORAMENTO.md](docs/PLANO_MONITORAMENTO.md) e [relatório da simulação](resultados/monitoramento/relatorio_monitoramento.md) |
| Matriz de riscos | [docs/MATRIZ_RISCOS.md](docs/MATRIZ_RISCOS.md) |
| Relatório executivo | [docs/Relatorio_Executivo_Etapa4.docx](docs/Relatorio_Executivo_Etapa4.docx) |

## Como reproduzir

### No Google Colab

Abra `notebooks/Etapa4_Executar_no_Colab.ipynb`, preencha `REPO_URL` com o endereço deste repositório e use Executar tudo. O notebook treina, aprova, monitora e baixa os resultados. Leva cerca de 4 minutos.

### No computador

Requer Python 3.13.

```
pip install -r requirements.txt
python -m src.versoes
python -m src.treinar
python -m src.promover --versao candidato --aprovado-por "Seu nome" --motivo "Primeira versão"
python -m src.monitorar
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

O último comando abre a interface do MLflow em <http://127.0.0.1:5000>, com os experimentos, os modelos registrados e o monitoramento.

| Comando | O que faz |
|---|---|
| `python -m src.versoes` | Mostra as versões de código, dados, configuração e modelo |
| `python -m src.treinar` | Valida os dados, roda as 16 runs, escolhe pela regra de validação e registra o modelo final como candidato |
| `python -m src.promover` | Coloca um candidato em produção ou revalida a versão atual, com aprovador registrado |
| `python -m src.prever --inicio AAAA-MM-DD --fim AAAA-MM-DD` | Gera previsões com o modelo em produção |
| `python -m src.monitorar` | Aplica o plano de monitoramento aos dados de 2026 e gera o relatório |

Os dados brutos não precisam ser baixados de novo. Para refazer o dataset desde as fontes, rode os notebooks das Etapas 2 e 3, nessa ordem, e registre a nova versão como descrito em [docs/VERSIONAMENTO.md](docs/VERSIONAMENTO.md).

## Pipeline

| Etapa | Onde está no código |
|---|---|
| Dados brutos com hash | notebooks das Etapas 2 e 3, `dados/manifesto_dados.json` |
| Validação e barreira contra vazamento | `src/dados.py` |
| Preparação e divisão no tempo | `src/dados.py`, janelas em `config/config.yaml` |
| Variáveis | `src/variaveis.py` |
| Treinamento e escolha | `src/pipeline.py`, `src/treinar.py` |
| Registro no MLflow | `src/rastreio.py`, `src/treinar.py` |
| Aprovação e ciclo de vida | `src/promover.py` |
| Monitoramento | `src/monitorar.py` |

## Versionamento

Código no Git, dados por manifesto com hash, modelo no registro do MLflow e configuração em um único arquivo. Cada run grava as quatro versões. Os detalhes estão em [docs/VERSIONAMENTO.md](docs/VERSIONAMENTO.md).

O resultado guardado neste repositório foi gerado com os dados `v1@4ea3eb86cad8`, o código `dc124bad9218` e a configuração `183fdc4dc532`.

## Limitações

A temperatura usada é a observada, e em produção seria a prevista. A carga do Sul é uma aproximação da área da Copel. As demais limitações estão no [Model Card](docs/MODEL_CARD.md).
