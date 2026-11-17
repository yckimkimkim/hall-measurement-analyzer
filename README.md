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
