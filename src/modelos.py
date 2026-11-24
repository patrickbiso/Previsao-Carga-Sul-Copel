"""Algoritmos disponíveis e o modelo que sempre devolve a carga em MWmed."""
import logging

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression



def silenciar_prophet():
    """O Prophet escreve uma linha por ajuste. Aqui só passam os erros."""
    for nome in ("cmdstanpy", "prophet"):
        logging.getLogger(nome).setLevel(logging.ERROR)
    logging.getLogger("prophet.plot").setLevel(logging.CRITICAL)


class ReferenciaSazonal:
    """Repete a carga do mesmo dia da semana anterior."""
    def __init__(self, coluna="carga_sem1"):
        self.coluna = coluna

    def fit(self, X, y):
        return self

    def predict(self, X):
        return X[self.coluna].to_numpy()

    def get_params(self, deep=False):
        return {"coluna": self.coluna}


class ProphetRegressor:
    """Prophet com a interface do scikit-learn."""
    def __init__(self, sazonalidade="multiplicative", changepoint_prior_scale=0.05, feriados=None):
        self.sazonalidade, self.changepoint_prior_scale, self.feriados = sazonalidade, changepoint_prior_scale, feriados

    def get_params(self, deep=False):
        n = 0 if self.feriados is None else self.feriados["holiday"].nunique()
        return {"sazonalidade": self.sazonalidade, "changepoint_prior_scale": self.changepoint_prior_scale,
                "feriados": f"{n} tipos, janela -1 a +1 dia"}

    def _tabela(self, X):
        df = pd.DataFrame({"ds": X.index})
        for c in X.columns:
            df[c] = X[c].to_numpy()
        return df

    def fit(self, X, y):
        silenciar_prophet()
        import cmdstanpy  # noqa: F401
        from prophet import Prophet
        silenciar_prophet()
        self.colunas = list(X.columns)
        self.m = Prophet(holidays=self.feriados, seasonality_mode=self.sazonalidade,
                         changepoint_prior_scale=self.changepoint_prior_scale,
                         yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        for c in self.colunas:
            self.m.add_regressor(c)
        self.m.fit(self._tabela(X).assign(y=np.asarray(y)))
        return self

    def componentes(self, X):
        return self.m.predict(self._tabela(X[self.colunas])).set_index("ds")

    def predict(self, X):
        return self.componentes(X)["yhat"].to_numpy()


ALGORITMOS = {
    "Referência sazonal": ReferenciaSazonal,
    "Regressão Linear": LinearRegression,
    "Random Forest": RandomForestRegressor,
    "Gradient Boosting": HistGradientBoostingRegressor,
    "Prophet": ProphetRegressor,
}
COMPLEXIDADE = {"Referência sazonal": 0, "Regressão Linear": 1, "Random Forest": 2, "Gradient Boosting": 2, "Prophet": 2}


def criar_estimador(algoritmo, parametros, semente, feriados=None):
    params = dict(parametros)
    if algoritmo in ("Random Forest", "Gradient Boosting"):
        params.setdefault("random_state", semente)
    if algoritmo == "Prophet":
        return ALGORITMOS[algoritmo](feriados=feriados, **params), params
    return ALGORITMOS[algoritmo](**params), params


class ModeloCarga(BaseEstimator, RegressorMixin):
    """Recebe as variáveis e devolve a carga em MWmed, seja o alvo absoluto ou relativo."""
    def __init__(self, estimador=None, variaveis=None, alvo="nivel"):
        self.estimador, self.variaveis, self.alvo = estimador, variaveis, alvo

    def _entrada(self, X):
        return X[self.variaveis]

    def fit(self, X, carga):
        y = carga / X["nivel_semana"] if self.alvo == "razao" else carga
        self.estimador.fit(self._entrada(X), y)
        return self

    def predict(self, X):
        p = np.asarray(self.estimador.predict(self._entrada(X)), dtype=float)
        return p * X["nivel_semana"].to_numpy() if self.alvo == "razao" else p
