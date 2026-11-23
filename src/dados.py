"""Carga, versão, validação e preparação dos dados."""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .config import RAIZ, sha256

COLUNAS_OBRIGATORIAS = ["data", "carga_mwmed", "dia_semana", "mes", "feriado", "regime_metodologico",
                        "flag_imputado", "flag_evento_conhecido", "flag_grande_interrupcao",
                        "temp_media_sul", "temp_max_sul", "temp_min_sul", "graus_dia_calor", "graus_dia_frio"]
# só filtram dias de treino
COLUNAS_SO_FILTRO = {"flag_grande_interrupcao", "flag_evento_conhecido", "flag_imputado"}
# colunas da Etapa 2 conhecidas antes do dia
CALENDARIO_ETAPA2 = {"data", "dia_semana", "mes", "feriado", "nome_feriado", "fim_de_semana",
                     "regime_metodologico", "carga_mwmed"}
FAIXA_CARGA = (3000, 30000)
FAIXA_TEMPERATURA = (-5, 40)


def ler_manifesto(cfg):
    arq = RAIZ / cfg["dados"]["manifesto"]
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {"versoes": []}


def versao_registrada(cfg, rotulo=None):
    rotulo = rotulo or cfg["dados"]["versao"]
    for v in ler_manifesto(cfg)["versoes"]:
        if v["versao"] == rotulo:
            return v
    return None


def registrar_versao_dados(cfg, rotulo, origem, observacao="", fontes_brutas=None):
    """Acrescenta uma versão do dataset ao manifesto, com hash e período."""
    arq = RAIZ / cfg["dados"]["arquivo"]
    df = pd.read_csv(arq, parse_dates=["data"], low_memory=False)
    manifesto = ler_manifesto(cfg)
    if any(v["versao"] == rotulo for v in manifesto["versoes"]):
        raise ValueError(f"A versão {rotulo} já existe no manifesto")
    dic = RAIZ / cfg["dados"]["dicionario"]
    manifesto.setdefault("descricao", "Versões do dataset integrado. O hash identifica o conteúdo exato de cada versão.")
    manifesto["versoes"].append({
        "versao": rotulo, "arquivo": cfg["dados"]["arquivo"], "sha256": sha256(arq),
        "linhas": len(df), "colunas": df.shape[1],
        "inicio": df["data"].min().date().isoformat(), "fim": df["data"].max().date().isoformat(),
        "dicionario_sha256": sha256(dic) if dic.exists() else None,
        "registrado_em": date.today().isoformat(), "origem": origem, "observacao": observacao,
        "fontes_brutas": fontes_brutas or [],
    })
    (RAIZ / cfg["dados"]["manifesto"]).write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifesto["versoes"][-1]


def carregar_dados(cfg):
    """Lê o dataset integrado e confere o hash com a versão do manifesto."""
    arq = RAIZ / cfg["dados"]["arquivo"]
    df = pd.read_csv(arq, parse_dates=["data"], low_memory=False)
    hash_arquivo = sha256(arq)
    registrada = versao_registrada(cfg)
    versao = {"versao": cfg["dados"]["versao"], "arquivo": cfg["dados"]["arquivo"], "sha256": hash_arquivo,
              "linhas": len(df), "colunas": df.shape[1],
              "inicio": df["data"].min().date().isoformat(), "fim": df["data"].max().date().isoformat(),
              "confere_com_manifesto": bool(registrada and registrada["sha256"] == hash_arquivo)}
    versao["rotulo"] = f"{versao['versao']}@{hash_arquivo[:12]}"
    return df, versao


def ler_dicionario(cfg):
    arq = RAIZ / cfg["dados"]["dicionario"]
    return pd.read_csv(arq) if arq.exists() else None


