"""Simula a chegada de dados novos mês a mês e aplica o plano de monitoramento ao modelo em produção.

Uso  python -m src.monitorar
"""
import json
from datetime import date, datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd

from .config import RAIZ, carregar_config
from .dados import FAIXA_CARGA, FAIXA_TEMPERATURA
from .pipeline import dias_de_treino, montar_contexto, prever_periodo, treinar_modelo
from .prever import carregar_modelo, prever
from .rastreio import etiquetas_de_versao, iniciar_mlflow

SAIDA = RAIZ / "resultados" / "monitoramento"
ORDEM = {"OK": 0, "ATENÇÃO": 1, "ALERTA": 2}
COR = {"serie": "#1F5F8B", "ref": "#7A7A7A", "alerta": "#C0392B", "segunda": "#D9822B", "atencao": "#E0A800"}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def situacao(valor, limite, menor_e_pior=False):
    """Compara o indicador com os limites de atenção e de alerta."""
    if valor is None or pd.isna(valor):
        return "OK"
    if menor_e_pior:
        return "ALERTA" if valor < limite["alerta"] else "ATENÇÃO" if valor < limite["atencao"] else "OK"
    return "ALERTA" if valor > limite["alerta"] else "ATENÇÃO" if valor > limite["atencao"] else "OK"


def psi(referencia, atual, faixas=5):
    """Índice de estabilidade populacional com faixas definidas pelos quantis da referência."""
    referencia, atual = pd.Series(referencia).dropna(), pd.Series(atual).dropna()
    if len(referencia) < 30 or len(atual) < 20:
        return np.nan
    cortes = np.quantile(referencia, np.linspace(0, 1, faixas + 1))
    cortes[0], cortes[-1] = -np.inf, np.inf
    p = np.histogram(referencia, cortes)[0] / len(referencia)
    q = np.histogram(atual, cortes)[0] / len(atual)
    p, q = np.clip(p, 1e-3, None), np.clip(q, 1e-3, None)
    return float(((q - p) * np.log(q / p)).sum())


