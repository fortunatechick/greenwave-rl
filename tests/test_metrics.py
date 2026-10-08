"""Metric definitions on a hand-built tripinfo file."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from greenwave.metrics import episode_metrics, parse_tripinfo, summarise, welch_p

TRIPINFO = """<tripinfos>
  <tripinfo id="N-S-car-0.0" depart="0.00" arrival="60.00" waitingTime="10.00" timeLoss="20.00" departDelay="0.0">
    <emissions CO2_abs="100000.0"/>
  </tripinfo>
  <tripinfo id="N-E-bus-0.0" depart="5.00" arrival="90.00" waitingTime="30.00" timeLoss="40.00" departDelay="1.0">
    <emissions CO2_abs="500000.0"/>
  </tripinfo>
  <tripinfo id="E-W-tw-0.3" depart="9.00" arrival="-1" waitingTime="50.00" timeLoss="55.00" departDelay="0.0">
    <emissions CO2_abs="30000.0"/>
  </tripinfo>
  <tripinfo id="W-E-au-1.2" depart="12.00" arrival="70.00" waitingTime="0.00" timeLoss="4.00" departDelay="0.0">
    <emissions CO2_abs="70000.0"/>
  </tripinfo>
</tripinfos>
"""


@pytest.fixture()
def trips(tmp_path: Path) -> pd.DataFrame:
    path = tmp_path / "tripinfo.xml"
    path.write_text(TRIPINFO, encoding="utf-8")
    return parse_tripinfo(path)


def test_parse(trips: pd.DataFrame) -> None:
    assert list(trips["approach"]) == ["N", "N", "E", "W"]
    assert list(trips["cls"]) == [2, 3, 0, 1]  # car, bus, two_wheeler, auto_rickshaw


def test_metrics(trips: pd.DataFrame) -> None:
    m = episode_metrics(trips, {"seconds": 1800, "avg_queue": 7.5, "teleports": 1},
                        weights=np.array([1.5, 2.5, 2.0, 40.0]))  # fmt: skip
    assert m["veh_wait"] == pytest.approx(22.5)
    # (2*10 + 40*30 + 1.5*50 + 2.5*0) / (2 + 40 + 1.5 + 2.5)
    assert m["person_wait"] == pytest.approx(1295 / 46)
    assert m["throughput"] == pytest.approx(3 * 2)  # 3 arrivals in half an hour
    assert m["max_wait_N"] == 30 and m["max_wait_E"] == 50 and m["max_wait_S"] == 0
    assert m["max_wait"] == 50
    assert m["delay_bus"] == 40 and m["delay_car"] == 20
    assert m["co2"] == pytest.approx(175.0)  # mean 175 000 mg -> g
    assert m["avg_queue"] == 7.5
    assert m["teleport_pct"] == pytest.approx(25.0)


def test_summarise_and_welch() -> None:
    eps = pd.DataFrame({"controller": ["a"] * 3 + ["b"] * 3, "regime": ["peak"] * 6,
                        "seed": [0, 1, 2] * 2, "veh_wait": [10.0, 12.0, 14.0, 30.0, 31.0, 32.0]})  # fmt: skip
    s = summarise(eps, ["controller", "regime"]).set_index(["controller", "metric"])
    assert s.loc[("a", "veh_wait"), "mean"] == pytest.approx(12.0)
    assert s.loc[("a", "veh_wait"), "std"] == pytest.approx(2.0)
    assert s.loc[("b", "veh_wait"), "n"] == 3
    assert welch_p(eps["veh_wait"][:3], eps["veh_wait"][3:]) < 0.01
    assert np.isnan(welch_p(np.array([1.0]), np.array([2.0, 3.0])))
