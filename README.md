# Hall Data Analyzer — Single / Batch ZIP

TFT Data Analyzer-inspired Streamlit app for Keithley 4200A-SCS raw I1/VDIFF Hall and Van der Pauw data.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Deploy the folder to GitHub and select `app.py` on Streamlit Community Cloud.

## ZIP folder structure

```text
Hall_Batch.zip
├── Sample_01_AsDep/
│   ├── Repeat_001/
│   │   ├── i1-v23#1@1.xls
│   │   ├── i2-v34#1@1.xls
│   │   ├── i3-v41#1@1.xls
│   │   ├── i4-v12#1@1.xls
│   │   ├── i13-v24_Bpos#1@1.xls
│   │   ├── i13-v24_Bneg#1@1.xls
│   │   ├── i24-v13_Bpos#1@1.xls
│   │   └── i24-v13_Bneg#1@1.xls
│   ├── Repeat_002/ (Hall-only repeat allowed)
│   └── Repeat_003/
└── Sample_02_RTA/
    └── Repeat_001/
```

B=0 `_offset` files are optional diagnostics. `Sample/Resistivity/Repeat_001/` and `Sample/Hall/Repeat_002/` folder layouts are supported.

**Important:** Each Sample+Repeat+Type combination can contain one file; if a repeated acquisition is exported as multiple files with the same naming convention, separate it into distinct Repeat folders. Measurements with just one field polarity cannot yield Hall signal.

## Config defaults

- Magnetic field magnitude 1.08 T
- Thickness 15 nm
- Test Current 1 mA
- Uses recorded I1 by default, checks ±20% matching of current setpoint
- Hall geometry 2 has a sign reversal switch in source code (`flip_second_hall=True`), which matches the supplied raw-pair geometry in magnitude but is **not evidence of absolute polarity**.

## Computation

1. Each file: `R(B) = (V(+I) - V(-I)) / (I(+) - I(-))`.
2. Each Hall wiring geometry: `Rxy = (R(+B) - R(-B)) / 2`.
3. Take average of aligned signed Hall resistance across available geometries; `RH = Rxy * thickness(cm) * 1e4 / B(T)` in cm^3/C (convert SI m³/C to cm³/C).
4. Van der Pauw `exp(-pi RA/Rs)+exp(-pi RB/Rs)=1` where **RA and RB are manually chosen and verified** because raw filenames alone cannot determine the correct physical wiring.
5. Average `RH` and `Rs` separately over repeat groups (Hall and VDP may have different repeat counts); derive `nH = 1/(q|mean RH|)`, `rho = mean Rs * thickness(cm)`, `muH = |mean RH|/rho`.
6. Standard deviation of RH and Rs is sample SD (ddof=1). Missing/invalid readings stay visible; they are not silently zero-filled or excluded as statistical outliers.

Physical safeguards: without an explicit contact-polarity calibration, carrier type cannot be concluded from Hall voltage sign. Voltage signs for VDP contacts must be verified before treating abs(measured slope) as RA/RB. Strong field-dependent offsets or nonlinear IVs require review. No automatic outlier rejection.

## Exports

- Per-sample summary CSV
- Repeat-level CSV
- Raw-file extraction CSV
- 300dpi PNG graph ZIP

## Performance and limitations

ZIP is read in memory and parsed file by file. Limits: 500MB uncompressed and 10,000 ZIP members (not a hosting-memory guarantee). Streamlit's upload limit can be configured in `.streamlit/config.toml` if necessary. Repeated file uploads are reparsed only when the `분석 실행` button is pressed. Changing thickness/B recalculates summaries from extracted slopes.

This is a research prototype; check measurement wiring, magnetic-field direction, Van der Pauw prerequisites and current-voltage linearity before treating results as validated material parameters.
