"""ZIP-per-measurement batch aggregation and reporting."""
import numpy as np
import pandas as pd
from hall_core import Q, read_zip

METRICS = [
    ("Resistivity", "rho_ohm_cm", "Ω·cm"),
    ("Hall mobility", "mu_each_cm2_Vs", "cm²/V·s"),
    ("Carrier concentration", "n_each_cm3", "cm⁻³"),
    ("Hall coefficient", "RH_cm3_C", "cm³/C"),
    ("Sheet resistance", "Rs_ohm_sq", "Ω/□"),
]

def batch_one_zip(data: bytes, name: str, sample: str, seq: int, current_a: float, recorded: bool):
    """Each ZIP is one repeat: ignore incidental internal folder names as grouping."""
    raw, notices = read_zip(data, current_a, recorded)
    if raw.empty:
        return raw, notices
    duplicates = raw["Type"].duplicated(keep=False)
    if duplicates.any():
        notices.append(f"{name}: 같은 측정 종류가 ZIP 내에 중복됨. 첫 번째 유효 파일만 채택: {', '.join(raw.loc[duplicates,'Type'].unique())}")
        raw = raw.drop_duplicates("Type", keep="first")
    raw = raw.copy()
    raw["Sample"] = sample
    raw["Repeat"] = f"Repeat_{seq:04d}"
    raw["ZIP"] = name
    return raw, notices


def batch_derived(reps):
    d = reps.copy()
    rh = pd.to_numeric(d["RH_cm3_C"], errors="coerce")
    rho = pd.to_numeric(d["rho_ohm_cm"], errors="coerce")
    d["n_each_cm3"] = np.where(rh.notna() & (rh.abs()>0), 1/(Q*rh.abs()), np.nan)
    d["mu_each_cm2_Vs"] = np.where(rh.notna() & (rho>0), rh.abs()/rho, np.nan)
    return d


def batch_stats(reps):
    rows=[]
    for sample, d in reps.groupby("Sample", sort=False):
        for label, col, unit in METRICS:
            a=pd.to_numeric(d[col], errors="coerce").dropna()
            avg=float(a.mean()) if len(a) else np.nan
            sd=float(a.std(ddof=1)) if len(a)>1 else np.nan
            rows.append({"Sample":sample,"Metric":label,"Unit":unit,"N":len(a),
                         "Mean (arithmetic repeat values)":avg,"SD":sd,
                         "CV (%)":abs(sd/avg)*100 if np.isfinite(sd) and avg else np.nan,
                         "Min":float(a.min()) if len(a) else np.nan,
                         "Max":float(a.max()) if len(a) else np.nan})
    return pd.DataFrame(rows)

