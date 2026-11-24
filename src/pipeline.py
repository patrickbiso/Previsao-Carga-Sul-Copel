"""Pipeline comum a treino, previsão e monitoramento."""
import json
import time
from dataclasses import dataclass

import pandas as pd

from .avaliacao import metricas
from .dados import carregar_dados, ler_dicionario, preparar, validar_entrada, validar_variaveis
from .modelos import ModeloCarga, criar_estimador
from .variaveis import FONTE_DO_GRUPO, GRUPOS, criar_variaveis, tabela_feriados

EXCLUSAO_PADRAO = ("historico_cruza_regime",)


@dataclass
class Contexto:
    cfg: dict
    versao_dados: dict
    validacao: pd.DataFrame
    prep: pd.DataFrame
    X: pd.DataFrame
    origem: dict
    feriados: pd.DataFrame
    dicionario: pd.DataFrame

    @property
    def carga(self):
        return self.prep["carga_mwmed"]


def montar_contexto(cfg):
    """Dados brutos, validação, preparação e variáveis."""
    df, versao = carregar_dados(cfg)
    dicionario = ler_dicionario(cfg)
    validacao = validar_entrada(df, cfg, versao, dicionario)
    if (validacao["resultado"] == "ERRO").any():
        falhas = validacao.loc[validacao["resultado"] == "ERRO", "verificacao"].tolist()
        raise RuntimeError(f"Validação de entrada falhou em {falhas}")
    prep = preparar(df, cfg)
    X, origem = criar_variaveis(prep, cfg["pipeline"]["horizonte_dias"])
    validar_variaveis(list(origem.values()) + ["feriado", "nome_feriado"], dicionario)
    return Contexto(cfg, versao, validacao, prep, X, origem, tabela_feriados(prep), dicionario)


def variaveis_da_run(run):
    if run["algoritmo"] == "Referência sazonal":
        return ["carga_sem1"]
    return [c for g in run["grupos"] for c in GRUPOS[g]]


def dias_usaveis(ctx, variaveis):
    return ctx.prep["avaliavel"] & ctx.X[variaveis].notna().all(axis=1) & ctx.X["nivel_semana"].notna()


def dias_de_treino(ctx, run, inicio, fim):
    """Dias de treino no período, sem os dias excluídos. Devolve também a contagem dos excluídos."""
    usavel = dias_usaveis(ctx, variaveis_da_run(run))
    no_treino = usavel & (ctx.prep.index >= inicio) & (ctx.prep.index <= fim)
    excluidos, fora_sempre = {}, pd.Series(False, index=ctx.prep.index)
    for flag in EXCLUSAO_PADRAO + tuple(run.get("excluir_treino", ())):
        marca = no_treino & (ctx.prep[flag] == 1)
        excluidos[flag] = int(marca.sum())
        no_treino &= ~marca
        fora_sempre |= ctx.prep[flag] == 1
    return no_treino, excluidos, fora_sempre


def treinar_modelo(ctx, run, dias):
    estimador, params = criar_estimador(run["algoritmo"], run.get("parametros") or {}, ctx.cfg["pipeline"]["semente"], ctx.feriados)
    modelo = ModeloCarga(estimador, variaveis_da_run(run), run["alvo"]).fit(ctx.X[dias], ctx.carga[dias])
    return modelo, params


def prever_periodo(ctx, run, modelo, dias, inicio_treino=None, fora_sempre=None):
    """Previsão dos dias pedidos. Com retreino mensal, cada mês usa dados até 7 dias antes do mês."""
    if run.get("retreino") != "mensal":
        return pd.Series(modelo.predict(ctx.X[dias]), index=ctx.prep.index[dias]), 0
    h = ctx.cfg["pipeline"]["horizonte_dias"]
    usavel = dias_usaveis(ctx, variaveis_da_run(run))
    p = pd.Series(index=ctx.prep.index[dias], dtype=float)
    apto = usavel & ~fora_sempre & (ctx.prep.index >= inicio_treino)
    ajustes = 0
    for mes, datas in pd.Series(p.index, index=p.index).groupby(p.index.to_period("M")).groups.items():
        origem = mes.start_time - pd.Timedelta(days=h)
        m_tr = apto & (ctx.prep.index <= origem)
        mod_mes, _ = treinar_modelo(ctx, run, m_tr)
        p[datas] = mod_mes.predict(ctx.X.loc[datas])
        ajustes += 1
    return p, ajustes


