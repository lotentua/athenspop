# Plan: Extract error messages as private constants and match whole strings in tests

## Context

Tests currently use partial string fragments in `pytest.raises(match=...)` (e.g. `match="earliest departure"`). This is fragile — it could match unrelated messages. Instead, error messages should be exported as module-level private `Final` string constants from the model modules, and tests should match the complete formatted message.

## Design

Error messages with runtime values become `.format()`-style templates. Validators call `.format(...)` on the constant. Tests format the template with the expected values and pass `re.escape(formatted)` to `match=` — this checks the full message text appears in the `ValidationError` output.

## Files to modify

### 1. `src/athenspop/long/scheduling/base.py`
- Add `_DEPARTURE_WINDOW_ERR: Final = "The earliest departure ({}) must be strictly before the latest departure ({})."`
- Validator uses `_DEPARTURE_WINDOW_ERR.format(self.earliest_departure, self.latest_departure)`

### 2. `src/athenspop/long/model/chain.py`
- Add three constants:
  - `_EMPTY_CHAIN_ERR: Final = "The trip chain must contain at least one trip."`
  - `_MONOTONICITY_ERR: Final = "Departure times must be non-decreasing but trip {} has earliest_departure={} which exceeds trip {} earliest_departure={}."`
  - `_SPATIAL_CONTINUITY_ERR: Final = "Trip chain must be spatially continuous but trip {} ends at zone {} while trip {} starts at zone {}."`
- Validators use `.format(...)` on the respective constant

### 3. `tests/long/test_flexible_trip.py`
- Import `_DEPARTURE_WINDOW_ERR` from `scheduling.base`
- `test_rejects_earliest_ge_latest`: match `re.escape(_DEPARTURE_WINDOW_ERR.format(8.0, 8.0))` and `re.escape(_DEPARTURE_WINDOW_ERR.format(9.0, 8.0))`

### 4. `tests/long/test_flexible_trip_chain.py`
- Import `_EMPTY_CHAIN_ERR`, `_MONOTONICITY_ERR`, `_SPATIAL_CONTINUITY_ERR` from `model.chain`
- `test_rejects_empty_chain`: match `re.escape(_EMPTY_CHAIN_ERR)`
- `test_rejects_non_monotonic_departures`: match `re.escape(_MONOTONICITY_ERR.format(0, 9.0, 1, 6.0))`
- `test_rejects_spatial_discontinuity`: match `re.escape(_SPATIAL_CONTINUITY_ERR.format(0, 1, 1, 5))`

## Verification

Run `PYTHONPATH=src python -m pytest tests/long/ -v` — all 13 tests should pass.
