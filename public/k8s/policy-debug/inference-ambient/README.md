This directory contains inference-only ambient debug policies that should be
applied manually during staged validation.

Recommended order:

1. `01-inference-strict-mtls.yaml`
2. `02-inference-api-alb-permissive.yaml`
3. `03-pdm-predictor-authorization.yaml`
4. `04-pdm-predictor-networkpolicy.yaml`
