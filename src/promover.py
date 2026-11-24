"""Coloca uma versão do modelo em produção, com aprovação registrada.

Uso  python -m src.promover --versao candidato --aprovado-por "Nome" --motivo "primeira versão"
     python -m src.promover --versao 1 --revalidar --aprovado-por "Nome" --motivo "candidato sem ganho"
"""
import argparse
import csv
from datetime import datetime

from .config import RAIZ, carregar_config
from .rastreio import iniciar_mlflow

HISTORICO = RAIZ / "governanca" / "historico_modelo.csv"
CAMPOS = ["data", "acao", "versao", "aprovado_por", "motivo", "run_de_origem", "janela_treino", "versao_dados",
          "versao_codigo", "versao_config", "MAE_teste", "MAPE_teste", "sha256_arquivo", "versao_anterior"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versao", required=True)
    ap.add_argument("--aprovado-por", required=True)
    ap.add_argument("--motivo", default="")
    ap.add_argument("--revalidar", action="store_true", help="registra que a versão foi reavaliada e mantida")
    args = ap.parse_args()
    cfg = carregar_config()
    cliente = iniciar_mlflow(cfg)
    nome = cfg["projeto"]["modelo_registrado"]
    if args.versao == "candidato":
        args.versao = cliente.get_model_version_by_alias(nome, "candidato").version
    nova = cliente.get_model_version(nome, args.versao)
    try:
        anterior = cliente.get_model_version_by_alias(nome, "producao").version
    except Exception:
        anterior = ""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acao = "revalidado e mantido em produção" if args.revalidar else "promovido a produção"
    if args.revalidar:
        if str(anterior) != str(args.versao):
            raise SystemExit(f"A versão {args.versao} não é a que está em produção")
        cliente.set_model_version_tag(nome, args.versao, "revalidado_em", agora)
        cliente.set_model_version_tag(nome, args.versao, "revalidado_por", args.aprovado_por)
        anterior = ""
    else:
        promover(cliente, nome, args, anterior, agora)
    gravar_historico(nova.tags, args, acao, agora, anterior)
    print(f"Versão {args.versao} de {nome}, {acao}, por {args.aprovado_por}.")


def promover(cliente, nome, args, anterior, agora):
    if anterior and str(anterior) != str(args.versao):
        cliente.set_registered_model_alias(nome, "anterior", anterior)
        cliente.set_model_version_tag(nome, anterior, "situacao", f"substituída pela versão {args.versao} em {agora}")
    cliente.set_registered_model_alias(nome, "producao", args.versao)
    try:
        cliente.delete_registered_model_alias(nome, "candidato")
    except Exception:
        pass
    for k, v in {"situacao": "em produção", "aprovado_por": args.aprovado_por, "aprovado_em": agora, "motivo": args.motivo}.items():
        cliente.set_model_version_tag(nome, args.versao, k, v)


def gravar_historico(t, args, acao, agora, anterior):
    HISTORICO.parent.mkdir(exist_ok=True)
    novo_arquivo = not HISTORICO.exists()
    with open(HISTORICO, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo_arquivo:
            w.writeheader()
        w.writerow({"data": agora, "acao": acao, "versao": args.versao, "aprovado_por": args.aprovado_por,
                    "motivo": args.motivo, "run_de_origem": t.get("run_de_origem"), "janela_treino": t.get("janela_treino"),
                    "versao_dados": t.get("versao_dados"), "versao_codigo": t.get("versao_codigo"),
                    "versao_config": t.get("versao_config"), "MAE_teste": t.get("MAE_teste"), "MAPE_teste": t.get("MAPE_teste"),
                    "sha256_arquivo": t.get("sha256_arquivo"), "versao_anterior": anterior})


if __name__ == "__main__":
    main()
