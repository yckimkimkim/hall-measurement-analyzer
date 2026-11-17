# Hall Data Analyzer v1.8

## Changed in v1.8
- Batch Analyzer: **Carrier concentration** and **Hall mobility** are calculated for each ZIP measurement independently, then the valid individual values are arithmetically averaged per Sample.
- Top `Electrical properties`, `Batch summary`, and `Per-metric repeat statistics` now use the **same arithmetic means** for these two metrics.
- Mean signed Hall coefficient, mean resistivity, and mean sheet resistance remain arithmetic means of their own measurements.
- Existing graphs (five), ZIP-only Single/Batch upload, scientific-notation current entry, and thickness in the per-measurement CSV are retained.
- Single Analyzer remains unchanged.
- Invalid/NaN measurements are excluded from a specific metric's mean but are not silently deleted. Consult repeat tables/diagnostics, especially for unstable Hall polarity.

### Update on GitHub
Replace `app.py`, `batch_processing.py`, and optionally `test_batch.py`, `README.md`. Keep `hall_core.py` and `requirements.txt`.

### Local tests
`python test_core.py` and `python test_batch.py`.

# Hall Data Analyzer v1.7

This version accepts **ZIP only** in both Single and Batch tabs.

- **Single Analyzer:** Upload one ZIP containing Hall and van der Pauw files.
- **Batch Analyzer:** Upload several ZIPs simultaneously; each ZIP corresponds to **one measurement repeat**. The Sample field allows grouping repetitions by specimen.
- Magnetic field: 1.08 T default. Thickness: required (no prefill). Test Current: A, accepts `1e-7` / `1E-7`.
- Batch plots: resistivity, Hall mobility, carrier concentration, signed Hall coefficient, sheet resistance.
- Batch downloads include `Thickness_nm` in the per-measurement CSV.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Interpretation

The **Electrical properties** summary derives Hall concentration and mobility from the sample's *mean signed Hall coefficient* and *mean resistivity*. **Per-metric repeat statistics** uses arithmetic means of the properties computed for each repeat. These generally differ because inversion and ratios are nonlinear.

With unstable Hall coefficient signs, neither value should be treated as a confirmed material property until magnetic-field polarity, contact wiring, and Hall geometry consistency have been checked. Don't automatically flip negative values to positive.

## Changes

v1.7 removes directory upload, folder slots, and ZIP/directory selectors. Analysis formulas, repeat plots, and CSV exports are unchanged. The now-unused `folder_upload.py` is not included in this release.
