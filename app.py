"""TFT Analyzer-style Hall ZIP Batch dashboard."""
import io
import zipfile
from pathlib import PurePosixPath
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import streamlit as st
from hall_core import read_zip, compute_repeats, summarize_samples, HALL_GEOMS, VDP_GEOMS

st.set_page_config(page_title="Hall Data Analyzer",page_icon="🧲",layout="wide")
st.markdown('''<style>
.block-container {padding-top: 2.2rem; max-width: 1740px;}
h1 {font-size:2.15rem !important; font-weight:750 !important; color:#293246;}
h2,h3 {color:#293246;}
[data-testid="stMetric"] {min-height: 119px; border:1px solid #e6eaf0;}
[data-testid="stMetricLabel"] {font-weight:600;}
[data-testid="stMetricValue"] {font-size:clamp(1.18rem, 1.7vw, 2rem);font-weight:750;letter-spacing:-0.035em;}

div.stButton > button[kind="primary"] {background:#ff4b4b;border-color:#ff4b4b;}
[data-testid="stMetric"] {background:#f3f5f8;border-radius:8px;padding:15px 17px;}
</style>''',unsafe_allow_html=True)
st.title("Hall Data Analyzer")
st.caption("Single / Batch Hall Effect & Van der Pauw Measurement Analysis")


SUPERSCRIPT = str.maketrans("-+0123456789", "⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹")


