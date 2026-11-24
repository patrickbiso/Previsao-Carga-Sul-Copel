"""Gera previsões com o modelo que está em produção no registro.
"""
import argparse
import json

import mlflow
import pandas as pd

from .config import RAIZ, carregar_config
from .pipeline import montar_contexto
from .rastreio import iniciar_mlflow


def carregar_modelo(cfg, apelido="producao"):
    """Modelo e ficha da versão apontada pelo apelido no registro."""
    cliente = iniciar_mlflow(cfg)
    nome = cfg["projeto"]["modelo_registrado"]
    versao = cliente.get_model_version_by_alias(nome, apelido)
    modelo = mlflow.sklearn.load_model(f"models:/{nome}@{apelido}")
    ficha = json.loads((RAIZ / "resultados" / "modelo" / f"ficha_modelo_v{versao.version}.json").read_text(encoding="utf-8"))
    return modelo, ficha, versao


def prever(ctx, modelo, inicio, fim):
    """Previsão diária em MWmed. Dias sem todas as variáveis ficam vazios."""
    dias = ctx.prep.index[(ctx.prep.index >= inicio) & (ctx.prep.index <= fim)]
    X = ctx.X.loc[dias, modelo.variaveis + ["nivel_semana"]]
    completo = X.notna().all(axis=1)
    p = pd.Series(index=dias, dtype=float, name="previsto_mwmed")
    p[completo] = modelo.predict(X[completo])
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", required=True)
    ap.add_argument("--fim", required=True)
    args = ap.parse_args()
    cfg = carregar_config()
    ctx = montar_contexto(cfg)
    modelo, ficha, versao = carregar_modelo(cfg)
    p = prever(ctx, modelo, args.inicio, args.fim).round(1).to_frame()
    p["modelo_versao"] = versao.version
    p["versao_dados"] = ctx.versao_dados["rotulo"]
    saida = RAIZ / "resultados" / "previsoes"
    saida.mkdir(parents=True, exist_ok=True)
    arq = saida / f"previsao_{args.inicio}_{args.fim}.csv"
    p.to_csv(arq, index_label="data")
    print(f"{p['previsto_mwmed'].notna().sum()} dias previstos com a versão {versao.version}. Arquivo {arq.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
