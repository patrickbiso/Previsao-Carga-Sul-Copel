"""Roda o plano de experimentos com registro no MLflow e registra o modelo final como candidato.
"""
import argparse
import json
from datetime import datetime

import joblib
import mlflow
import pandas as pd
from mlflow.models import infer_signature

from .config import RAIZ, carregar_config, sha256
from .pipeline import escolher_run, executar_run, montar_contexto
from .rastreio import (ambiente, etiquetas_de_versao, iniciar_mlflow, limpar_temporarios, parametros_planos,
                       pasta_temporaria, requisitos)

SAIDA = RAIZ / "resultados" / "experimentos"
METRICAS = ("MAE_", "RMSE_", "MAPE_", "vies_", "erro_max_", "ganho_", "dias_", "tempo_treino_s", "n_ajustes", "n_variaveis")


def registrar_run(ctx, linha, modelo, previsoes, tags, tipo):
    """Grava parâmetros, métricas, modelo e artefatos da run aberta no MLflow."""
    mlflow.set_tags({**tags, "tipo": tipo, "elegivel_escolha": str(linha["elegivel_escolha"]),
                     "observacao": linha["observacao"], "mlflow.note.content": linha["descricao"]})
    mlflow.log_params({"algoritmo": linha["modelo"], "alvo": linha["alvo"], "grupos_variaveis": linha["grupos_variaveis"],
                       "fontes_externas": linha["fontes_externas"], "janela_treino": linha["janela_treino"],
                       "excluidos_do_treino": linha["excluidos_do_treino"], "retreino": linha["retreino"],
                       "horizonte_dias": linha["horizonte_dias"], "semente": linha["semente"]})
    mlflow.log_params(parametros_planos(json.loads(linha["parametros"]), "modelo."))
    mlflow.log_metrics({k: float(v) for k, v in linha.items()
                        if k.startswith(METRICAS) and isinstance(v, (int, float)) and pd.notna(v)})
    tmp = pasta_temporaria(linha["run"])
    tab = pd.concat([pd.DataFrame({"janela": j, "real": ctx.carga[p.index], "previsto": p}) for j, p in previsoes.items()])
    tab.round(2).to_csv(tmp / "previsoes.csv", index_label="data")
    (tmp / "variaveis.json").write_text(json.dumps(modelo.variaveis, indent=1, ensure_ascii=False), encoding="utf-8")
    mlflow.log_artifact(tmp / "previsoes.csv")
    mlflow.log_artifact(tmp / "variaveis.json")
    try:
        joblib.dump(modelo, tmp / "modelo.joblib", compress=3)
        mlflow.log_artifact(tmp / "modelo.joblib", artifact_path="modelo_joblib")
    except Exception:
        # o Prophet tem formato próprio
        from prophet.serialize import model_to_json
        (tmp / "modelo_prophet.json").write_text(model_to_json(modelo.estimador.m))
        mlflow.log_artifact(tmp / "modelo_prophet.json", artifact_path="modelo_joblib")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="", help="lista de runs separadas por vírgula, vazio roda o plano inteiro")
    args = ap.parse_args()
    cfg = carregar_config()
    if args.runs:
        pedidas = set(args.runs.split(",")) | {"R01"}
        cfg["runs"] = [r for r in cfg["runs"] if r["id"] in pedidas]
    ctx = montar_contexto(cfg)
    cliente = iniciar_mlflow(cfg)
    agora = datetime.now()
    id_execucao = agora.strftime("%Y%m%d_%H%M%S")
    tags = etiquetas_de_versao(cfg, ctx.versao_dados)
    SAIDA.mkdir(parents=True, exist_ok=True)
    print(f"Execução {id_execucao} | dados {ctx.versao_dados['rotulo']} | código {tags['versao_codigo']} | config {cfg['_hash']}")

    registro, modelos, previsoes = [], {}, {}
    with mlflow.start_run(run_name=f"treino_{id_execucao}") as pai:
        mlflow.set_tags({**tags, "tipo": "execucao", "id_execucao": id_execucao})
        mlflow.log_params(parametros_planos(cfg["pipeline"], "pipeline."))
        mlflow.log_params(parametros_planos(ambiente(), "ambiente."))
        tmp = pasta_temporaria("execucao")
        ctx.validacao.to_csv(tmp / "validacao_entrada.csv", index=False)
        for arq in (cfg["_arquivo"], RAIZ / cfg["dados"]["manifesto"], RAIZ / "requirements.txt", tmp / "validacao_entrada.csv"):
            mlflow.log_artifact(str(arq), artifact_path="configuracao")

        for run in cfg["runs"]:
            with mlflow.start_run(run_name=run["id"], nested=True) as filha:
                linha, modelo, prev = executar_run(ctx, run)
                ref = next((r for r in registro if r["run"] == "R01"), None)
                for janela in ("validacao", "teste"):
                    if ref:
                        linha[f"ganho_vs_ref_{janela}_pct"] = (1 - linha[f"MAE_{janela}"] / ref[f"MAE_{janela}"]) * 100
                linha.update({"id_execucao": id_execucao, "data_execucao": agora.strftime("%Y-%m-%d %H:%M:%S"),
                              "versao_dados": ctx.versao_dados["rotulo"], "versao_codigo": tags["versao_codigo"],
                              "versao_config": cfg["_hash"], "mlflow_run_id": filha.info.run_id})
                registrar_run(ctx, linha, modelo, prev, tags, "experimento")
                registro.append(linha); modelos[run["id"]] = modelo; previsoes[run["id"]] = prev
                print(f"{run['id']} {run['descricao']}  MAE validação {linha['MAE_validacao']:,.1f}  teste {linha['MAE_teste']:,.1f}")

        escolhida, empatados = escolher_run(registro, cfg)
        run_final = next(r for r in cfg["runs"] if r["id"] == escolhida)
        mlflow.set_tag("run_escolhida", escolhida)
        (tmp / "escolha.json").write_text(json.dumps({
            "regra": "menor MAE de validação, empate até a tolerância vai para menos fontes e depois o modelo mais simples",
            "tolerancia_empate": cfg["pipeline"]["tolerancia_empate"], "escolhida": escolhida,
            "empatados": empatados.round(2).to_dict("records")}, indent=1, ensure_ascii=False), encoding="utf-8")
        mlflow.log_artifact(tmp / "escolha.json", artifact_path="configuracao")
        print(f"Escolhida {escolhida} ({run_final['descricao']})")

        with mlflow.start_run(run_name="FINAL", nested=True) as filha:
            run_f = {**run_final, "id": "FINAL", "descricao": f"{run_final['descricao']} (treino 2017-2024)"}
            linha, modelo, prev = executar_run(ctx, run_f, treino=("treino", "validacao"), avaliar=("teste",))
            ref = registro[0]
            linha["ganho_vs_ref_teste_pct"] = (1 - linha["MAE_teste"] / ref["MAE_teste"]) * 100
            linha.update({"id_execucao": id_execucao, "data_execucao": agora.strftime("%Y-%m-%d %H:%M:%S"),
                          "versao_dados": ctx.versao_dados["rotulo"], "versao_codigo": tags["versao_codigo"],
                          "versao_config": cfg["_hash"], "mlflow_run_id": filha.info.run_id})
            registrar_run(ctx, linha, modelo, prev, tags, "final")
            mlflow.set_tag("run_de_origem", escolhida)
            exemplo = ctx.X.loc[prev["teste"].index[:5], modelo.variaveis + ["nivel_semana"]].astype(float)
            info = mlflow.sklearn.log_model(
                modelo, name="modelo", signature=infer_signature(exemplo, modelo.predict(exemplo)), input_example=exemplo,
                registered_model_name=cfg["projeto"]["modelo_registrado"], pip_requirements=requisitos(),
                code_paths=[str(RAIZ / "src")], skops_trusted_types=["src.modelos.ModeloCarga"])
            versao = str(info.registered_model_version)
            nome = cfg["projeto"]["modelo_registrado"]
            arq_modelo = SAIDA.parent / "modelo" / f"modelo_v{versao}.joblib"
            arq_modelo.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(modelo, arq_modelo, compress=3)
            ficha = {
                "modelo_registrado": nome, "versao": versao, "run_de_origem": escolhida, "mlflow_run_id": filha.info.run_id,
                "algoritmo": linha["modelo"], "alvo": linha["alvo"], "variaveis": modelo.variaveis,
                "janela_treino": linha["janela_treino"], "dias_treino": linha["dias_treino"],
                "excluidos_do_treino": json.loads(linha["excluidos_do_treino"]),
                "versao_dados": ctx.versao_dados["rotulo"], "versao_codigo": tags["versao_codigo"],
                "versao_config": cfg["_hash"], "commit_git": tags.get("commit_git"),
                "treinado_em": agora.strftime("%Y-%m-%d %H:%M:%S"), "arquivo": arq_modelo.name,
                "sha256_arquivo": sha256(arq_modelo),
                "teste": {k: round(float(linha[k]), 2) for k in ("MAE_teste", "RMSE_teste", "MAPE_teste", "vies_teste", "MAE_pico_teste")},
                "referencia_teste": {"MAE_teste": round(float(ref["MAE_teste"]), 2), "MAPE_teste": round(float(ref["MAPE_teste"]), 2),
                                     "MAE_pico_teste": round(float(ref["MAE_pico_teste"]), 2)},
            }
            (arq_modelo.parent / f"ficha_modelo_v{versao}.json").write_text(json.dumps(ficha, indent=1, ensure_ascii=False), encoding="utf-8")
            mlflow.log_artifact(arq_modelo.parent / f"ficha_modelo_v{versao}.json")
            cliente.set_registered_model_alias(nome, "candidato", versao)
            for k, v in {**tags, "run_de_origem": escolhida, "janela_treino": linha["janela_treino"],
                         "MAE_teste": f"{linha['MAE_teste']:.1f}", "MAPE_teste": f"{linha['MAPE_teste']:.2f}",
                         "sha256_arquivo": ficha["sha256_arquivo"][:12], "situacao": "candidato, aguarda aprovação"}.items():
                cliente.set_model_version_tag(nome, versao, k, v)
            cliente.update_model_version(nome, versao, description=(
                f"{linha['descricao']}. Previsão da carga diária do Sul (MWmed) com 7 dias de antecedência. "
                f"Teste 2025 com MAE de {linha['MAE_teste']:.0f} MWmed e MAPE de {linha['MAPE_teste']:.2f}%."))
            registro.append(linha); previsoes["FINAL"] = prev

        reg = pd.DataFrame(registro)
        reg.round(4).to_csv(SAIDA / "registro_experimentos.csv", index=False)
        mlflow.log_artifact(SAIDA / "registro_experimentos.csv")

    tab = pd.DataFrame({"real": ctx.carga[previsoes["R01"]["teste"].index]})
    for rid, prev in previsoes.items():
        tab[rid] = prev["teste"]
    tab.round(1).to_csv(SAIDA / "previsoes_teste.csv", index_label="data")
    ctx.validacao.to_csv(SAIDA / "validacao_entrada.csv", index=False)
    exportar_mlflow(cfg)
    limpar_temporarios()
    f = registro[-1]
    print(f"Modelo {nome} versão {versao} registrado como candidato. Teste 2025 com MAE de {f['MAE_teste']:,.0f} MWmed "
          f"({f['MAPE_teste']:.2f}%), referência com {registro[0]['MAE_teste']:,.0f}.")
    print("Para colocar em produção, rode  python -m src.promover --versao", versao, '--aprovado-por "Nome"')


def exportar_mlflow(cfg):
    """Exporta o que está no MLflow para CSV, para o histórico ficar legível no repositório."""
    exp = mlflow.get_experiment_by_name(cfg["projeto"]["experimento"])
    runs = mlflow.search_runs([exp.experiment_id], order_by=["attributes.start_time ASC"])
    manter = [c for c in runs.columns if c.startswith(("params.", "metrics.", "tags."))
              and not c.startswith(("tags.mlflow.source", "tags.mlflow.user", "tags.mlflow.log-model", "params.ambiente"))]
    saida = runs[["run_id", "start_time", "status"] + sorted(manter)].copy()
    saida["start_time"] = pd.to_datetime(saida["start_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    saida.to_csv(SAIDA / "runs_mlflow.csv", index=False)


if __name__ == "__main__":
    main()