def scientific_text(value, digits=4, always=False):
    """Human-readable display only; calculations and CSV keep full numeric precision."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not np.isfinite(number):
        return "N/A"
    if number == 0:
        return "0"
    exponent = int(np.floor(np.log10(abs(number))))
    if not always and -2 <= exponent < 4:
        return f"{number:.{max(0, digits - exponent - 1)}f}".rstrip("0").rstrip(".")
    mantissa = number / (10.0 ** exponent)
    return f"{mantissa:.{digits-1}f} × 10{str(exponent).translate(SUPERSCRIPT)}"


def format_display_table(df):
    """Only format the displayed table; numeric values remain unchanged in exports."""
    output = df.copy()
    for column in output.columns:
        if pd.api.types.is_bool_dtype(output[column]):
            continue
        if pd.api.types.is_numeric_dtype(output[column]):
            if pd.api.types.is_integer_dtype(output[column]):
                continue
            output[column] = output[column].map(lambda x: scientific_text(x, digits=5))
    return output


def frame_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def plot_sample(d, name, param, unit):
    fig,ax=plt.subplots(figsize=(9,4.6),dpi=105)
    x=np.arange(1,len(d)+1)
    y=d[param].to_numpy(dtype=float)
    ax.plot(x,y,marker="o",linewidth=1.5)
    finite=y[np.isfinite(y)]
    if len(finite):
        ax.axhline(float(np.mean(finite)),linestyle="--",linewidth=1.3,color="#ff4b4b",label="Mean")
        if len(finite)>1:
            std=float(np.std(finite,ddof=1)); mean=float(np.mean(finite))
            ax.axhspan(mean-std,mean+std,color="#ff4b4b",alpha=.09,label="Mean ± SD")
    ax.set_xticks(x)
    ax.set_xticklabels(d["Repeat"].astype(str),rotation=45,ha="right",fontsize=8)
    ax.set_xlabel("Measurement repeat")
    ax.set_ylabel(f"{param} ({unit})")
    ax.set_title(f"{name} — {param}")
    ax.grid(alpha=.22)
    if len(finite):ax.legend(loc="best",fontsize=8)
    fig.tight_layout()
    return fig


def figure_zip(figs):
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,"w",zipfile.ZIP_DEFLATED) as z:
        for name,fig in figs.items():
            img=io.BytesIO();fig.savefig(img,format="png",dpi=300,bbox_inches="tight")
            z.writestr(name,img.getvalue())
    return bio.getvalue()


def measurement_controls(key):
    a,b,c,d=st.columns(4)
    with a:
        field=st.number_input("Magnetic field |B| (T)",min_value=.000001,value=1.08,format="%.5f",key=f"{key}b")
    with b:
        thick=st.number_input("Thickness (nm)",min_value=.001,value=15.0,step=1.0,key=f"{key}t")
    with c:
        current=st.number_input("Test Current (mA)",min_value=.000001,value=1.0,step=.1,format="%.5f",key=f"{key}i")
    with d:
        recorded=st.checkbox("파일의 실측 전류 사용",value=True,key=f"{key}rec")
    return field,thick,current,recorded


def resistance_controls(key):
    with st.expander("Van der Pauw 자동 계산 설정", expanded=False):
        st.caption("i1-v23 / i3-v41 → RA, i2-v34 / i4-v12 → RB. 각 방향을 평균하여 면저항을 계산합니다. 검증되지 않은 접촉/비오믹 특성은 자동 보정되지 않습니다.")
        override=st.checkbox("저항 파일이 없을 때 Rs 직접 입력",value=False,key=f"{key}manual_switch")
        manual=None
        if override:
            manual=st.number_input("Sheet resistance Rs (Ω/□)",min_value=0.0,value=0.0,format="%.6f",key=f"{key}rs")
            if manual<=0:manual=None
    return None,None,manual


def metric_text(value, digits=4):
    return scientific_text(value, digits=digits)


def display_primary_metrics(summary, key):
    st.markdown("### Electrical properties")
    if len(summary)>1:
        sample=st.selectbox("결과를 표시할 시편",list(summary["Sample"]),key=f"{key}focus")
        s=summary.loc[summary["Sample"]==sample].iloc[0]
    else:
        s=summary.iloc[0]
    c1,c2,c3=st.columns(3)
    c1.metric("Carrier concentration",f"{metric_text(s['Carrier concentration (cm⁻³)'])} cm⁻³")
    c2.metric("Hall mobility",f"{metric_text(s['Hall mobility (cm²/V·s)'])} cm²/V·s")
    c3.metric("Resistivity",f"{metric_text(s['Resistivity (Ω·cm)'])} Ω·cm")
    c4,c5,c6=st.columns(3)
    c4.metric("Sheet resistance",f"{metric_text(s['Rs mean (Ω/□)'])} Ω/□")
    c5.metric("Hall coefficient |RH|",f"{metric_text(abs(s['RH mean (cm³/C)']))} cm³/C")
    c6.metric("Valid repeats",f"Hall {int(s['N Hall'])} / Rs {int(s['N Rs'])}")
    if not np.isfinite(s["Hall mobility (cm²/V·s)"]):
        st.warning("면저항이 계산되지 않아 이동도를 표시할 수 없습니다. ZIP 안의 i1-v23, i2-v34, i3-v41, i4-v12 측정 데이터를 확인하세요.")


def show_results(raw,field,thickness,ra,rb,manual,key):
    reps,issues=compute_repeats(raw,field,thickness,ra,rb)
    summary,reps=summarize_samples(reps,thickness,field,manual)
    if summary.empty:
        st.error("분석할 데이터가 없습니다.");return
    display_primary_metrics(summary,key)
    st.subheader("Analysis summary")
    st.dataframe(format_display_table(summary),hide_index=True,use_container_width=True)
    st.caption("반복별 signed RH와 Rs를 각각 평균한 뒤 nH=1/(q|RH_mean|), μH=|RH_mean|/ρ_mean을 계산합니다. Hall sign은 전극/자기장 극성 검증 전까지 캐리어 타입으로 해석하지 않습니다.")
    with st.expander("Repeat-level results / 반복별 계산 결과",expanded=True):
        st.dataframe(format_display_table(reps),hide_index=True,use_container_width=True)
    with st.expander("Raw file diagnostics / 파일별 추출 결과"):
        st.dataframe(format_display_table(raw),hide_index=True,use_container_width=True)
    with st.expander("Missing conditions and diagnostics"):
        if len(issues):st.dataframe(issues,hide_index=True,use_container_width=True)
        else:st.success("필수 조건 누락이 감지되지 않았습니다.")
        devi=raw[raw["I_deviation_pct"]>5]
        if len(devi):st.warning(f"설정 전류와 실측 전류가 5% 이상 다른 파일 {len(devi)}개")
        for _,s in summary.iterrows():
            if not bool(s["Hall sign stable"]):st.warning(f"{s['Sample']}: Hall 반복의 부호가 일관되지 않습니다. 잡음/배선 방향을 점검하세요.")
            if s["N Hall"]<2:st.warning(f"{s['Sample']}: Hall 유효 반복이 2회 미만이어서 표준편차가 계산되지 않습니다.")
    st.subheader("Plots")
    options=list(summary["Sample"])
    selected=st.selectbox("Sample",options,key=f"{key}sample")
    d=reps[reps["Sample"]==selected].sort_values("Repeat")
    metrics={"Hall coefficient":"RH_cm3_C", "Hall signal":"Rxy_mean_ohm", "Sheet resistance":"Rs_ohm_sq", "Resistivity":"rho_ohm_cm"}
    units={"RH_cm3_C":"cm³/C","Rxy_mean_ohm":"Ω","Rs_ohm_sq":"Ω/□","rho_ohm_cm":"Ω·cm"}
    chosen=st.selectbox("Metric",list(metrics),key=f"{key}metric")
    param=metrics[chosen]
    fig=plot_sample(d,selected,param,units[param]);st.pyplot(fig,use_container_width=True)
    st.subheader("Download")
    c1,c2,c3=st.columns(3)
    c1.download_button("Summary CSV",frame_bytes(summary),"hall_sample_summary.csv",mime="text/csv",key=f"{key}summary")
    c2.download_button("Repeat CSV",frame_bytes(reps),"hall_repeat_results.csv",mime="text/csv",key=f"{key}repeats")
    c3.download_button("Raw / diagnostic CSV",frame_bytes(raw),"hall_raw_extraction.csv",mime="text/csv",key=f"{key}raw")
    st.download_button("Graph PNG (300 dpi)",figure_zip({f"{selected}_{param}.png":fig}),"hall_graphs.zip",mime="application/zip",key=f"{key}fig")
    plt.close(fig)

single,batch=st.tabs(["Single Analyzer","Batch Analyzer"])
with single:
    st.subheader("Single Hall Analyzer")
    st.caption("시편 하나의 반복 측정 ZIP 파일 업로드 · RA/RB 자동 계산")
    upload=st.file_uploader("ZIP file",type=["zip"],key="singlezip")
    field,thick,current,recorded=measurement_controls("single")
    ra,rb,manual=resistance_controls("single")
    if st.button("분석 실행",type="primary",key="single_run"):
        if upload is None:st.error("ZIP 파일을 업로드하세요.")
        else:
            try: st.session_state["single_data"]=read_zip(upload.getvalue(),current,recorded)
            except Exception as e:st.error(f"ZIP 분석 실패: {e}")
    if "single_data" in st.session_state:
        raw,notices=st.session_state["single_data"]
        if len(raw):
            samples=raw["Sample"].unique()
            if len(samples)>1:st.warning("여러 시편이 감지됐습니다. Single 모드에서는 첫 번째 시편만 표시합니다.")
            raw=raw[raw["Sample"]==samples[0]]
            st.caption(f"Detected: {len(raw)} files / {raw['Repeat'].nunique()} repeats")
            show_results(raw,field,thick,ra,rb,manual,"single")
        else:st.error("인식된 데이터가 없습니다.")
        if notices:
            with st.expander(f"File warnings ({len(notices)})"):
                for s in notices[:200]:st.warning(s)
with batch:
    st.subheader("Batch Hall Analyzer")
    st.caption("여러 시편·반복 측정 데이터를 폴더별로 분류한 ZIP 업로드 · RA/RB 자동 계산")
    upload=st.file_uploader("ZIP file (Sample/Repeat/file.xls)",type=["zip"],key="batchzip")
    field,thick,current,recorded=measurement_controls("batch")
    ra,rb,manual=resistance_controls("batch")
    if st.button("Batch 분석 실행",type="primary",key="batch_run"):
        if upload is None:st.error("ZIP 파일을 업로드하세요.")
        else:
            try:st.session_state["batch_data"]=read_zip(upload.getvalue(),current,recorded)
            except Exception as e:st.error(f"ZIP 분석 실패: {e}")
    if "batch_data" in st.session_state:
        raw,notices=st.session_state["batch_data"]
        if len(raw):
            a,b,c=st.columns(3)
            a.metric("Samples",raw["Sample"].nunique())
            b.metric("Repeat groups",raw.groupby(["Sample","Repeat"]).ngroups)
            c.metric("Parsed files",len(raw))
            show_results(raw,field,thick,ra,rb,manual,"batch")
        else:st.error("인식된 데이터가 없습니다.")
        if notices:
            with st.expander(f"File warnings ({len(notices)})",expanded=True):
                for s in notices[:200]:st.warning(s)

st.divider()
st.caption("Method: ±I slope → ±B antisymmetrization → geometry-aligned Hall coefficient → independent repeat means of RH and Rs → nH and μH. Assumptions: uniform film, ohmic contacts, single dominant carrier, calibrated lead polarity.")
