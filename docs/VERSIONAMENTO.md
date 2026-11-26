# Versionamento

A solução versiona quatro coisas. Cada run registrada no MLflow carrega a versão das quatro, então é possível saber com que dados, código e configuração cada modelo foi produzido.

| O que | Como é versionado | Onde ver |
|---|---|---|
| Código | Git, com um commit por mudança e uma tag por entrega. Cada run grava o commit e o hash dos arquivos de `src` | `git log`, etiqueta `versao_codigo` nas runs |
| Dados | Manifesto com hash SHA-256, período e fontes brutas de cada versão. O dataset integrado fica no repositório. Os arquivos brutos grandes ficam fora e são identificados pelo hash | `dados/manifesto_dados.json`, etiqueta `versao_dados` |
| Modelo | Registro de modelos do MLflow, com versão numerada, apelidos `candidato`, `producao` e `anterior`, e aprovação registrada | Interface do MLflow, `governanca/historico_modelo.csv` |
| Configuração | Arquivo único `config/config.yaml` no Git. Cada run grava o hash do arquivo e uma cópia dele | etiqueta `versao_config`, artefato `configuracao/config.yaml` |

## Como registrar uma nova versão dos dados

1. Rodar os notebooks de dados e substituir `dados/processado/dataset_integrado.csv` e o dicionário.
2. Guardar os relatórios da execução em `dados/documentacao/`.
3. Rodar `python -m src.versoes registrar-dados v2 --origem "..." --observacao "..."`.
4. Trocar `dados.versao` para `v2` em `config/config.yaml`.
5. Fazer o commit das quatro mudanças juntas.

Se o arquivo de dados mudar sem esse registro, a validação de entrada falha e o treino não roda.

## Ciclo de vida do modelo

1. `python -m src.treinar` roda o plano de experimentos e registra o modelo final como `candidato`.
2. O responsável confere as métricas e aprova com `python -m src.promover --versao candidato --aprovado-por "Nome" --motivo "..."`. A versão recebe o apelido `producao` e a anterior passa a `anterior`.
3. `python -m src.monitorar` aplica o plano de monitoramento ao modelo em produção.
4. Se o monitoramento pedir, um novo candidato é treinado e comparado. Se ele não for melhor, a versão atual é revalidada com `python -m src.promover --versao 1 --revalidar ...`.
5. Para voltar à versão anterior basta promover de novo o número dela.

Cada passo 2 e 4 acrescenta uma linha em `governanca/historico_modelo.csv`, que fica no Git.

## Conferir as versões

`python -m src.versoes` mostra o hash do código, o commit, o hash da configuração, a versão dos dados com a conferência contra o manifesto e o histórico do modelo.

## Tags no Git

Cada entrega recebe uma tag. A primeira é `v1.0`, com a solução da Etapa 4 e o modelo na versão 1. Uma mudança de dados, de configuração ou de modelo que vá para produção gera uma tag nova.
