"""Leitura da configuração e identificação das versões de código e de configuração."""
import hashlib
import subprocess
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
ARQ_CONFIG = RAIZ / "config" / "config.yaml"


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_config(caminho=ARQ_CONFIG):
    """Lê o YAML e anexa o hash do arquivo."""
    caminho = Path(caminho)
    cfg = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    cfg["_hash"] = sha256(caminho)[:12]
    cfg["_arquivo"] = str(caminho)
    return cfg


def versao_codigo():
    """Hash dos arquivos de src, igual em qualquer máquina com o mesmo código."""
    h = hashlib.sha256()
    for arq in sorted((RAIZ / "src").glob("*.py")):
        h.update(arq.name.encode())
        h.update(arq.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def commit_git():
    """Commit atual, quando o código está em um repositório Git."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return None
        sujo = subprocess.run(["git", "status", "--porcelain", "src", "config"], cwd=RAIZ, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() + ("+alterado" if sujo.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None
