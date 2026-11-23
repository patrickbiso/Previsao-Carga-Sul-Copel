"""Variáveis do modelo. Todas usam só o que se sabe 7 dias antes do dia previsto."""
import numpy as np
import pandas as pd

CALENDARIO = [f"dow_{k}" for k in range(1, 7)] + ["mes_sen", "mes_cos", "ano_sen", "ano_cos", "feriado",
              "vespera_feriado", "pos_feriado", "fim_de_ano"]
GRUPOS = {
    "calendario": CALENDARIO + ["regime_2", "regime_3", "tendencia_anos"],
    "calendario_relativo": CALENDARIO,
    "regime": ["regime_2", "regime_3"],
    "historico": ["nivel_semana", "carga_sem1", "carga_sem2", "carga_sem3", "carga_ano"],
    "historico_relativo": ["rel_carga_sem1", "rel_carga_sem2", "rel_carga_sem3", "rel_carga_ano"],
    "temperatura": ["temp_media_sul", "temp_max_sul", "temp_min_sul", "graus_dia_calor", "graus_dia_frio",
                    "calor_20", "frio_15", "max_acima_28", "calor_20_util", "frio_15_util",
                    "temp_semana_ref", "dif_temp_ref", "dif_calor_ref", "dif_frio_ref"],
    "epe": ["part_residencial_pr_lag2m", "part_industrial_pr_lag2m", "part_comercial_pr_lag2m", "cresc_consumo_12m_lag2m"],
}
FONTE_DO_GRUPO = {"temperatura": "Open-Meteo", "epe": "EPE"}


def criar_variaveis(d, h=7):
    """Monta as variáveis candidatas e a coluna de origem de cada uma."""
    f = pd.DataFrame(index=d.index)
    origem = {}
    carga = d["carga_mwmed"]
    sem = int(np.ceil(h / 7) * 7)          # mesmo dia da semana

    # calendário
    for k in range(1, 7):
        f[f"dow_{k}"] = (d["dia_semana"] == k).astype(int); origem[f"dow_{k}"] = "dia_semana"
    doy = d.index.dayofyear
    f["mes_sen"], f["mes_cos"] = np.sin(2 * np.pi * d["mes"] / 12), np.cos(2 * np.pi * d["mes"] / 12)
    f["ano_sen"], f["ano_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    origem.update({"mes_sen": "mes", "mes_cos": "mes", "ano_sen": "data", "ano_cos": "data"})
    fer = d["feriado"].fillna(0).astype(int)
    f["feriado"] = fer
    f["vespera_feriado"] = fer.shift(-1, fill_value=0)
    f["pos_feriado"] = fer.shift(1, fill_value=0)
    f["fim_de_ano"] = (((d.index.month == 12) & (d.index.day >= 24)) | ((d.index.month == 1) & (d.index.day <= 2))).astype(int)
    origem.update({"feriado": "feriado", "vespera_feriado": "feriado", "pos_feriado": "feriado", "fim_de_ano": "data"})
    for r in (2, 3):
        f[f"regime_{r}"] = (d["regime_metodologico"] == r).astype(int); origem[f"regime_{r}"] = "regime_metodologico"
    f["tendencia_anos"] = (d.index - pd.Timestamp("2015-01-01")).days / 365.25; origem["tendencia_anos"] = "data"

    # histórico da carga até D
    f["nivel_semana"] = carga.shift(h).rolling(7, min_periods=7).mean()
    for k, lag in (("1", sem), ("2", sem + 7), ("3", sem + 14)):
        f[f"carga_sem{k}"] = carga.shift(lag)
    f["carga_ano"] = carga.shift(364)
    for c in ("nivel_semana", "carga_sem1", "carga_sem2", "carga_sem3", "carga_ano"):
        origem[c] = "carga_mwmed"
    # versão relativa
    for c in ("carga_sem1", "carga_sem2", "carga_sem3", "carga_ano"):
        f[f"rel_{c}"] = f[c] / f["nivel_semana"]; origem[f"rel_{c}"] = "carga_mwmed"

    # temperatura
    for c in ("temp_media_sul", "temp_max_sul", "temp_min_sul", "graus_dia_calor", "graus_dia_frio"):
        f[c] = d[c]; origem[c] = c
    t = d["temp_media_sul"]
    util = ((d["dia_semana"] < 5) & (fer == 0)).astype(int)
    f["calor_20"] = (t - 20).clip(lower=0)
    f["frio_15"] = (15 - t).clip(lower=0)
    f["max_acima_28"] = (d["temp_max_sul"] - 28).clip(lower=0)
    f["calor_20_util"] = f["calor_20"] * util
    f["frio_15_util"] = f["frio_15"] * util
    # temperatura da semana de referência
    f["temp_semana_ref"] = t.shift(h).rolling(7, min_periods=7).mean()
    f["dif_temp_ref"] = t - f["temp_semana_ref"]
    f["dif_calor_ref"] = f["calor_20"] - f["calor_20"].shift(h).rolling(7, min_periods=7).mean()
    f["dif_frio_ref"] = f["frio_15"] - f["frio_15"].shift(h).rolling(7, min_periods=7).mean()
    for c in ("calor_20", "frio_15", "calor_20_util", "frio_15_util", "temp_semana_ref", "dif_temp_ref",
              "dif_calor_ref", "dif_frio_ref"):
        origem[c] = "temp_media_sul"
    origem["max_acima_28"] = "temp_max_sul"

    # perfil da EPE, já defasado
    for c in ("part_residencial_pr_lag2m", "part_industrial_pr_lag2m", "part_comercial_pr_lag2m"):
        f[c] = d[c]; origem[c] = c
    f["cresc_consumo_12m_lag2m"] = d["consumo_pr_total_mwh_lag2m"] / d["consumo_pr_total_mwh_lag2m"].shift(365) - 1
    origem["cresc_consumo_12m_lag2m"] = "consumo_pr_total_mwh_lag2m"
    return f, origem


def tabela_feriados(d):
    """Feriados no formato do Prophet, com véspera e dia seguinte."""
    fer = d.loc[d["feriado"] == 1, ["nome_feriado"]].reset_index()
    return pd.DataFrame({"holiday": fer["nome_feriado"].fillna("feriado").to_numpy(), "ds": fer["data"].to_numpy(),
                         "lower_window": -1, "upper_window": 1})