def meses_entre(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


def indicadores_do_mes(mes, ctx, tab, serie_drift, ref_treino, ficha, lim):
    """Indicadores de dados, modelo e negócio de um mês."""
    dias = pd.date_range(mes.start_time, mes.end_time.normalize(), freq="D")
    t = tab.loc[tab.index.isin(dias)]
    aval = t.dropna(subset=["real", "previsto"])
    erro = aval["previsto"] - aval["real"]
    erro_ref = aval["referencia"] - aval["real"]
    mae, mae_ref = erro.abs().mean(), erro_ref.abs().mean()
    lin = {"mes": str(mes), "dias_esperados": len(dias), "dias_recebidos": int(t["real"].notna().sum())}

    # dados
    lin["dias_faltantes"] = len(dias) - lin["dias_recebidos"]
    lin["pct_ausentes"] = float(ctx.X.loc[ctx.X.index.isin(dias), ficha["variaveis"]].isna().mean().max() * 100)
    carga, temp = ctx.carga[ctx.prep.index.isin(dias)], ctx.prep.loc[ctx.prep.index.isin(dias), "temp_media_sul"]
    lin["valores_fora_da_faixa"] = int(((carga < FAIXA_CARGA[0]) | (carga > FAIXA_CARGA[1])).sum()
                                       + ((temp < FAIXA_TEMPERATURA[0]) | (temp > FAIXA_TEMPERATURA[1])).sum())
    n = ctx.cfg["monitoramento"]["janela_drift_meses"]
    janela = pd.period_range(mes - (n - 1), mes, freq="M")
    meses_da_janela = [p.month for p in janela]
    for v, s in serie_drift.items():
        atual = s[s.index.to_period("M").isin(janela)]
        referencia = ref_treino[v][ref_treino[v].index.month.isin(meses_da_janela)]
        lin[f"psi_{v}"] = psi(referencia, atual)

    # modelo
    lin["MAE"], lin["MAE_referencia"] = mae, mae_ref
    lin["MAPE"] = float((erro.abs() / aval["real"]).mean() * 100)
    lin["vies"] = float(erro.mean())
    lin["vies_pct_da_carga"] = float(abs(erro.mean()) / aval["real"].mean() * 100)
    lin["razao_mae_sobre_teste"] = float(mae / ficha["teste"]["MAE_teste"])
    lin["erro_max"] = float(erro.abs().max())

    # negócio
    lin["ganho_sobre_referencia_pct"] = float((1 - mae / mae_ref) * 100)
    lin["pct_dias_subestimou_5"] = float(((erro / aval["real"]) < -0.05).mean() * 100)
    lin["erro_evitado_mwh"] = float((mae_ref - mae) * 24 * len(aval))
    return lin


def avaliar_limites(ind, lim, variaveis_drift):
    """Uma linha por indicador e mês, com a situação e a ação prevista no plano."""
    regras = [
        ("dados", "dias_faltantes", lim["dados"]["dias_faltantes"], False, "conferir a publicação do ONS e segurar a previsão dos dias afetados"),
        ("dados", "pct_ausentes", lim["dados"]["pct_ausentes"], False, "identificar a fonte com falha e refazer a integração"),
        ("dados", "valores_fora_da_faixa", lim["dados"]["valores_fora_da_faixa"], False, "tratar como erro de medição e abrir incidente"),
        ("modelo", "MAPE", lim["modelo"]["mape_pct"], False, "investigar os dias de maior erro e avaliar retreino"),
        ("modelo", "razao_mae_sobre_teste", lim["modelo"]["razao_mae_sobre_teste"], False, "comparar com o modelo retreinado e avaliar troca"),
        ("modelo", "vies_pct_da_carga", lim["modelo"]["vies_pct_da_carga"], False, "verificar erro sistemático e avaliar retreino"),
        ("negocio", "ganho_sobre_referencia_pct", lim["negocio"]["ganho_minimo_sobre_referencia_pct"], True, "rever se o modelo ainda se justifica frente à regra simples"),
        ("negocio", "pct_dias_subestimou_5", lim["negocio"]["pct_dias_subestimou_5"], False, "avisar o planejamento e usar margem de segurança"),
    ] + [("dados", f"psi_{v}", lim["dados"]["psi"], False, "conferir se o erro subiu no mesmo período e avaliar retreino") for v in variaveis_drift]
    linhas = []
    for _, r in ind.iterrows():
        for dim, nome, limite, menor, acao in regras:
            s = situacao(r[nome], limite, menor)
            linhas.append({"mes": r["mes"], "dimensao": dim, "indicador": nome, "valor": r[nome],
                           "limite_atencao": limite["atencao"], "limite_alerta": limite["alerta"],
                           "situacao": s, "acao": acao if s != "OK" else ""})
    return pd.DataFrame(linhas)


def decidir(aval, lim):
    """Decisão de cada mês a partir das situações dos indicadores."""
    qualidade = ["dias_faltantes", "pct_ausentes", "valores_fora_da_faixa"]
    seguidos, decisoes = 0, []
    for mes, g in aval.groupby("mes", sort=True):
        def pior(filtro):
            return max((ORDEM[x] for x in g.loc[filtro, "situacao"]), default=0)
        q = pior(g["indicador"].isin(qualidade))
        drift = pior(g["indicador"].str.startswith("psi_"))
        erro = pior(g["dimensao"] == "modelo")
        negocio = pior(g["dimensao"] == "negocio")
        erro_alerta = pior(g["indicador"].isin(["MAPE", "razao_mae_sobre_teste"])) == 2
        seguidos = seguidos + 1 if erro_alerta else 0
        if seguidos >= lim["modelo"]["meses_seguidos_em_alerta_para_retreinar"]:
            d = "retreinar e submeter novo candidato à aprovação"
        elif q == 2:
            d = "investigar os dados antes de usar a previsão"
        elif erro == 2 or negocio == 2:
            d = "investigar o modelo"
        elif drift == 2 and max(erro, negocio) >= 1:
            d = "investigar o modelo, drift com piora do erro"
        elif drift == 2:
            d = "acompanhar, drift sem piora do erro"
        elif max(q, drift, erro, negocio) >= 1:
            d = "manter e acompanhar"
        else:
            d = "manter"
        decisoes.append({"mes": mes, "pior_situacao": {0: "OK", 1: "ATENÇÃO", 2: "ALERTA"}[max(q, drift, erro, negocio)],
                         "meses_seguidos_com_erro_em_alerta": seguidos, "decisao": d})
    return pd.DataFrame(decisoes)


def atualidade_das_fontes(ctx, lim, variaveis_modelo):
    """Último dado de cada fonte em relação ao fim do dataset."""
    fim = ctx.prep.index.max()
    fontes = [("ONS, carga diária", "carga_mwmed", "alvo e histórico do modelo"),
              ("Open-Meteo, temperatura", "temp_media_sul", "variável do modelo"),
              ("ANEEL, interrupções", None, "escolha dos dias de treino"),
              ("ANEEL, DEC e FEC", "dec_medio_conjuntos", "validação"),
              ("EPE, consumo por classe", "consumo_pr_total_mwh", "análise, fora do modelo em produção")]
    linhas = []
    for nome, col, uso in fontes:
        if col is None:
            ultimo = ctx.prep.index[ctx.prep["tem_dados_interrupcao"] == 1].max()
        else:
            ultimo = ctx.prep[col].dropna().index.max()
        atraso = meses_entre(ultimo, fim)
        linhas.append({"fonte": nome, "ultimo_dado": ultimo.date().isoformat(), "atraso_meses": atraso, "uso": uso,
                       "situacao": situacao(atraso, lim["dados"]["atraso_fonte_meses"])})
    return pd.DataFrame(linhas)


def governanca(ctx, tab, ficha, cfg, lim):
    """Indicadores de governança na data da execução."""
    aval = tab.dropna(subset=["real", "previsto"]).copy()
    aval["ape"] = (aval["previsto"] - aval["real"]).abs() / aval["real"] * 100
    feriado = ctx.prep.loc[aval.index, "feriado"] == 1
    util = (ctx.prep.loc[aval.index, "dia_semana"] < 5) & ~feriado
    fds = (ctx.prep.loc[aval.index, "dia_semana"] >= 5) & ~feriado
    segmentos = pd.DataFrame({"segmento": ["dias úteis", "fins de semana", "feriados"],
                              "dias": [int(util.sum()), int(fds.sum()), int(feriado.sum())],
                              "MAPE": [aval.loc[util, "ape"].mean(), aval.loc[fds, "ape"].mean(), aval.loc[feriado, "ape"].mean()]})
    estacao = ctx.prep.loc[aval.index, "estacao"]
    por_estacao = aval.groupby(estacao)["ape"].agg(["size", "mean"]).rename(columns={"size": "dias", "mean": "MAPE"}).reset_index()
    por_estacao.columns = ["segmento", "dias", "MAPE"]
    segmentos = pd.concat([segmentos, por_estacao], ignore_index=True)

    fim_treino = pd.Timestamp(ficha["janela_treino"].split(" a ")[1])
    hoje = pd.Timestamp(date.today())
    arq_inc = RAIZ / "governanca" / "incidentes.csv"
    inc = pd.read_csv(arq_inc) if arq_inc.exists() else pd.DataFrame(columns=["situacao"])
    abertos = int(inc["situacao"].astype(str).str.startswith("aberto").sum())
    g = lim["governanca"]
    razao = float(segmentos.loc[2, "MAPE"] / segmentos.loc[0, "MAPE"])
    # conta a partir do treino ou da última revalidação registrada
    marco = fim_treino
    hist = RAIZ / "governanca" / "historico_modelo.csv"
    if hist.exists():
        h = pd.read_csv(hist)
        h = h[(h["versao"].astype(str) == str(ficha["versao"])) & h["acao"].str.startswith("revalidado")]
        if len(h):
            marco = max(marco, pd.Timestamp(h["data"].max()))
    idade = max(0, meses_entre(marco, ctx.prep.index.max()))
    sem_revisao = int((hoje - pd.Timestamp(cfg["monitoramento"]["revisao_model_card"])).days)
    linhas = [
        ("razao_mape_feriado_sobre_util", razao, g["razao_mape_feriado_sobre_util"], "revisar as variáveis de feriado e avisar o planejamento sobre a incerteza nesses dias"),
        ("meses_desde_treino_ou_revalidacao", idade, g["meses_desde_treino_ou_revalidacao"], "treinar candidato com os dados mais recentes e comparar"),
        ("dias_sem_revisar_model_card", sem_revisao, g["dias_sem_revisar_model_card"], "revisar o Model Card e a matriz de riscos"),
        ("incidentes_abertos", abertos, g["incidentes_abertos"], "tratar os incidentes abertos e registrar a solução"),
    ]
    tabela = pd.DataFrame([{"indicador": n, "valor": v, "limite_atencao": l["atencao"], "limite_alerta": l["alerta"],
                            "situacao": situacao(v, l), "acao": a if situacao(v, l) != "OK" else ""} for n, v, l, a in linhas])
    return tabela, segmentos


def comparar_retreino(ctx, run, tab, ficha, inicio, fim):
    """Compara o modelo em produção com um candidato treinado até o ano anterior e com retreino mensal."""
    ini_treino = ficha["janela_treino"].split(" a ")[0]
    alvo = (ctx.prep.index >= inicio) & (ctx.prep.index <= fim) & ctx.prep["avaliavel"] \
        & ctx.X[ficha["variaveis"] + ["nivel_semana"]].notna().all(axis=1)
    fim_anual = (pd.Timestamp(inicio) - pd.Timedelta(days=1)).date().isoformat()
    dias, _, fora = dias_de_treino(ctx, run, ini_treino, fim_anual)
    anual, _ = treinar_modelo(ctx, run, dias)
    p_anual = pd.Series(anual.predict(ctx.X[alvo]), index=ctx.prep.index[alvo])
    p_mensal, _ = prever_periodo(ctx, {**run, "retreino": "mensal"}, None, alvo, ini_treino, fora)
    comp = pd.DataFrame({"real": tab["real"], "producao": tab["previsto"], "treino_ate_ano_anterior": p_anual,
                         "retreino_mensal": p_mensal, "referencia": tab["referencia"]}).dropna()
    mensal = comp.groupby(comp.index.to_period("M")).apply(
        lambda g: pd.Series({c: (g[c] - g["real"]).abs().mean() for c in comp.columns if c != "real"}))
    mensal.index = mensal.index.astype(str)
    total = pd.Series({c: (comp[c] - comp["real"]).abs().mean() for c in comp.columns if c != "real"}, name="periodo")
    mape = pd.Series({c: ((comp[c] - comp["real"]).abs() / comp["real"]).mean() * 100 for c in comp.columns if c != "real"}, name="MAPE_periodo")
    return mensal, total, mape, fim_anual


def figuras(tab, ind, aval, mensal_retreino, lim, ficha, variaveis_drift):
    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 200, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.6,
                         "axes.titlesize": 12, "axes.titleweight": "bold", "font.size": 10})
    rot = [MESES[int(m[-2:]) - 1] for m in ind["mes"]]
    x = np.arange(len(ind))

    # figura 1, erro mensal contra os limites
    fig, ax = plt.subplots(figsize=(11, 4.2))
    mape_ref = ind["MAE_referencia"] / ind["MAE"] * ind["MAPE"]
    ax.bar(x - 0.2, mape_ref, 0.4, color=COR["ref"], label="regra simples")
    ax.bar(x + 0.2, ind["MAPE"], 0.4, color=COR["serie"], label="modelo em produção")
    ax.axhline(lim["modelo"]["mape_pct"]["atencao"], color=COR["atencao"], ls="--", lw=1.2, label=f"atenção ({lim['modelo']['mape_pct']['atencao']:g}%)")
    ax.axhline(lim["modelo"]["mape_pct"]["alerta"], color=COR["alerta"], ls="--", lw=1.2, label=f"alerta ({lim['modelo']['mape_pct']['alerta']:g}%)")
    ax.axhline(ficha["teste"]["MAPE_teste"], color="#1A1A1A", ls=":", lw=1, label=f"teste 2025 ({ficha['teste']['MAPE_teste']:.1f}%)".replace(".", ","))
    ax.set_xticks(x, rot); ax.set_ylabel("MAPE (%)"); ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=5, frameon=False, fontsize=9)
    ax.set_title("Erro mensal do modelo em produção e limites do plano", loc="left", pad=30)
    fig.savefig(SAIDA / "fig1_erro_mensal.png", bbox_inches="tight"); plt.close(fig)

    # figura 2, real x previsto no período monitorado
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.plot(tab.index, tab["real"], color="#1A1A1A", lw=1.1, label="carga real")
    ax.plot(tab.index, tab["referencia"], color=COR["ref"], lw=0.9, alpha=0.8, label="regra simples")
    ax.plot(tab.index, tab["previsto"], color=COR["segunda"], lw=1.1, label="modelo em produção")
    ax.set_ylabel("MWmed"); ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False)
    ax.set_title("Carga real e prevista com 7 dias de antecedência no período monitorado", loc="left", pad=30)
    fig.savefig(SAIDA / "fig2_real_x_previsto.png", bbox_inches="tight"); plt.close(fig)

    # figura 3, drift das variáveis
    fig, ax = plt.subplots(figsize=(11, 4.2))
    cores = [COR["serie"], COR["segunda"], "#4C9F70", "#7A5195", COR["ref"]]
    for v, c in zip(variaveis_drift, cores):
        ax.plot(x, ind[f"psi_{v}"], marker="o", ms=4, lw=1.4, color=c, label=NOMES[f"psi_{v}"].replace("PSI da ", "").replace("PSI do ", ""))
    ax.axhline(lim["dados"]["psi"]["atencao"], color=COR["atencao"], ls="--", lw=1.2)
    ax.axhline(lim["dados"]["psi"]["alerta"], color=COR["alerta"], ls="--", lw=1.2)
    ax.set_xticks(x, rot); ax.set_ylabel("PSI (janela de 3 meses)"); ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9)
    ax.set_title("Mudança na distribuição dos dados em relação ao treino", loc="left", pad=44)
    fig.savefig(SAIDA / "fig3_drift.png", bbox_inches="tight"); plt.close(fig)

    # figura 4, efeito do retreino
    fig, ax = plt.subplots(figsize=(11, 4.2))
    xm = np.arange(len(mensal_retreino)); rotm = [MESES[int(m[-2:]) - 1] for m in mensal_retreino.index]
    for k, (col, nome, c) in enumerate((("producao", "produção (treino até 2024)", COR["serie"]),
                                        ("treino_ate_ano_anterior", "candidato (treino até 2025)", COR["segunda"]),
                                        ("retreino_mensal", "retreino mensal", "#4C9F70"))):
        ax.bar(xm + (k - 1) * 0.27, mensal_retreino[col], 0.27, color=c, label=nome)
    ax.set_xticks(xm, rotm); ax.set_ylabel("MAE (MWmed)"); ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False)
    ax.set_title("Erro mensal com e sem retreino", loc="left", pad=30)
    fig.savefig(SAIDA / "fig4_retreino.png", bbox_inches="tight"); plt.close(fig)


