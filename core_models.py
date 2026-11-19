from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cvxpy as cp
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


@dataclass
class ForecastResult:
    model: str
    target: str
    horizon: int
    forecast: pd.DataFrame
    diagnostics: dict[str, Any]


@dataclass
class OptimizationResult:
    status: str
    solver: str
    objective_value: float | None
    order_plan: pd.DataFrame
    constraints: dict[str, Any]
    message: str


def monthly_price_series(
    prices: pd.DataFrame,
    market: str,
    target_commodity: str,
    exogenous_commodities: list[str] | None = None,
    price_type: str = "Retail",
) -> pd.DataFrame:
    """Build a monthly aligned public market-price frame.

    This is a real-data modeling utility. Its target is market price, not company
    demand. For production demand forecasting, replace the target with employer
    sell-through and pass known future promotions/calendar regressors.
    """
    exogenous_commodities = exogenous_commodities or []
    keep = [target_commodity, *exogenous_commodities]
    work = prices.loc[
        (prices["market"] == market)
        & (prices["pricetype"] == price_type)
        & prices["commodity"].isin(keep),
        ["date", "commodity", "price"],
    ].copy()
    if work.empty:
        raise ValueError(f"No rows found for market={market!r}, price_type={price_type!r}, commodities={keep!r}")
    work["date"] = pd.to_datetime(work["date"])
    work["price"] = pd.to_numeric(work["price"], errors="coerce")
    work = work.dropna(subset=["date", "price"])
    work["month"] = work["date"].dt.to_period("M").dt.to_timestamp()
    pivot = work.pivot_table(index="month", columns="commodity", values="price", aggfunc="median")
    required = [target_commodity, *exogenous_commodities]
    missing = [col for col in required if col not in pivot.columns]
    if missing:
        raise ValueError(f"Missing aligned commodities in {market}: {missing}")
    aligned = pivot[required].sort_index()
    regular_index = pd.date_range(aligned.index.min(), aligned.index.max(), freq="MS")
    aligned = aligned.reindex(regular_index).interpolate(method="time").ffill().bfill()
    return aligned.rename(columns={target_commodity: "y", **{col: f"x_{i}" for i, col in enumerate(exogenous_commodities)}})


def _future_frame(index: pd.DatetimeIndex, values: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"date": index, "p50": np.maximum(values, 0.0), "p90": np.maximum(upper, values), "lower_80": lower})


def _future_index(index: pd.Index, horizon: int) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(index)
    inferred = dates.freqstr if dates.freq is not None else pd.infer_freq(dates)
    frequency = getattr(inferred, "freqstr", inferred) or "D"
    return pd.date_range(dates[-1], periods=horizon + 1, freq=frequency)[1:]


