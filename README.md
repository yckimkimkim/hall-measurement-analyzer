# Hall Data Analyzer v1.3

Streamlit web application for Keithley-style Hall and Van der Pauw measurement ZIP files.

## Changes (v1.3)

- Both tabs: **Thickness (nm) starts empty**; numeric input is required when running analysis.
- Both tabs: **Test Current in A**, entered as text, accepting e.g. `1e-7`, `1E-7`, `0.0000001`; default `1e-3 A` (equivalent to the old 1 mA default).
- Single Analyzer: **plots removed**. Displays three primary properties, Rs, RH, results tables, and downloadable CSV.
- Batch Analyzer: **multiple ZIP upload**, with **one ZIP = one measurement repeat**. Each uploaded ZIP is assigned one sequential repeat number, irrespective of internal folder names.
- Batch: editable **Sample** column. Same Sample label = repetitions of that sample; different label = separate sample. Default is `Sample_01` for all uploads.
- Batch: **five graphs**, one per resistivity, Hall mobility, carrier concentration, Hall coefficient, and sheet resistance. X-axis is ZIP upload order / measurement number, Y-axis is each measured/derived property; each graph includes arithmetic mean and ±1 sample SD where available.
- Batch: per-property arithmetic repeat means, sample standard deviations, and CV%, plus the primary derived sample values using **mean signed Hall coefficient** and **mean resistivity**. They are intentionally distinguished: `mean[1/(q|RH|)]` is not generally equal to `1/(q|mean[RH]|)`.
- Each tab keeps raw diagnostics, missing/invalid data warnings, and CSV downloads. Batch also exports all five PNGs in one ZIP.

## Inputs and equations

- Magnetic Field defaults to **1.08 T**.
- Thickness in **nm** must be filled manually, no default.
- Test Current is in **A**, supports scientific notation. It is used for selecting ±I measurement points (±20% threshold). When `파일의 실측 전류 사용` is checked, the accepted points are fitted by their actual measured ΔI. A large current deviation still leads to rejected points, with a file warning; it is **not** proof of valid Hall measurement.
- Each ZIP should have at most one of each measurement type: `i1-v23`, `i2-v34`, `i3-v41`, `i4-v12`, plus `i13-v24_Bpos/Bneg`, `i24-v13_Bpos/Bneg` and optional `offset` files.
- Geometries are inferred from the file names and the already confirmed current return lead convention. Automatic RA/RB pairing: `i1-v23` with `i3-v41`, and `i2-v34` with `i4-v12`.
- `RH = Rxy * t / B` with SI→cm³/C conversion, `rho = Rs * t(cm)`, `nH = 1/(q|RH|)`, `muH=|RH|/rho` in a single-carrier approximation.
- Hall sign is not interpreted as carrier type without independent polarity calibration.

## Examples of ZIP layout

```
run-001.zip
  i1-v23#1@1.xls
  i2-v34#1@1.xls
  i3-v41#1@1.xls
  i4-v12#1@1.xls
  i13-v24_Bpos#1@1.xls
  i13-v24_Bneg#1@1.xls
  i24-v13_Bpos#1@1.xls
  i24-v13_Bneg#1@1.xls
  i13-v24_offset#1@1.xls
  i24-v13_offset#1@1.xls
```

Repeat measurements are uploaded as `run-001.zip`, `run-002.zip`, etc. **Multiple ZIPs**, not a ZIP of ZIPs. If one ZIP contains nested directories, only the individual Excel/CSV measurement files inside that ZIP are parsed.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Upload the CONTENTS of this folder directly into the GitHub repository root (including `.streamlit/config.toml`). The Streamlit entry point is `app.py`. For an existing deployment commit replacements of `app.py` and `hall_core.py`, and add **`batch_processing.py`**. `requirements.txt` stays applicable.

## Local tests

```bash
python test_core.py
python test_batch.py
```

Both tests use synthetic CSV data. The included source was also tested against previously uploaded `.xlsx` measurements (10 files; expected N Hall=1, N Rs=1). `.xls` files need `xlrd` installed from `requirements.txt`. Streamlit's full browser interface should be checked in the deployed environment.

## Caution

The displayed values are conditioned on stable ohmic contacts, reliable ±I at a known B, valid current range, and confirmed geometry. The program does not determine measurement credibility from an algebraically finite result alone.
