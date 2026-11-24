"""Ligação com o MLflow. Tudo que identifica uma execução passa por aqui."""
import platform
import shutil
from pathlib import Path

import mlflow

from .config import RAIZ, commit_git, versao_codigo


def iniciar_mlflow(cfg, experimento=None):
    """Aponta para o banco local e garante que o experimento existe."""
    uri = cfg["projeto"]["mlflow_uri"]
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        uri = f"sqlite:///{RAIZ / uri[len('sqlite:///'):]}"
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    nome = experimento or cfg["projeto"]["experimento"]
    if mlflow.get_experiment_by_name(nome) is None:
        pasta = RAIZ / cfg["projeto"]["pasta_artefatos"]
        pasta.mkdir(exist_ok=True)
        mlflow.create_experiment(nome, artifact_location=pasta.resolve().as_uri())
    mlflow.set_experiment(nome)
    return mlflow.tracking.MlflowClient()


def ambiente():
    import numpy, pandas, prophet, sklearn
    return {"python": platform.python_version(), "pandas": pandas.__version__, "numpy": numpy.__version__,
            "scikit-learn": sklearn.__version__, "prophet": prophet.__version__, "mlflow": mlflow.__version__}


def etiquetas_de_versao(cfg, versao_dados):
    """Versões de dados, código e configuração que acompanham cada run."""
    tags = {"versao_dados": versao_dados["rotulo"], "sha256_dados": versao_dados["sha256"],
            "versao_codigo": versao_codigo(), "versao_config": cfg["_hash"]}
    commit = commit_git()
    if commit:
        tags["commit_git"] = commit
    return tags


def requisitos():
    arq = RAIZ / "requirements.txt"
    linhas = [l.strip() for l in arq.read_text().splitlines()] if arq.exists() else []
    return [l for l in linhas if l and not l.startswith("#")]


def pasta_temporaria(nome):
    p = RAIZ / "resultados" / "_tmp" / nome
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


def limpar_temporarios():
    shutil.rmtree(RAIZ / "resultados" / "_tmp", ignore_errors=True)


def parametros_planos(d, prefixo=""):
    """Achata dicionários para o formato de parâmetros do MLflow."""
    saida = {}
    for k, v in d.items():
        chave = f"{prefixo}{k}"
        if isinstance(v, dict):
            saida.update(parametros_planos(v, chave + "."))
        else:
            saida[chave] = v if isinstance(v, (int, float, str, bool)) or v is None else str(v)
    return saida
