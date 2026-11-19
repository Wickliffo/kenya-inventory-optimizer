from __future__ import annotations

import numpy as np
import pandas as pd

from src.core_models import fit_arima, optimize_replenishment


def test_arima_returns_nonnegative_forecast():
    index = pd.date_range("2021-01-01", periods=48, freq="MS")
    y = pd.Series(100 + np.arange(48) * 0.4 + 4 * np.sin(np.arange(48) / 2), index=index)
    result = fit_arima(y, horizon=3)
    assert len(result.forecast) == 3
    assert (result.forecast["p50"] >= 0).all()
    assert (result.forecast["p90"] >= result.forecast["p50"]).all()


def test_cvxpy_plan_respects_budget_capacity_supplier_and_multiple():
    planning = pd.DataFrame([
        {"sku_id": "A", "location_id": "Nairobi", "p50_demand": 50, "p90_demand": 80, "inventory_position": 10, "unit_cost_ksh": 100, "storage_capacity": 120, "supplier_capacity": 60, "order_multiple": 10, "holding_cost_ksh": 1, "shortage_penalty_ksh": 500},
        {"sku_id": "B", "location_id": "Eldoret", "p50_demand": 20, "p90_demand": 40, "inventory_position": 5, "unit_cost_ksh": 200, "storage_capacity": 80, "supplier_capacity": 20, "order_multiple": 5, "holding_cost_ksh": 1, "shortage_penalty_ksh": 300},
    ])
    result = optimize_replenishment(planning, budget_ksh=5000)
    assert result.status in {"OPTIMAL", "OPTIMAL_INACCURATE", "FALLBACK_RULE_BASED"}
    plan = result.order_plan
    assert float((plan["order_qty"] * plan["unit_cost_ksh"]).sum()) <= 5000.01
    assert (plan["order_qty"] <= plan["supplier_capacity"] + 1e-6).all()
    assert (plan["inventory_position"] + plan["order_qty"] <= plan["storage_capacity"] + 1e-6).all()
    assert all(abs(q / m - round(q / m)) < 1e-6 for q, m in zip(plan["order_qty"], plan["order_multiple"]))
