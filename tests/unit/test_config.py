from vnqml.config import load_config


def test_inherit_overrides_only_changed_keys():
    c = load_config("configs/experiments/E05_no_frictions.yaml")
    assert c["market"]["fee_buy"] == 0.0
    assert c["market"]["allow_short"] is False  # kế thừa từ base
    assert c["model"]["name"] == "lgbm"
