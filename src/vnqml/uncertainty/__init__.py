from .conformal import ACI, DtACI, NoCalibrator, SplitConformal


def get_calibrator(ucfg: dict):
    m = ucfg.get("method", "none")
    a = ucfg.get("alpha", 0.1)
    if m == "none":
        return NoCalibrator()
    if m == "split":
        return SplitConformal(alpha=a)
    if m == "aci":
        return ACI(alpha=a, gamma=ucfg.get("gamma", 0.005))
    if m == "dtaci":
        return DtACI(alpha=a, gammas=ucfg.get("gammas", [0.001, 0.005, 0.01, 0.05]))
    raise ValueError(m)


__all__ = ["ACI", "DtACI", "NoCalibrator", "SplitConformal", "get_calibrator"]