def executar_run(ctx, run, treino=("treino",), avaliar=("validacao", "teste")):
    """Treina e avalia uma configuração. Devolve o registro, o modelo e as previsões."""
    cfg = ctx.cfg
    janelas = cfg["pipeline"]["janelas"]
    inicio = time.time()
    variaveis = variaveis_da_run(run)
    validar_variaveis([ctx.origem[c] for c in variaveis], ctx.dicionario)
    ini_treino, fim_treino = janelas[treino[0]][0], janelas[treino[-1]][1]
    no_treino, excluidos, fora_sempre = dias_de_treino(ctx, run, ini_treino, fim_treino)
    modelo, params = treinar_modelo(ctx, run, no_treino)
    tempo = time.time() - inicio

    grupos = run["grupos"]
    linha = {
        "run": run["id"], "descricao": run["descricao"], "modelo": run["algoritmo"],
        "parametros": json.dumps(params, ensure_ascii=False),
        "parametros_completos": json.dumps(modelo.estimador.get_params(), ensure_ascii=False, default=str),
        "alvo": "carga (MWmed)" if run["alvo"] == "nivel" else "razão carga / média da semana conhecida",
        "grupos_variaveis": "+".join(grupos) if grupos else "carga de 7 dias antes",
        "fontes_externas": "+".join(sorted({FONTE_DO_GRUPO[g] for g in grupos if g in FONTE_DO_GRUPO})) or "nenhuma",
        "n_variaveis": len(variaveis),
        "janela_treino": f"{ini_treino} a {fim_treino}",
        "dias_treino": int(no_treino.sum()),
        "excluidos_do_treino": json.dumps(excluidos),
        "horizonte_dias": cfg["pipeline"]["horizonte_dias"],
        "semente": cfg["pipeline"]["semente"] if "random_state" in params else None,
        "tempo_treino_s": round(tempo, 2),
        "retreino": run.get("retreino") or "nenhum",
        "elegivel_escolha": "diagnostico" not in run,
        "observacao": run.get("diagnostico", ""),
    }
    usavel = dias_usaveis(ctx, variaveis)
    previsoes, ajustes = {}, 1
    for janela in avaliar:
        m = usavel & (ctx.prep["janela"] == janela)
        p, n = prever_periodo(ctx, run, modelo, m, ini_treino, fora_sempre)
        ajustes += n
        real = ctx.carga[m]
        linha.update(metricas(real, p.to_numpy(), janela, cfg["pipeline"]["percentil_pico"]))
        linha[f"dias_{janela}"] = int(m.sum())
        previsoes[janela] = p
    if run.get("retreino"):
        linha["tempo_treino_s"] = round(time.time() - inicio, 2)
        linha["n_ajustes"] = ajustes
    return linha, modelo, previsoes


def escolher_run(registro, cfg):
    """Menor MAE de validação. No empate vence menos fontes e depois o modelo mais simples."""
    from .modelos import COMPLEXIDADE
    reg = pd.DataFrame(registro)
    candidatos = reg[(reg["run"] != "R01") & reg["elegivel_escolha"]].copy()
    melhor = candidatos["MAE_validacao"].min()
    empatados = candidatos[candidatos["MAE_validacao"] <= melhor * (1 + cfg["pipeline"]["tolerancia_empate"])].copy()
    empatados["n_fontes"] = empatados["fontes_externas"].map(lambda s: 0 if s == "nenhuma" else len(s.split("+")))
    empatados["complexidade"] = empatados["modelo"].map(COMPLEXIDADE)
    escolhida = empatados.sort_values(["n_fontes", "complexidade", "MAE_validacao"]).iloc[0]
    return escolhida["run"], empatados.sort_values("MAE_validacao")[["run", "MAE_validacao"]]
