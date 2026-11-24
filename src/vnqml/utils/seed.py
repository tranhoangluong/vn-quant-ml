import os
import random

import numpy as np


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)  # noqa: NPY002 (cho thư viện còn dùng global RNG)
    os.environ["PYTHONHASHSEED"] = str(seed)
