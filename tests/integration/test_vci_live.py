"""Gọi API thật (cần mạng). Chạy: pytest -m integration"""

import pytest

pytestmark = pytest.mark.integration


def test_vci_ohlcv_live_and_delisted():
    from vnqml.data.sources import VCI

    vci = VCI()
    fpt = vci.ohlcv("FPT", "2024-01-01", "2024-03-31")
    assert len(fpt) > 50 and fpt["close"].gt(0).all()
    ros = vci.ohlcv("ROS", "2018-01-01", "2018-12-31")  # đã huỷ niêm yết 2022
    assert len(ros) > 200