def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(v):
    """Número curto para tabela, inteiro quando não tem decimais."""
    return br(v) if float(v).is_integer() else br(v, 2)


NOMES = {
    "dias_faltantes": "Dias sem carga", "pct_ausentes": "Variáveis ausentes (%)", "valores_fora_da_faixa": "Valores fora da faixa",
    "MAPE": "MAPE (%)", "razao_mae_sobre_teste": "MAE do mês sobre o MAE do teste", "vies_pct_da_carga": "Viés (% da carga)",
    "ganho_sobre_referencia_pct": "Ganho sobre a regra simples (%)", "pct_dias_subestimou_5": "Dias com subestimação acima de 5% (%)",
    "psi_temp_media_sul": "PSI da temperatura média", "psi_dif_temp_ref": "PSI da diferença de temperatura",
    "psi_rel_carga_sem1": "PSI da carga relativa de 7 dias antes", "psi_razao_alvo": "PSI do alvo relativo",
    "psi_carga_mwmed": "PSI da carga",
    "razao_mape_feriado_sobre_util": "MAPE de feriados sobre o de dias úteis", "meses_desde_treino_ou_revalidacao": "Meses desde o treino ou a última revalidação",
    "dias_sem_revisar_model_card": "Dias sem revisar o Model Card", "incidentes_abertos": "Incidentes abertos",
}
DIMENSOES = {"dados": "Dados", "modelo": "Modelo", "negocio": "Negócio"}


