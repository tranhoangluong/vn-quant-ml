from .baselines import MomentumRule, RidgeModel
from .lgbm import LGBMModel

_MODELS = {"lgbm": LGBMModel, "ridge": RidgeModel, "momentum_rule": MomentumRule}
# "mlp": thêm sau (giai đoạn 4, tùy chọn) trong models/mlp.py


def get_model(name: str, params: dict | None = None):
    return _MODELS[name](**(params or {}))
