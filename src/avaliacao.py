"""Métricas de erro usadas em todas as runs e no monitoramento."""
import numpy as np
import pandas as pd


def metricas(real, prev, prefixo, percentil_pico=0.90):
    real, prev = pd.Series(real), pd.Series(np.asarray(prev), index=pd.Series(real).index)
    erro = prev - real
    pico = real >= real.quantile(percentil_pico)
    return {
        f"MAE_{prefixo}": erro.abs().mean(),
        f"RMSE_{prefixo}": np.sqrt((erro ** 2).mean()),
        f"MAPE_{prefixo}": (erro.abs() / real).mean() * 100,
        f"vies_{prefixo}": erro.mean(),
        f"MAE_pico_{prefixo}": erro[pico].abs().mean(),
        f"erro_max_{prefixo}": erro.abs().max(),
    }