def fit_arima(y: pd.Series, horizon: int, order: tuple[int, int, int] = (1, 1, 1), seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 12)) -> ForecastResult:
    y = pd.Series(y).astype(float).dropna().sort_index()
    if len(y) < max(24, seasonal_order[-1] * 2):
        raise ValueError(f"ARIMA requires at least {max(24, seasonal_order[-1] * 2)} observations; received {len(y)}")
    model = SARIMAX(y, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit(disp=False)
    prediction = fitted.get_forecast(steps=horizon)
    mean = np.asarray(prediction.predicted_mean, dtype=float)
    interval = prediction.conf_int(alpha=0.20)
    future_index = _future_index(y.index, horizon)
    frame = _future_frame(future_index, mean, np.asarray(interval.iloc[:, 0]), np.asarray(interval.iloc[:, 1]))
    return ForecastResult("ARIMA", "price_or_demand", horizon, frame, {"aic": float(fitted.aic), "n_obs": int(len(y)), "order": order, "seasonal_order": seasonal_order})


def fit_arimax(
    y: pd.Series,
    exog_train: pd.DataFrame,
    exog_future: pd.DataFrame,
    horizon: int,
    order: tuple[int, int, int] = (1, 1, 1),
    seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 12),
) -> ForecastResult:
    y = pd.Series(y).astype(float).sort_index()
    exog_train = exog_train.astype(float).reindex(y.index)
    exog_future = exog_future.astype(float).iloc[:horizon]
    if len(y) < max(24, seasonal_order[-1] * 2):
        raise ValueError(f"ARIMAX requires at least {max(24, seasonal_order[-1] * 2)} observations; received {len(y)}")
    if len(exog_future) != horizon:
        raise ValueError("exog_future must have exactly horizon rows")
    if exog_train.isna().any().any() or exog_future.isna().any().any():
        raise ValueError("ARIMAX exogenous matrices cannot contain missing values")
    model = SARIMAX(y, exog=exog_train, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit(disp=False)
    prediction = fitted.get_forecast(steps=horizon, exog=exog_future)
    mean = np.asarray(prediction.predicted_mean, dtype=float)
    interval = prediction.conf_int(alpha=0.20)
    future_index = _future_index(y.index, horizon)
    frame = _future_frame(future_index, mean, np.asarray(interval.iloc[:, 0]), np.asarray(interval.iloc[:, 1]))
    return ForecastResult("ARIMAX", "price_or_demand", horizon, frame, {"aic": float(fitted.aic), "n_obs": int(len(y)), "exogenous": list(exog_train.columns), "order": order, "seasonal_order": seasonal_order})


def wape(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    denominator = np.abs(actual).sum()
    return float(np.abs(actual - predicted).sum() / denominator * 100) if denominator else float("nan")


def optimize_replenishment(
    planning_input: pd.DataFrame,
    budget_ksh: float,
    enforce_order_multiples: bool = True,
    solver: str | None = None,
) -> OptimizationResult:
    """Solve the replenishment LP/MILP from demand forecasts and constraints.

    Required columns:
    sku_id, location_id, p50_demand, p90_demand, inventory_position,
    unit_cost_ksh, storage_capacity, supplier_capacity, order_multiple,
    holding_cost_ksh, shortage_penalty_ksh.
    """
    required = {"sku_id", "location_id", "p50_demand", "p90_demand", "inventory_position", "unit_cost_ksh", "storage_capacity", "supplier_capacity", "order_multiple", "holding_cost_ksh", "shortage_penalty_ksh"}
    missing = sorted(required - set(planning_input.columns))
    if missing:
        raise ValueError(f"CVXPY input missing required columns: {missing}")
    work = planning_input.reset_index(drop=True).copy()
    n = len(work)
    if n == 0:
        raise ValueError("CVXPY input has no planning lines")
    costs = work["unit_cost_ksh"].to_numpy(float)
    inventory = work["inventory_position"].to_numpy(float)
    p50 = work["p50_demand"].to_numpy(float)
    p90 = work["p90_demand"].to_numpy(float)
    capacity = work["storage_capacity"].to_numpy(float)
    supplier = work["supplier_capacity"].to_numpy(float)
    multiples = np.maximum(work["order_multiple"].to_numpy(int), 1)
    holding = work["holding_cost_ksh"].to_numpy(float)
    shortage_penalty = work["shortage_penalty_ksh"].to_numpy(float)
    if np.any(costs < 0) or np.any(capacity < inventory) or np.any(supplier < 0):
        raise ValueError("Invalid optimization inputs: costs must be non-negative, capacity must cover current inventory, and supplier capacity cannot be negative")

    use_integer = enforce_order_multiples and "HIGHS" in cp.installed_solvers()
    if use_integer:
        batches = cp.Variable(n, integer=True, nonneg=True)
        order = cp.multiply(multiples, batches)
        chosen_solver = solver or "HIGHS"
    else:
        order = cp.Variable(n, nonneg=True)
        chosen_solver = solver or ("CLARABEL" if "CLARABEL" in cp.installed_solvers() else None)
    shortage = cp.Variable(n, nonneg=True)
    ending = inventory + order - p50
    constraints = [
        ending >= 0,
        shortage >= p90 - inventory - order,
        order <= supplier,
        inventory + order <= capacity,
        cp.sum(cp.multiply(costs, order)) <= budget_ksh,
    ]
    objective = cp.Minimize(cp.sum(cp.multiply(costs, order)) + cp.sum(cp.multiply(holding, ending)) + cp.sum(cp.multiply(shortage_penalty, shortage)))
    problem = cp.Problem(objective, constraints)
    try:
        problem.solve(solver=chosen_solver, verbose=False)
    except Exception as exc:
        return _greedy_fallback(work, budget_ksh, f"CVXPY solver error: {type(exc).__name__}")
    if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE} or order.value is None:
        return _greedy_fallback(work, budget_ksh, f"CVXPY status {problem.status}; deterministic fallback used")
    work["order_qty"] = np.maximum(np.asarray(order.value).round(6), 0.0)
    work["ending_inventory"] = np.maximum(inventory + work["order_qty"] - p50, 0.0)
    work["shortage_units"] = np.maximum(p90 - inventory - work["order_qty"], 0.0)
    work["spend_ksh"] = work["order_qty"] * costs
    status = "OPTIMAL" if problem.status == cp.OPTIMAL else "OPTIMAL_INACCURATE"
    return OptimizationResult(status, chosen_solver or "default", float(problem.value) if problem.value is not None else None, work, {"budget_ksh": budget_ksh, "integer_order_multiples": use_integer, "total_spend_ksh": float(work["spend_ksh"].sum()), "total_shortage_units": float(work["shortage_units"].sum())}, "CVXPY solved the constrained replenishment problem.")


def _greedy_fallback(work: pd.DataFrame, budget_ksh: float, message: str) -> OptimizationResult:
    result = work.copy()
    result["raw_need"] = np.maximum(0, result["p90_demand"] - result["inventory_position"])
    result["priority"] = result["raw_need"] * result["shortage_penalty_ksh"] / result["unit_cost_ksh"].clip(lower=0.01)
    remaining = float(budget_ksh)
    orders: list[float] = []
    for _, row in result.sort_values("priority", ascending=False).iterrows():
        multiple = max(int(row["order_multiple"]), 1)
        max_units = min(max(0, row["storage_capacity"] - row["inventory_position"]), row["supplier_capacity"], remaining / max(row["unit_cost_ksh"], 0.01))
        order = np.floor(max_units / multiple) * multiple
        orders.append(float(order))
        remaining -= float(order) * float(row["unit_cost_ksh"])
    result["order_qty"] = orders
    result["ending_inventory"] = np.maximum(result["inventory_position"] + result["order_qty"] - result["p50_demand"], 0)
    result["shortage_units"] = np.maximum(result["p90_demand"] - result["inventory_position"] - result["order_qty"], 0)
    result["spend_ksh"] = result["order_qty"] * result["unit_cost_ksh"]
    return OptimizationResult("FALLBACK_RULE_BASED", "none", None, result, {"budget_ksh": budget_ksh, "total_spend_ksh": float(result["spend_ksh"].sum())}, message)


def save_forecast(result: ForecastResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.forecast.to_csv(path, index=False)
    path.with_suffix(".json").write_text(json.dumps({"model": result.model, "target": result.target, "horizon": result.horizon, "diagnostics": result.diagnostics}, indent=2, default=str))
