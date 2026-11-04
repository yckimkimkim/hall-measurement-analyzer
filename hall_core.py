"""Hall data analysis: pure functions, no Streamlit dependencies."""
from __future__ import annotations
import io
import math
import re
import zipfile
from collections import defaultdict
from pathlib import PurePosixPath
import numpy as np
import pandas as pd
from scipy.optimize import brentq

Q = 1.602176634e-19
HALL_GEOMS = ("i13-v24", "i24-v13")
VDP_GEOMS = ("i1-v23", "i2-v34", "i3-v41", "i4-v12")
VALID_EXT = {".xls", ".xlsx", ".csv", ".txt"}
MAX_UNCOMPRESSED = 500 * 1024 * 1024
MAX_MEMBERS = 10000


def classify(name: str) -> str | None:
    name = PurePosixPath(name).name.lower().replace(" ", "")
    mat = re.search(r"(i13-v24|i24-v13|i1-v23|i2-v34|i3-v41|i4-v12)", name)
    if not mat:
        return None
    g = mat.group(1)
    if g in VDP_GEOMS:
        return g
    if re.search(r"bpos|b_pos|b\+|_plus", name):
        return g + "_pos"
    if re.search(r"bneg|b_neg|b-|_minus", name):
        return g + "_neg"
    if re.search(r"offset|bzero|b_zero|b0", name):
        return g + "_zero"
    return None


def parse_location(path: str) -> tuple[str, str]:
    """Expected Sample/Repeat_001/file.xls; flat files become Sample_01/Repeat_001.

    Also supports Sample/Resistivity/Repeat_001, Sample/Hall/Repeat_001.
    """
    parts = PurePosixPath(path).parts
    folders = list(parts[:-1])
    if folders and folders[0].lower() in {"hall_batch", "hall_data", "measurements", "data"}:
        folders.pop(0)
    sample = folders[0] if folders else "Sample_01"
    repeat = next((p for p in folders[1:] if re.search(r"^(repeat|rep|cycle|run)[_ -]?\d+", p, re.I)), None)
    if repeat is None:
        # In a sample folder, distinct files can still share a common repetition
        repeat = "Repeat_001"
    return sample, repeat


def load_table(path: str, data: bytes) -> pd.DataFrame:
    ext = PurePosixPath(path).suffix.lower()
    if ext in {".xls", ".xlsx"}:
        eng = "xlrd" if ext == ".xls" else "openpyxl"
        excel = pd.ExcelFile(io.BytesIO(data), engine=eng)
        # Keithley files: Runxx worksheet first, nonempty tabs follow
        for sheet in excel.sheet_names:
            head = pd.read_excel(excel, sheet_name=sheet, nrows=4)
            names = {str(c).upper().replace(" ", "") for c in head.columns}
            if any("DIFF" in n for n in names) and any(re.fullmatch(r"I\d+|\d+I", n) for n in names):
                return pd.read_excel(excel, sheet_name=sheet)
        raise ValueError("측정 시트의 I1/VDIFF 열을 찾지 못함")
    else:
        for encoding in ("utf-8-sig", "cp949"):
            try:
                return pd.read_csv(io.BytesIO(data), encoding=encoding, sep=None, engine="python")
            except UnicodeDecodeError:
                continue
        raise ValueError("텍스트 파일 인코딩을 인식하지 못함")


def extract_iv(df: pd.DataFrame, target_ma: float, recorded: bool = True) -> dict:
    col = {str(c).upper().replace(" ", ""): c for c in df.columns}
    i_col = col.get("I1") or next((v for k, v in col.items() if re.fullmatch(r"I\d+|\d+I", k)), None)
    v_col = col.get("VDIFF") or next((v for k, v in col.items() if "DIFF" in k), None)
    if not i_col or not v_col:
        raise ValueError("I1 또는 VDIFF 컬럼 누락")
    ix = pd.to_numeric(df[i_col], errors="coerce").to_numpy(float)
    vy = pd.to_numeric(df[v_col], errors="coerce").to_numpy(float)
    good = np.isfinite(ix) & np.isfinite(vy)
    ix, vy = ix[good], vy[good]
    target = target_ma * 1e-3
    if target <= 0:
        raise ValueError("Test Current는 양수여야 함")
    plus = np.flatnonzero(ix > 0)
    minus = np.flatnonzero(ix < 0)
    if not len(plus) or not len(minus):
        raise ValueError("+I/-I 두 극성 측정점이 모두 필요함")
    # Allows multiple +- cycles inside one file. Each polarity paired by closest time/order.
    # If a file contains a full sweep, keep all points within 20% of the selected test current.
    p_valid = plus[np.abs(ix[plus] - target) <= max(target * .20, 1e-14)]
    n_valid = minus[np.abs(ix[minus] + target) <= max(target * .20, 1e-14)]
    if len(p_valid) == 0 or len(n_valid) == 0:
        raise ValueError("설정 전류 ±20% 내에서 +I/-I 측정점 누락")
    # Approximate symmetric IV slope using independent polarity means.
    ip, im = float(np.mean(ix[p_valid])), float(np.mean(ix[n_valid]))
    vp, vm = float(np.mean(vy[p_valid])), float(np.mean(vy[n_valid]))
    denom = ip - im if recorded else 2 * target
    r = (vp-vm)/denom
    intercept = (vp + vm)/2 - r*(ip+im)/2
    return {"R_ohm":float(r), "Iplus_A":ip, "Iminus_A":im,
            "Vplus_V":vp, "Vminus_V":vm, "offset_iv_V":float(intercept),
            "points_plus":len(p_valid), "points_minus":len(n_valid),
            "I_deviation_pct":max(abs(ip-target), abs(im+target))/target*100}


