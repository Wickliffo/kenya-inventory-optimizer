# Core Kenyan inventory modeling project

## Scope

This project is intentionally limited to the data-science core: ARIMA, ARIMAX, and CVXPY. It does not build a website or an application shell. Public Kenyan market data is used to prove the forecasting path on real observations. The CVXPY model accepts employer-provided demand forecasts and inventory constraints; it does not invent a company demand dataset.

## Data reality

The included WFP Kenya CSV is market-price data. It supports a real Nairobi price-model demonstration and external-context analysis. It is not POS demand. The actual demand model should be run after an employer provides SKU-location sales or dispatch history, inventory position and supplier constraints.

## Three model components

### ARIMA

Fit a seasonal ARIMA/SARIMA baseline to a single SKU-location demand series or a public market-price series. Return p50 and p90 planning forecasts plus AIC and model configuration.

### ARIMAX

Fit a SARIMAX model with known future regressors. For Kenyan operations, appropriate regressors include promotion, holiday, price, stockout, public market-price context and weather when a causal relationship and future values exist. The implementation requires `exog_future` so future regressors are not hidden or fabricated.

### CVXPY

Solve a replenishment LP/MILP from p50 and p90 lead-time demand, current inventory position, unit cost, capacity, supplier limit, order multiple, holding cost and shortage penalty. Use HIGHS through CVXPY for integer order multiples where available. Return solver status, order quantity, spend, ending inventory, shortage units and the constraint inputs.

## Execution

```bash
python3 -m pip install -r requirements.txt
python3 scripts/profile_public_data.py
python3 scripts/run_core_models.py --market Nairobi --target 'Oil (vegetable)' --exog Bread
python3 scripts/run_cvxpy_plan.py --planning-input path/to/employer_planning_input.csv --budget-ksh 250000
pytest -q
```

The public demonstration is a price forecast. It should be described to an employer as proof that the statistical machinery runs on real Kenyan data, not as demand accuracy. The CVXPY command should be run only on a real employer planning table.

## Employer presentation

The strongest explanation is: “I built the part that turns uncertain demand into a feasible order plan.” Show ARIMA as the baseline, ARIMAX as the use of known business and Kenyan context variables, then show how CVXPY changes the purchase quantities when the budget or supplier capacity changes. The improvement claim is only made after fitting the same code to the employer's data and evaluating an untouched time window.