def tabela_md(df):
    linhas = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        linhas.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(linhas)


def relatorio(cfg, ficha, versao_modelo, ctx, ind, aval, dec, fontes, gov, segmentos, mensal_r, total_r, mape_r, fim_anual, id_exec):
    m = cfg["monitoramento"]
    alertas = aval[aval["situacao"] != "OK"]
    tot_mae = (ind["MAE"] * ind["dias_recebidos"]).sum() / ind["dias_recebidos"].sum()
    tot_ref = (ind["MAE_referencia"] * ind["dias_recebidos"]).sum() / ind["dias_recebidos"].sum()
    resumo_mes = ind[["mes", "MAE", "MAPE", "vies", "ganho_sobre_referencia_pct", "pct_dias_subestimou_5"]].copy()
    resumo_mes = resumo_mes.merge(dec[["mes", "pior_situacao", "decisao"]], on="mes")
    for c, casas in (("MAE", 0), ("MAPE", 2), ("vies", 0), ("ganho_sobre_referencia_pct", 1), ("pct_dias_subestimou_5", 1)):
        resumo_mes[c] = resumo_mes[c].map(lambda v: br(v, casas))
    resumo_mes.columns = ["Mês", "MAE (MWmed)", "MAPE (%)", "Viés (MWmed)", "Ganho sobre a regra simples (%)", "Dias com subestimação acima de 5% (%)", "Situação", "Decisão"]
    tab_alertas = alertas[["mes", "dimensao", "indicador", "valor", "limite_atencao", "limite_alerta", "situacao", "acao"]].copy()
    tab_alertas["valor"] = tab_alertas["valor"].map(lambda v: br(v, 2))
    tab_alertas["indicador"] = tab_alertas["indicador"].map(lambda n: NOMES.get(n, n))
    tab_alertas["dimensao"] = tab_alertas["dimensao"].map(DIMENSOES)
    for c in ("limite_atencao", "limite_alerta"):
        tab_alertas[c] = tab_alertas[c].map(num)
    tab_alertas.columns = ["Mês", "Dimensão", "Indicador", "Valor", "Atenção", "Alerta", "Situação", "Ação do plano"]
    retreino = pd.DataFrame({"Modelo": ["Em produção (treino até 2024)", f"Candidato (treino até {fim_anual[:4]})", "Retreino mensal", "Regra simples"],
                             "MAE no período (MWmed)": [br(total_r[c]) for c in ("producao", "treino_ate_ano_anterior", "retreino_mensal", "referencia")],
                             "MAPE (%)": [br(mape_r[c], 2) for c in ("producao", "treino_ate_ano_anterior", "retreino_mensal", "referencia")]})
    f = fontes.copy(); f.columns = ["Fonte", "Último dado", "Atraso (meses)", "Uso", "Situação"]
    g = gov.copy()
    g["indicador"] = g["indicador"].map(lambda n: NOMES.get(n, n))
    for c in ("valor", "limite_atencao", "limite_alerta"):
        g[c] = g[c].map(num)
    g.columns = ["Indicador", "Valor", "Atenção", "Alerta", "Situação", "Ação do plano"]
    s = segmentos.copy(); s["MAPE"] = s["MAPE"].map(lambda v: br(v, 2)); s.columns = ["Segmento", "Dias", "MAPE (%)"]
    ganho_candidato = (1 - total_r["treino_ate_ano_anterior"] / total_r["producao"]) * 100
    ganho_mensal = (1 - total_r["retreino_mensal"] / total_r["producao"]) * 100
    n_alerta, n_atencao = int((aval["situacao"] == "ALERTA").sum()), int((aval["situacao"] == "ATENÇÃO").sum())
    tol = cfg["pipeline"]["tolerancia_empate"] * 100
    if ganho_candidato > tol:
        recomendacao = (f"Recomendação. O candidato melhora o erro acima da tolerância de {br(tol, 0)}%. Treinar a nova versão com "
                        "`python -m src.treinar`, registrar como candidato e submeter à aprovação.")
    else:
        recomendacao = (f"Recomendação. A diferença fica dentro da tolerância de {br(tol, 0)}%, então a versão em produção é mantida "
                        "e a revalidação é registrada no histórico do modelo.")
    texto = f"""# Relatório de monitoramento

Execução {id_exec}. Modelo {ficha['modelo_registrado']} versão {versao_modelo}, treinado com {ficha['janela_treino']}. Dados {ctx.versao_dados['rotulo']}.

A simulação trata cada mês de {m['inicio'][:7]} a {m['fim'][:7]} como um lote novo de dados que chega depois do treino. O modelo em produção fica congelado e prevê cada dia com 7 dias de antecedência. Os limites vêm de `config/config.yaml`.

## Resumo

- No período o modelo teve MAE de {br(tot_mae)} MWmed, contra {br(tot_ref)} da regra simples. No teste de 2025 o MAE foi de {br(ficha['teste']['MAE_teste'])} MWmed.
- Foram avaliados {len(aval)} pares de indicador e mês. {n_alerta} ficaram em alerta e {n_atencao} em atenção.
- Decisão do último mês, {dec.iloc[-1]['mes']}, {dec.iloc[-1]['decisao']}.

## Situação por mês

{tabela_md(resumo_mes)}

## Indicadores fora do limite

{tabela_md(tab_alertas) if len(tab_alertas) else "Nenhum indicador saiu do limite."}

## Retreino

{tabela_md(retreino)}

O candidato treinado com um ano a mais de dados muda o MAE em {br(-ganho_candidato, 1)}% em relação ao modelo em produção. O retreino mensal muda em {br(-ganho_mensal, 1)}%.

{recomendacao}

## Mudança nos dados

O PSI compara a distribuição dos últimos {m['janela_drift_meses']} meses com a dos mesmos meses no período de treino. O da carga em MWmed foi de {br(ind['psi_carga_mwmed'].min(), 2)} a {br(ind['psi_carga_mwmed'].max(), 2)}, muito acima do limite, porque o consumo cresce todo ano. Esse indicador fica só como contexto. O modelo usa a carga em forma relativa, e o PSI dessa variável ficou entre {br(ind['psi_rel_carga_sem1'].min(), 2)} e {br(ind['psi_rel_carga_sem1'].max(), 2)}.

## Atualidade das fontes

{tabela_md(f)}

## Governança

{tabela_md(g)}

Erro por segmento no período, para verificar se o modelo erra de forma desigual.

{tabela_md(s)}

## Arquivos

- `indicadores_mensais.csv` tem todos os indicadores por mês.
- `avaliacao_limites.csv` tem a situação de cada indicador em cada mês e a ação prevista.
- `decisoes.csv` tem a decisão de cada mês.
- `comparacao_retreino.csv` tem o MAE mensal de cada alternativa de retreino.
- As figuras 1 a 4 mostram o erro mensal, a série prevista, o drift e o efeito do retreino.
"""
    (SAIDA / "relatorio_monitoramento.md").write_text(texto, encoding="utf-8")