def read_zip(content: bytes, current_ma: float, recorded: bool = True) -> tuple[pd.DataFrame, list[str]]:
    rows, notices = [], []
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        infos = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
        if len(infos) > MAX_MEMBERS or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
            raise ValueError("ZIP 파일 크기/개수 한도를 초과했습니다 (압축 해제 500MB, 10000개).")
        seen = set()
        for info in infos:
            path = info.filename.replace("\\", "/")
            if ".." in PurePosixPath(path).parts:
                notices.append(f"위험한 경로 건너뜀: {path}")
                continue
            if PurePosixPath(path).suffix.lower() not in VALID_EXT:
                continue
            kind = classify(path)
            if kind is None:
                notices.append(f"분류 불가: {path}")
                continue
            sample, repeat = parse_location(path)
            key = (sample, repeat, kind)
            if key in seen:
                notices.append(f"중복 측정 분류 (각각 독립 반복 처리하려면 Repeat 폴더로 분리): {path}")
                continue
            seen.add(key)
            try:
                values = extract_iv(load_table(path, z.read(info)), current_ma, recorded)
                rows.append({"Sample":sample,"Repeat":repeat,"Type":kind,"File":path, **values})
            except Exception as e:
                notices.append(f"읽기 실패: {path} — {e}")
    return pd.DataFrame(rows), notices


def van_der_pauw(ra: float, rb: float) -> float:
    if not (np.isfinite(ra) and np.isfinite(rb) and ra > 0 and rb > 0):
        return float("nan")
    fun = lambda x: np.exp(-np.pi * ra / x) + np.exp(-np.pi * rb / x) - 1
    return float(brentq(fun, min(ra,rb)*.01, max(ra,rb)*1e5))