def validar_entrada(df, cfg, versao, dicionario):
    """Confere o arquivo. Devolve a tabela de verificações."""
    linhas = []

    def checar(nome, ok, detalhe, grave=False):
        linhas.append({"verificacao": nome, "resultado": "OK" if ok else ("ERRO" if grave else "ALERTA"), "detalhe": detalhe})

    checar("Hash do arquivo confere com o manifesto de dados", versao["confere_com_manifesto"],
           f"versão {versao['rotulo']}", grave=True)
    faltam = [c for c in COLUNAS_OBRIGATORIAS if c not in df]
    checar("Colunas obrigatórias presentes", not faltam,
           f"faltam {faltam}" if faltam else f"{len(COLUNAS_OBRIGATORIAS)} colunas", grave=True)
    dup = int(df["data"].duplicated().sum())
    checar("Uma linha por dia (sem datas repetidas)", dup == 0, f"{dup} datas repetidas", grave=True)
    esperado = pd.date_range(df["data"].min(), df["data"].max(), freq="D")
    lacunas = len(esperado.difference(df["data"]))
    checar("Calendário contínuo", lacunas == 0, f"{lacunas} dias ausentes no intervalo")
    alvo_nulo = int(df["carga_mwmed"].isna().sum())
    checar("Alvo preenchido", alvo_nulo == 0, f"{alvo_nulo} dias sem carga", grave=True)
    fora = int(((df["carga_mwmed"] < FAIXA_CARGA[0]) | (df["carga_mwmed"] > FAIXA_CARGA[1])).sum())
    checar("Carga em faixa plausível (3 a 30 mil MWmed)", fora == 0, f"{fora} dias fora da faixa")
    t = df["temp_media_sul"]
    checar("Temperatura em faixa plausível (-5 a 40 °C)", bool(t.dropna().between(*FAIXA_TEMPERATURA).all()),
           f"mín {t.min():.1f}, máx {t.max():.1f}")
    for nome, (ini, fim) in cfg["pipeline"]["janelas"].items():
        n = int(df["data"].between(ini, fim).sum())
        dias = len(pd.date_range(ini, fim))
        checar(f"Janela de {nome} coberta pelos dados", n == dias, f"{n} de {dias} dias", grave=True)
    checar("Dicionário de dados disponível", dicionario is not None,
           f"{len(dicionario)} campos descritos" if dicionario is not None else "sem dicionário")
    return pd.DataFrame(linhas)


def validar_variaveis(origens, dicionario):
    """Barreira contra vazamento pelo dicionário de dados."""
    campos = {} if dicionario is None else dict(zip(dicionario["campo"], dicionario["uso_no_modelo"].astype(str)))
    bloqueadas = []
    for col in sorted(set(origens)):
        if col in COLUNAS_SO_FILTRO:
            bloqueadas.append(f"{col} (só pode escolher dias de treino)")
            continue
        uso = campos.get(col)
        if uso is None:
            if col not in CALENDARIO_ETAPA2:
                bloqueadas.append(f"{col} (não está no dicionário)")
            continue
        u = uso.lower()
        permitida = u.startswith("preditor") or (u.startswith("conforme etapa 2") and col in CALENDARIO_ETAPA2)
        if not permitida:
            bloqueadas.append(f"{col} (uso no dicionário é {uso})")
    if bloqueadas:
        raise ValueError("Variáveis bloqueadas pela validação " + ", ".join(bloqueadas))
    return True


def preparar(df, cfg):
    """Ordena por dia e marca a janela de cada dia."""
    h = cfg["pipeline"]["horizonte_dias"]
    d = df.sort_values("data").set_index("data").asfreq("D")
    d["janela"] = "fora"
    for nome, (ini, fim) in cfg["pipeline"]["janelas"].items():
        d.loc[ini:fim, "janela"] = nome
    d["avaliavel"] = (d["flag_imputado"].fillna(0) == 0) & d["carga_mwmed"].notna()
    # dia mais antigo usado no histórico semanal
    alcance = int(np.ceil(h / 7) * 7) + 14
    regime = d["regime_metodologico"]
    d["historico_cruza_regime"] = (regime != regime.shift(alcance)).astype(int)
    return d
