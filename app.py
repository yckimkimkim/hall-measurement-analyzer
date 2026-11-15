"""Hall Data Analyzer v1.4 — ZIP and directory-per-measurement support."""
from __future__ import annotations

import io
import math
import re
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from hall_core import compute_repeats, read_zip, summarize_samples
from batch_processing import METRICS, batch_one_zip, batch_derived, batch_stats
from folder_upload import batch_sources

st.set_page_config(page_title="Hall Data Analyzer", page_icon="🧲", layout="wide")
st.markdown("""<style>
.block-container {padding-top:2.2rem; max-width:1740px}
h1 {font-size:2.15rem !important;font-weight:750 !important;color:#293246}
h2,h3 {color:#293246}
[data-testid="stMetric"] {min-height:115px;background:#f3f5f8;border:1px solid #e6eaf0;border-radius:8px;padding:15px 17px}
[data-testid="stMetricValue"] {font-size:clamp(1.2rem,1.7vw,2rem);font-weight:750;letter-spacing:-.035em}
div.stButton > button[kind="primary"] {background:#ff4b4b;border-color:#ff4b4b}
</style>""", unsafe_allow_html=True)
st.title("Hall Data Analyzer")
st.caption("Single / Batch Hall Effect & Van der Pauw Measurement Analysis")

SUP = str.maketrans("-+0123456789", "⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹")


def sci(value, sig=4):
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "N/A"
    if not np.isfinite(v):
        return "N/A"
    if v == 0:
        return "0"
    e = int(math.floor(math.log10(abs(v))))
    if -2 <= e < 4:
        return f"{v:.{max(0, sig-e-1)}f}".rstrip("0").rstrip(".") if abs(v) >= 1 else f"{v:.{max(0, sig-e-1)}f}".rstrip("0").rstrip(".")
    return f"{v/10**e:.{sig-1}f} × 10{str(e).translate(SUP)}"


def styled_table(df):
    d = df.copy()
    for c in d:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda x: sci(x, sig=5))
    return d