def main():
    cfg = carregar_config()
    ctx = montar_contexto(cfg)
    modelo, ficha, versao = carregar_modelo(cfg)
    m, lim = cfg["monitoramento"], cfg["monitoramento"]["limites"]
    SAIDA.mkdir(parents=True, exist_ok=True)
    agora = datetime.now()
    id_exec = agora.strftime("%Y%m%d_%H%M%S")

    previsto = prever(ctx, modelo, m["inicio"], m["fim"])
    tab = pd.DataFrame({"real": ctx.carga[previsto.index], "previsto": previsto, "referencia": ctx.X.loc[previsto.index, "carga_sem1"]})

    # séries para drift e referência do período de treino do modelo
    series = {v: (ctx.carga / ctx.X["nivel_semana"] if v == "razao_alvo" else ctx.prep[v] if v in ctx.prep else ctx.X[v])
              for v in m["variaveis_drift"]}
    ini_t, fim_t = ficha["janela_treino"].split(" a ")
    ref_treino = {v: s[(s.index >= ini_t) & (s.index <= fim_t)].dropna() for v, s in series.items()}

    meses = pd.period_range(m["inicio"], m["fim"], freq="M")
    ind = pd.DataFrame([indicadores_do_mes(p, ctx, tab, series, ref_treino, ficha, lim) for p in meses])
    drift_com_limite = [v for v in m["variaveis_drift"] if v not in m.get("variaveis_contexto", [])]
    aval = avaliar_limites(ind, lim, drift_com_limite)
    dec = decidir(aval, lim)
    fontes = atualidade_das_fontes(ctx, lim, ficha["variaveis"])
    gov, segmentos = governanca(ctx, tab, ficha, cfg, lim)
    run = next(r for r in cfg["runs"] if r["id"] == ficha["run_de_origem"])
    mensal_r, total_r, mape_r, fim_anual = comparar_retreino(ctx, run, tab, ficha, m["inicio"], m["fim"])

    ind.round(4).to_csv(SAIDA / "indicadores_mensais.csv", index=False)
    aval.round(4).to_csv(SAIDA / "avaliacao_limites.csv", index=False)
    dec.to_csv(SAIDA / "decisoes.csv", index=False)
    fontes.to_csv(SAIDA / "atualidade_fontes.csv", index=False)
    gov.round(3).to_csv(SAIDA / "indicadores_governanca.csv", index=False)
    segmentos.round(3).to_csv(SAIDA / "erro_por_segmento.csv", index=False)
    comp = mensal_r.copy(); comp.loc["periodo"] = total_r
    comp.round(2).to_csv(SAIDA / "comparacao_retreino.csv", index_label="mes")
    tab.round(1).to_csv(SAIDA / "previsoes_monitoradas.csv", index_label="data")
    figuras(tab, ind, aval, mensal_r, lim, ficha, drift_com_limite)
    relatorio(cfg, ficha, versao.version, ctx, ind, aval, dec, fontes, gov, segmentos, mensal_r, total_r, mape_r, fim_anual, id_exec)

    iniciar_mlflow(cfg, cfg["projeto"]["experimento_monitoramento"])
    with mlflow.start_run(run_name=f"monitoramento_{id_exec}"):
        mlflow.set_tags({**etiquetas_de_versao(cfg, ctx.versao_dados), "tipo": "monitoramento",
                         "modelo_versao": versao.version, "periodo": f"{m['inicio']} a {m['fim']}",
                         "decisao_ultimo_mes": dec.iloc[-1]["decisao"]})
        mlflow.log_params({f"limite.{d}.{k}": json.dumps(v) for d, bloco in lim.items() for k, v in bloco.items()})
        for i, r in ind.iterrows():
            mlflow.log_metrics({k: float(r[k]) for k in ("MAE", "MAPE", "vies", "ganho_sobre_referencia_pct", "razao_mae_sobre_teste",
                                                         "pct_dias_subestimou_5") if pd.notna(r[k])}, step=int(i) + 1)
            mlflow.log_metrics({f"psi_{v}": float(r[f"psi_{v}"]) for v in m["variaveis_drift"] if pd.notna(r[f"psi_{v}"])}, step=int(i) + 1)
        mlflow.log_metrics({"alertas": float((aval["situacao"] == "ALERTA").sum()), "atencoes": float((aval["situacao"] == "ATENÇÃO").sum()),
                            "MAE_periodo_producao": float(total_r["producao"]), "MAE_periodo_candidato": float(total_r["treino_ate_ano_anterior"]),
                            "MAE_periodo_retreino_mensal": float(total_r["retreino_mensal"])})
        mlflow.log_artifacts(str(SAIDA), artifact_path="monitoramento")
    print(dec.to_string(index=False))
    print(f"Relatório em {(SAIDA / 'relatorio_monitoramento.md').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
