"""Mostra e registra as versões de código, dados, configuração e modelo.
"""
import argparse
import json

import pandas as pd

from .config import RAIZ, carregar_config, commit_git, sha256, versao_codigo
from .dados import carregar_dados, ler_manifesto, registrar_versao_dados


def fontes_brutas():
    """Arquivos baixados na integração, com o hash de cada um."""
    arq = RAIZ / "dados" / "documentacao" / "etapa3_integracao" / "registro_downloads_etapa3.csv"
    if not arq.exists():
        return []
    d = pd.read_csv(arq)
    cols = [c for c in ("fonte", "arquivo", "sha256", "tamanho_bytes", "data_obtencao", "url") if c in d]
    return json.loads(d[cols].to_json(orient="records", force_ascii=False))


def mostrar(cfg):
    _, v = carregar_dados(cfg)
    print("CÓDIGO")
    print("  hash de src         ", versao_codigo())
    print("  commit do Git       ", commit_git() or "fora de um repositório Git")
    print("CONFIGURAÇÃO")
    print("  hash de config.yaml ", cfg["_hash"])
    print("DADOS")
    print("  versão em uso       ", v["rotulo"], f"({v['linhas']} linhas, {v['inicio']} a {v['fim']})")
    print("  confere com manifesto", "sim" if v["confere_com_manifesto"] else "NÃO")
    for m in ler_manifesto(cfg)["versoes"]:
        print(f"  manifesto {m['versao']}  sha256 {m['sha256'][:12]}  registrado em {m['registrado_em']}")
    print("MODELO")
    hist = RAIZ / "governanca" / "historico_modelo.csv"
    if hist.exists():
        print(pd.read_csv(hist).tail(5).to_string(index=False))
    else:
        print("  nenhum modelo promovido ainda")
    for arq in sorted((RAIZ / "resultados" / "modelo").glob("modelo_v*.joblib")):
        print(f"  {arq.name}  sha256 {sha256(arq)[:12]}")


def main():
    cfg = carregar_config()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="comando")
    r = sub.add_parser("registrar-dados")
    r.add_argument("rotulo")
    r.add_argument("--origem", required=True)
    r.add_argument("--observacao", default="")
    args = ap.parse_args()
    if args.comando == "registrar-dados":
        v = registrar_versao_dados(cfg, args.rotulo, args.origem, args.observacao, fontes_brutas())
        print(f"Versão {v['versao']} registrada com sha256 {v['sha256'][:12]}. Atualize dados.versao em config.yaml.")
    else:
        mostrar(cfg)


if __name__ == "__main__":
    main()