def csv_data(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def parse_positive_number(text: str, field: str, required=True):
    value = text.strip()
    if not value:
        if required:
            raise ValueError(f"{field}을(를) 입력해 주세요.")
        return None
    try:
        x = float(value)
    except ValueError as ex:
        raise ValueError(f"{field}: 숫자 또는 지수 표기(예: 1e-7)로 입력해 주세요.") from ex
    if not np.isfinite(x) or x <= 0:
        raise ValueError(f"{field}: 0보다 큰 유한한 숫자여야 합니다.")
    return x


def controls(prefix):
    a, b, c, d = st.columns(4)
    with a:
        b_t = st.number_input("Magnetic field |B| (T)", min_value=0.000001, value=1.08, format="%.5f", key=f"{prefix}_B")
    with b:
        thick = st.text_input("Thickness (nm) *", value="", placeholder="예: 163", key=f"{prefix}_thickness")
    with c:
        current = st.text_input("Test Current (A) *", value="1e-3", placeholder="예: 1e-7 또는 1E-7", key=f"{prefix}_current")
    with d:
        recorded = st.checkbox("파일의 실측 전류 사용", value=True, key=f"{prefix}_recorded", help="실제 I+ / I- 값으로 ΔV/ΔI를 계산합니다. 설정 전류는 측정점 선택과 편차 진단에 사용합니다.")
    return b_t, thick, current, recorded


def parse_controls(ctl):
    b_t, thickness_txt, current_txt, recorded = ctl
    return b_t, parse_positive_number(thickness_txt, "Thickness"), parse_positive_number(current_txt, "Test Current"), recorded


def primary(s):
    st.subheader("Electrical properties")
    a,b,c=st.columns(3)
    a.metric("Carrier concentration", sci(s["Carrier concentration (cm⁻³)"]) + " cm⁻³")
    b.metric("Hall mobility", sci(s["Hall mobility (cm²/V·s)"]) + " cm²/V·s")
    c.metric("Resistivity", sci(s["Resistivity (Ω·cm)"]) + " Ω·cm")
    d,e,f=st.columns(3)
    d.metric("Sheet resistance", sci(s["Rs mean (Ω/□)"]) + " Ω/□")
    e.metric("Hall coefficient |RH|", sci(abs(s["RH mean (cm³/C)"])) + " cm³/C")
    f.metric("Valid repeats", f"Hall {int(s['N Hall'])} / Rs {int(s['N Rs'])}")
    if not np.isfinite(s["Hall mobility (cm²/V·s)"]):
        st.warning("이동도를 계산하지 못했습니다. Rs 또는 Hall 값이 누락되었거나 측정 전류가 설정값의 ±20% 범위를 벗어났을 수 있습니다. File warnings를 확인해 주세요.")


def common_diagnostics(raw, problems, notices, label):
    with st.expander(f"Raw file diagnostics — {label}"):
        st.dataframe(styled_table(raw), hide_index=True, use_container_width=True)
    with st.expander(f"Missing data / file warnings ({len(notices)+len(problems)})"):
        if len(problems):
            st.dataframe(problems, hide_index=True, use_container_width=True)
        for msg in notices[:300]:
            st.warning(msg)
        if not notices and not len(problems):
            st.success("파싱 실패 또는 구성 누락 경고 없음")
        if len(raw) and "I_deviation_pct" in raw:
            off = raw.loc[raw["I_deviation_pct"] > 5]
            if len(off):
                st.info(f"설정 전류와 실측 전류 편차가 5% 이상인 파일: {len(off)}개")




def plot_metric(df: pd.DataFrame, param: str, display_name: str, units: str):
    fig, ax = plt.subplots(figsize=(8.3, 4.35), dpi=105)
    d = df.sort_values("Order")
    x = d["Order"].to_numpy(int)
    y = pd.to_numeric(d[param], errors="coerce").to_numpy(float)
    ax.plot(x,y,"o-", linewidth=1.55, markersize=5.5, label="Each measurement")
    finite = y[np.isfinite(y)]
    if len(finite):
        avg = float(finite.mean())
        ax.axhline(avg, color="#ff4b4b", ls="--", lw=1.3, label=f"Mean: {avg:.3g}")
        if len(finite)>1:
            std=float(np.std(finite,ddof=1))
            ax.axhspan(avg-std,avg+std, color="#ff4b4b",alpha=.09,label="Mean ± SD")
    ax.set_xlabel("Measurement number")
    ax.set_ylabel(f"{display_name} ({units})")
    ax.set_title(display_name)
    if len(x):
        ax.set_xticks(x)
        if len(x) > 20:
            ax.set_xticks(x[::max(1,len(x)//15)])
    ax.grid(alpha=.16)
    if len(finite): ax.legend(fontsize=8)
    fig.tight_layout()
    return fig




def bundle_graphs(figures):
    out=io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for filename,fig in figures.items():
            tmp=io.BytesIO();fig.savefig(tmp,format="png",dpi=300,bbox_inches="tight")
            z.writestr(filename,tmp.getvalue())
    return out.getvalue()


single, batch = st.tabs(["Single Analyzer", "Batch Analyzer"])

with single:
    st.subheader("Single Hall Analyzer")
    st.caption("ZIP 1개 또는 측정 폴더 1개 → 주요 물성값과 계산 표만 출력 (그래프 없음)")
    single_mode=st.radio("업로드 방식",["폴더", "ZIP"],horizontal=True,key="single_mode")
    if single_mode=="폴더":
        st.caption("폴더 1개를 선택하세요. 폴더 내부의 Excel 파일명을 자동 인식합니다.")
        single_folder=st.file_uploader("Measurement folder",type=["xls","xlsx","csv","txt"],accept_multiple_files="directory",key="single_folder")
        file=None
    else:
        file=st.file_uploader("Measurement ZIP",type=["zip"],key="single_zip")
        single_folder=[]
    ctl=controls("single")
    if st.button("분석 실행",type="primary",key="single_run"):
        try:
            b_t,thickness,current_a,recorded=parse_controls(ctl)
            if single_mode=="폴더":
                sources=batch_sources([],single_folder,"폴더")
                if len(sources)!=1:
                    raise ValueError(f"Single Analyzer에서는 측정 폴더 1개를 선택해야 합니다. 현재 {len(sources)}개 폴더가 감지됐습니다.")
            else:
                sources=batch_sources([file] if file else [],[],"ZIP")
                if not sources: raise ValueError("ZIP 파일을 업로드해 주세요.")
            source_name,source_data=sources[0]
            raw,notices=read_zip(source_data,current_a,recorded)
            if raw.empty: raise ValueError("유효한 측정 파일이 없습니다. File warnings: " + "; ".join(notices[:5]))
            # One ZIP = one measurement, even if extracted folder happens to have an arbitrary name.
            if raw["Type"].duplicated().any():
                notices.append("ZIP에 동일한 측정 종류가 중복되어 첫 번째 유효 파일만 사용했습니다.")
                raw=raw.drop_duplicates("Type",keep="first")
            raw["Sample"]="Sample_01";raw["Repeat"]="Repeat_0001"
            reps, problems=compute_repeats(raw,b_t,thickness)
            summary,reps=summarize_samples(reps,thickness,b_t)
            st.session_state["single_result"]=(summary,reps,raw,problems,notices, (source_name,b_t,thickness,current_a,recorded))
        except Exception as ex:
            st.error(f"분석 실패: {ex}")
            st.session_state.pop("single_result",None)
    if "single_result" in st.session_state:
        summary,reps,raw,problems,notices,used=st.session_state["single_result"]
        st.caption(f"마지막 분석: {used[0]} · B={used[1]} T · t={used[2]} nm · I={used[3]:.3g} A")
        primary(summary.iloc[0])
        st.subheader("Analysis summary")
        st.dataframe(styled_table(summary), hide_index=True,use_container_width=True)
        with st.expander("Calculated resistance / Hall intermediate values"):
            st.dataframe(styled_table(reps),hide_index=True,use_container_width=True)
        common_diagnostics(raw,problems,notices,"Single")
        a,b,c=st.columns(3)
        a.download_button("Summary CSV",csv_data(summary),"hall_single_summary.csv",mime="text/csv")
        b.download_button("Calculated CSV",csv_data(reps),"hall_single_calculated.csv",mime="text/csv")
        c.download_button("Raw CSV",csv_data(raw),"hall_single_raw.csv",mime="text/csv")

with batch:
    st.subheader("Batch Hall Analyzer")
    st.caption("측정 폴더 1개 = 측정 1회. 부모 폴더를 선택하면 하위 1, 2, 2t, 3 등의 폴더별로 10개 파일을 묶습니다. 기존 ZIP도 지원합니다.")
    batch_mode=st.radio("업로드 방식",["폴더", "ZIP"],horizontal=True,key="batch_mode")
    if batch_mode=="폴더":
        st.caption("예시: Hall Measurements/1/*.xls, Hall Measurements/2/*.xls, Hall Measurements/2t/*.xls — 상위 Hall Measurements 폴더를 선택하세요.")
        folder_files=st.file_uploader("Measurement folders", type=["xls","xlsx","csv","txt"],accept_multiple_files="directory",key="batch_folders")
        zip_files=[]
    else:
        zip_files=st.file_uploader("Measurement ZIP files (multiple)",type=["zip"],accept_multiple_files=True,key="batch_zips")
        folder_files=[]
    sources=[]
    input_error=None
    try:
        sources=batch_sources(zip_files,folder_files,batch_mode)
    except Exception as ex:
        input_error=str(ex)
        st.error(input_error)
    ctl=controls("batch")
    if sources:
        st.caption(f"인식된 측정 세트: {len(sources)}개 · 각 폴더/ZIP을 1회 측정으로 처리합니다. 동일 Sample 이름은 반복 측정으로 집계합니다.")
        names=[name for name,_ in sources]
        labels=[name.rsplit('/',1)[-1] for name in names]
        if len(set(names)) != len(names):
            st.warning("동일한 측정 세트 이름이 있습니다. 업로드 순서로 구분합니다.")
        map_df=pd.DataFrame({"Order":range(1,len(sources)+1), "Measurement":names,"Sample":["Sample_01"]*len(sources)})
        map_df=st.data_editor(map_df,hide_index=True,use_container_width=True,
                              disabled=["Order","Measurement"],key=f"batch_file_map_{batch_mode}",
                              column_config={"Sample":st.column_config.TextColumn("Sample",help="반복 측정 그룹. 서로 다른 시편이면 Sample_02 등으로 변경")})
    else:
        map_df=None
    if st.button("Batch 분석 실행",type="primary",key="batch_run"):
        try:
            b_t,thickness,current_a,recorded=parse_controls(ctl)
            if input_error: raise ValueError(input_error)
            if not sources: raise ValueError("분석할 폴더 또는 ZIP 파일을 업로드해 주세요.")
            items=[];all_notices=[];failed=[]
            for j,((name,payload),(_,m)) in enumerate(zip(sources,map_df.iterrows()),start=1):
                sample=str(m["Sample"]).strip()
                if not sample: raise ValueError(f"{j}번째 측정 세트의 Sample 이름이 비어 있습니다.")
                try:
                    r,w=batch_one_zip(payload,name,sample,j,current_a,recorded)
                    all_notices += [f"[{j}: {name}] {warning}" for warning in w]
                    if r.empty:
                        failed.append(f"{j}: {name} — 유효한 측정 파일 없음")
                    else:
                        items.append(r)
                except Exception as ex:
                    failed.append(f"{j}: {name} — {ex}")
            if not items: raise ValueError("모든 ZIP 분석에 실패했습니다. " + "; ".join(failed[:5]))
            raw=pd.concat(items, ignore_index=True)
            reps,problems=compute_repeats(raw,b_t,thickness)
            order_map={f"Repeat_{i:04d}":i for i in range(1,len(sources)+1)}
            zip_map={f"Repeat_{i:04d}":name for i,(name,_) in enumerate(sources,start=1)}
            reps["Order"]=reps["Repeat"].map(order_map).astype(int)
            reps["ZIP"]=reps["Repeat"].map(zip_map)
            reps=batch_derived(reps)
            summary,reps=summarize_samples(reps,thickness,b_t)
            stats=batch_stats(reps)
            st.session_state["batch_result"]=(summary,reps,raw,problems,all_notices,failed,stats,(b_t,thickness,current_a,recorded))
        except Exception as ex:
            st.error(f"Batch 분석 실패: {ex}")
            st.session_state.pop("batch_result",None)
    if "batch_result" in st.session_state:
        summary,reps,raw,problems,notices,failed,stats,used=st.session_state["batch_result"]
        st.caption(f"마지막 분석 조건: B={used[0]} T · t={used[1]} nm · I={used[2]:.3g} A · 결과: {len(reps)}회 측정")
        a,b,c=st.columns(3)
        a.metric("Samples",len(summary))
        b.metric("Measurements parsed",len(reps))
        c.metric("Measurements failed",len(failed))
        if failed:
            with st.expander(f"Failed ZIPs ({len(failed)})",expanded=True):
                for s in failed: st.warning(s)
        sample=st.selectbox("결과를 표시할 시편",list(summary["Sample"]),key="batch_sample_focus")
        selected=summary.loc[summary["Sample"]==sample].iloc[0]
        primary(selected)
        st.subheader("Batch summary — mean RH and mean resistivity based derived properties")
        st.dataframe(styled_table(summary),hide_index=True,use_container_width=True)
        st.caption("대표 carrier concentration·mobility는 시편별 평균 signed Hall coefficient 및 평균 resistivity를 이용해 산출합니다. 각 ZIP의 개별 계산값에 대한 산술 평균은 아래 통계표에 별도로 표시됩니다.")
        st.subheader("Per-metric repeat statistics (Mean / SD / CV)")
        st.dataframe(styled_table(stats),hide_index=True,use_container_width=True)
        st.subheader(f"5 measurement graphs — {sample}")
        d=reps.loc[reps["Sample"]==sample].sort_values("Order")
        figs={}
        for k,(label,col,unit) in enumerate(METRICS):
            fig=plot_metric(d,col,label,unit)
            figs[f"{sample}_{k+1}_{label.replace(' ','_')}.png"]=fig
            # two graphs per row, last one at left
            if k%2==0:
                cols=st.columns(2)
            with cols[k%2]:
                st.pyplot(fig,use_container_width=True)
        st.caption("X축 숫자는 측정 폴더 또는 ZIP 순번입니다. 회색 점/선은 측정별 값, 빨간 점선은 해당 값의 산술 평균입니다. 데이터가 없는 ZIP은 선이 끊어집니다.")
        with st.expander("Repeat-level results / 측정별 물성값",expanded=True):
            show_cols=["Order","ZIP","Sample","RH_cm3_C","Rs_ohm_sq","rho_ohm_cm","mu_each_cm2_Vs","n_each_cm3","Hall_geometry_spread_pct","R_A_pair_diff_pct","R_B_pair_diff_pct"]
            st.dataframe(styled_table(reps[[c for c in show_cols if c in reps]]),hide_index=True,use_container_width=True)
        common_diagnostics(raw,problems,notices,"Batch")
        a,b,c,d=st.columns(4)
        a.download_button("Sample summary CSV",csv_data(summary),"hall_batch_summary.csv",mime="text/csv")
        b.download_button("5-property statistics CSV",csv_data(stats),"hall_batch_statistics.csv",mime="text/csv")
        c.download_button("Per-measurement results CSV",csv_data(reps),"hall_batch_repeats.csv",mime="text/csv")
        d.download_button("All 5 graphs PNG ZIP",bundle_graphs(figs),"hall_batch_graphs.zip",mime="application/zip")
        for fig in figs.values(): plt.close(fig)

st.divider()
st.caption("Method: ±I correction → ±B reversal → signed Hall coefficient and Van der Pauw Rs → repeat means → derived sample properties. Interpret carrier sign only after verifying probe/B polarity. Units: Thickness nm; Test Current A; B T.")