def compute_repeats(raw: pd.DataFrame, field_t: float, thickness_nm: float,
                    ra_kind: str | None = None, rb_kind: str | None = None,
                    flip_second_hall: bool=True) -> tuple[pd.DataFrame,pd.DataFrame]:
    if raw.empty: return pd.DataFrame(), pd.DataFrame()
    group_rows, diagnostics = [], []
    for (sample, rep), d in raw.groupby(["Sample","Repeat"], sort=True):
        vals = dict(zip(d["Type"], d["R_ohm"]))
        row = {"Sample":sample,"Repeat":rep,"files":len(d)}
        hall_candidates = []
        for geom in HALL_GEOMS:
            p,n,z = (vals.get(f"{geom}_{s}", float("nan")) for s in ("pos","neg","zero"))
            hall_r = (p-n)/2
            # The two lead configurations reverse apparent polarity, per Keithley layout convention.
            # But user must verify wiring polarity before interpreting sign.
            aligned = -hall_r if geom==HALL_GEOMS[1] and flip_second_hall else hall_r
            row[f"Rxy_{geom}_ohm"] = hall_r
            row[f"Rxy_aligned_{geom}_ohm"] = aligned
            row[f"Offset_est_{geom}_ohm"] = (p+n)/2
            row[f"Offset_B0_{geom}_ohm"] = z
            row[f"Offset_delta_{geom}_ohm"] = ((p+n)/2-z) if np.isfinite(z) else float("nan")
            if np.isfinite(aligned):
                hall_candidates.append(aligned)
        if hall_candidates:
            row["Rxy_mean_ohm"] = float(np.mean(hall_candidates))
            row["Hall_geometry_spread_pct"] = (100 * (max(hall_candidates)-min(hall_candidates)) / np.mean(np.abs(hall_candidates))) if len(hall_candidates)>1 and np.mean(np.abs(hall_candidates)) else float("nan")
            row["RH_cm3_C"] = row["Rxy_mean_ohm"] * (thickness_nm*1e-7) * 1e4 / field_t
        else:
            row["Rxy_mean_ohm"] = row["RH_cm3_C"] = float("nan")
        # Confirmed lead pattern: i1-v23 = current 1 -> 4, voltage 2 - 3.
        # Opposite configurations (1,3) and (2,4) are grouped as
        # the two characteristic van der Pauw resistance directions.
        # Use |V/I| only after the measurement polarity has been confirmed.
        pair_a = [abs(vals[k]) for k in ("i1-v23", "i3-v41") if k in vals and np.isfinite(vals[k])]
        pair_b = [abs(vals[k]) for k in ("i2-v34", "i4-v12") if k in vals and np.isfinite(vals[k])]
        row["R_A_ohm"] = float(np.mean(pair_a)) if pair_a else float("nan")
        row["R_B_ohm"] = float(np.mean(pair_b)) if pair_b else float("nan")
        row["R_A_pair_diff_pct"] = (100 * abs(pair_a[0]-pair_a[1])/np.mean(pair_a)) if len(pair_a)==2 and np.mean(pair_a)>0 else float("nan")
        row["R_B_pair_diff_pct"] = (100 * abs(pair_b[0]-pair_b[1])/np.mean(pair_b)) if len(pair_b)==2 and np.mean(pair_b)>0 else float("nan")
        if pair_a and pair_b and row["R_A_ohm"]>0 and row["R_B_ohm"]>0:
            row["Rs_ohm_sq"] = van_der_pauw(row["R_A_ohm"], row["R_B_ohm"])
            row["rho_ohm_cm"] = row["Rs_ohm_sq"]*(thickness_nm*1e-7)
        else:
            row["Rs_ohm_sq"] = row["rho_ohm_cm"] = float("nan")
        group_rows.append(row)
        if not hall_candidates:
            diagnostics.append({"Sample":sample,"Repeat":rep,"Issue":"Hall ±B 쌍이 완성되지 않음"})
        if not np.isfinite(row["Rs_ohm_sq"]):
            diagnostics.append({"Sample":sample,"Repeat":rep,"Issue":"이번 반복에서 두 방향 저항값 중 하나가 누락됨 (시편의 다른 반복 Rs 사용 가능)"})
    return pd.DataFrame(group_rows),pd.DataFrame(diagnostics)


def summarize_samples(repeats: pd.DataFrame, thickness_nm: float, field_t: float,
                      manual_rs: float | None = None) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Average signed RH and averaged resistivity independently, then derive nH and muH.
    Counts and standard deviations retain underlying repeat-level information.
    """
    if repeats.empty: return pd.DataFrame(),pd.DataFrame()
    output, detail = [], repeats.copy()
    for sample, d in repeats.groupby("Sample",sort=True):
        r_h = pd.to_numeric(d["RH_cm3_C"],errors="coerce").dropna()
        rs = pd.to_numeric(d["Rs_ohm_sq"],errors="coerce").dropna()
        if manual_rs is not None and manual_rs > 0 and len(rs)==0:
            rs = pd.Series([manual_rs],dtype=float)
        r_h_mean = float(r_h.mean()) if len(r_h) else float("nan")
        r_h_std = float(r_h.std(ddof=1)) if len(r_h)>1 else float("nan")
        rs_mean = float(rs.mean()) if len(rs) else float("nan")
        rs_std = float(rs.std(ddof=1)) if len(rs)>1 else float("nan")
        rho = rs_mean * thickness_nm*1e-7
        n = 1/(Q*abs(r_h_mean)) if np.isfinite(r_h_mean) and abs(r_h_mean)>0 else float("nan")
        mu = abs(r_h_mean)/rho if np.isfinite(r_h_mean) and np.isfinite(rho) and rho>0 else float("nan")
        # Hall geometry sign needs independent calibration; omit carrier type.
        output.append({"Sample":sample,"N Hall":len(r_h),"N Rs":len(rs),"RH mean (cm³/C)":r_h_mean,
                       "RH std (cm³/C)":r_h_std,"RH CV (%)":abs(r_h_std/r_h_mean)*100 if np.isfinite(r_h_std) and r_h_mean else np.nan,
                       "Rs mean (Ω/□)":rs_mean,"Rs std (Ω/□)":rs_std,
                       "Resistivity (Ω·cm)":rho,"Carrier concentration (cm⁻³)":n,
                       "Hall mobility (cm²/V·s)":mu,
                       "Hall sign stable": bool(len(r_h)>0 and (np.all(r_h>0) or np.all(r_h<0))),
                       "Hall sign calibrated":"No"})
        detail.loc[detail["Sample"]==sample,"Sample_Rs_mean_ohm_sq"] = rs_mean
        detail.loc[detail["Sample"]==sample,"Sample_RH_mean_cm3_C"] = r_h_mean
    return pd.DataFrame(output), detail
