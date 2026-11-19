# Core modeling outcomes

## ARIMA and ARIMAX

- [ ] The real WFP Kenya price file is profiled and its price-versus-demand limitation is documented.
- [ ] ARIMA produces p50/p90 forecasts and stores model diagnostics.
- [ ] ARIMAX accepts aligned training and future exogenous matrices and stores regressor metadata.
- [ ] A real Kenyan public-price holdout run is reproducible without being mislabeled as demand accuracy.

## CVXPY

- [ ] The optimizer accepts p50/p90 demand, inventory position, unit cost, capacity, supplier capacity, order multiple, holding cost and shortage penalty.
- [ ] The objective minimizes procurement, holding and shortage costs.
- [ ] Budget, inventory balance, capacity, supplier and order-multiple constraints are enforced.
- [ ] Solver status is returned and infeasibility has a deterministic fallback.

## Employer proof

- [ ] The project explains which inputs must come from the employer before claiming demand accuracy or savings.
- [ ] The employer walkthrough shows the effect of changing budget and supplier capacity on the order plan.
- [ ] Tests verify non-negative forecasts and CVXPY constraints.
