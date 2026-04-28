import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(
    page_title="VIX 대시보드",
    page_icon="📊",
    layout="centered"
)

# ── 모바일 최적화 CSS ─────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 15px; }
.block-container { padding-top: 0.6rem !important; padding-bottom: 1rem !important; }

/* 헤더 */
.app-header {
    text-align: center;
    padding: 4px 0;
    width: 100%;
}
.app-title {
    font-size: 19px;
    font-weight: 700;
    line-height: 1.3;
    word-break: keep-all;
    white-space: nowrap;
}
.app-subtitle {
    font-size: 11px;
    color: #999;
    margin-top: 4px;
}

.card {
    background: #f8f9fa;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 5px solid #ccc;
}
.card-label { font-size: 12px; color: #888; margin-bottom: 2px; }
.card-value { font-size: 26px; font-weight: 700; line-height: 1.2; }
.card-delta { font-size: 13px; margin-top: 2px; }

.badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 16px;
    font-weight: 700;
}

.advice-box {
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 8px;
    font-size: 14px;
    line-height: 1.6;
}

/* 평균 테이블 */
.avg-table {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 12px;
    margin: 12px 0;
}
.avg-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 4px;
    border-bottom: 1px solid #e8e8e8;
    font-size: 13px;
}
.avg-row:last-child { border-bottom: none; }
.avg-period { color: #666; font-weight: 500; }
.avg-vix { color: #E85A2A; font-weight: 700; }
.avg-sp { color: #1565C0; font-weight: 700; }

div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    end   = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    # 5년치 받아오기 (평균 계산용)
    start = (datetime.today() - timedelta(days=365*5 + 30)).strftime("%Y-%m-%d")

    dates, vix_vals, sp_vals = [], [], []

    try:
        vix_df = yf.download("^VIX",  start=start, end=end, progress=False, auto_adjust=True)
        sp_df  = yf.download("^GSPC", start=start, end=end, progress=False, auto_adjust=True)
    except Exception as e:
        return dates, vix_vals, sp_vals, f"다운로드 오류: {e}"

    if vix_df.empty or sp_df.empty:
        return dates, vix_vals, sp_vals, "데이터가 비어있습니다"

    try:
        if isinstance(vix_df.columns, pd.MultiIndex):
            vix = vix_df["Close"]["^VIX"]
            sp  = sp_df["Close"]["^GSPC"]
        else:
            vix = vix_df["Close"]
            sp  = sp_df["Close"]
    except Exception as e:
        return dates, vix_vals, sp_vals, f"데이터 구조 오류: {e}"

    vix_dict, sp_dict = {}, {}
    for idx in vix.index:
        key = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10]
        v = vix[idx]
        if pd.notna(v):
            vix_dict[key] = round(float(v), 2)
    for idx in sp.index:
        key = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10]
        s = sp[idx]
        if pd.notna(s):
            sp_dict[key] = round(float(s), 2)

    common = sorted(set(vix_dict.keys()) & set(sp_dict.keys()))
    for d in common:
        dates.append(d)
        vix_vals.append(vix_dict[d])
        sp_vals.append(sp_dict[d])

    if not dates:
        return dates, vix_vals, sp_vals, "공통 거래일이 없습니다"

    return dates, vix_vals, sp_vals, None

def get_signal(v):
    if v < 15:   return "탐욕 😊",      "#2E7D32", "#E8F5E9", "#A5D6A7"
    elif v < 25: return "중립 😐",      "#E65100", "#FFF3E0", "#FFCC80"
    elif v < 35: return "공포 😨",      "#B71C1C", "#FFEBEE", "#EF9A9A"
    else:        return "극단공포 🔴",  "#4A0000", "#FFCDD2", "#EF9A9A"

def get_advice(vix_val, vix_change, sp_pct):
    vix_up = vix_change > 0
    sp_up  = sp_pct > 0
    if vix_up and not sp_up:
        direction = "📉 VIX↑ S&P↓ — 전형적 공포 신호"
    elif not vix_up and sp_up:
        direction = "📈 VIX↓ S&P↑ — 전형적 안정/상승 신호"
    elif vix_up and sp_up:
        direction = "⚠️ VIX↑ S&P↑ — 비전형적, 단기 과열 주의"
    else:
        direction = "⚠️ VIX↓ S&P↓ — 비전형적, 추가 확인 필요"

    if vix_val < 15:
        core = "탐욕 구간입니다. 신규 매수보다 기존 포지션 유지 또는 분할 매도를 고려하세요."
    elif vix_val < 25:
        core = "중립 구간입니다. 포트폴리오 균형을 유지하며 추가 신호를 관망하세요."
    elif vix_val < 35:
        core = "공포 구간입니다. 우량주 분할 매수 기회일 수 있으나 추가 하락 가능성도 존재합니다."
    else:
        core = "극단 공포 구간입니다. 반등 사례가 많지만 변동성이 매우 크므로 신중히 접근하세요."
    return direction, core

# ── 평균 계산 ─────────────────────────────────────────
def calc_averages(dates, vals):
    """최근 1개월/6개월/1년/5년 평균"""
    today = datetime.today()
    periods = {
        "1개월":  30,
        "6개월":  183,
        "1년":    365,
        "5년":    365 * 5,
    }
    result = {}
    for label, days in periods.items():
        cutoff = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        filtered = [v for d, v in zip(dates, vals) if d >= cutoff]
        result[label] = sum(filtered) / len(filtered) if filtered else 0
    return result

# ── X축 눈금: 6개월 화면용 ─────────────────────────────
def make_tick_vals_for_recent(recent_dates):
    """
    - 과거 5개월: 15일 간격
    - 최근 1주일(7거래일): 매일 (세로로 표기)
    """
    if not recent_dates:
        return [], []

    recent_week = recent_dates[-7:] if len(recent_dates) >= 7 else recent_dates
    older       = recent_dates[:-7] if len(recent_dates) >  7 else []

    tick_vals, tick_texts = [], []

    # 과거: 15일 간격
    if older:
        last_pick = None
        for d in older:
            dt = datetime.strptime(d, "%Y-%m-%d")
            if last_pick is None or (dt - last_pick).days >= 15:
                tick_vals.append(d)
                tick_texts.append(d[5:])
                last_pick = dt

    # 최근 1주일: 매일 (세로 — 줄바꿈으로 표시)
    for d in recent_week:
        tick_vals.append(d)
        m, day = d[5:7], d[8:10]
        tick_texts.append(f"{m}<br>/<br>{day}")

    return tick_vals, tick_texts

def axis_range(vals, factor=1.5):
    if not vals: return [0, 1]
    mn, mx = min(vals), max(vals)
    if mn == mx: return [mn * 0.95, mx * 1.05]
    mid  = (mn + mx) / 2
    half = (mx - mn) / 2 * factor
    return [max(0, mid - half), mid + half]

# ── 데이터 fetch ──────────────────────────────────────
with st.spinner("최신 데이터 불러오는 중..."):
    dates, vix_vals, sp_vals, err = load_data()

if not dates:
    st.markdown("""
    <div style='text-align:center; padding: 40px 20px;'>
      <div style='font-size:48px;'>⏳</div>
      <div style='font-size:18px; font-weight:600; margin-top:12px;'>데이터를 불러올 수 없습니다</div>
      <div style='font-size:13px; color:#888; margin-top:8px;'>잠시 후 다시 시도해주세요.</div>
    </div>
    """, unsafe_allow_html=True)
    if err:
        st.caption(f"상세: {err}")
    if st.button("🔄 다시 시도", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# ── 최근 6개월 데이터 (차트용) ──────────────────────────
cutoff_6m = (datetime.today() - timedelta(days=183)).strftime("%Y-%m-%d")
recent_idx = [i for i, d in enumerate(dates) if d >= cutoff_6m]
recent_dates    = [dates[i]    for i in recent_idx]
recent_vix_vals = [vix_vals[i] for i in recent_idx]
recent_sp_vals  = [sp_vals[i]  for i in recent_idx]

# ── 현재값/변화 ───────────────────────────────────────
latest_vix  = vix_vals[-1]
latest_sp   = sp_vals[-1]
prev_vix    = vix_vals[-2] if len(vix_vals) > 1 else latest_vix
prev_sp     = sp_vals[-2]  if len(sp_vals)  > 1 else latest_sp
vix_change  = latest_vix - prev_vix
sp_change   = latest_sp  - prev_sp
sp_pct      = sp_change / prev_sp * 100 if prev_sp else 0

signal_label, signal_color, signal_bg, signal_border = get_signal(latest_vix)
direction, core = get_advice(latest_vix, vix_change, sp_pct)

sp_arrow  = "▲" if sp_change  >= 0 else "▼"
vix_arrow = "▲" if vix_change >= 0 else "▼"
sp_color  = "#1B5E20" if sp_change  >= 0 else "#B71C1C"
vix_color = "#B71C1C" if vix_change >= 0 else "#1B5E20"

# ── 헤더 (글자 안 짤리게) ─────────────────────────────
st.markdown(f"""
<div class='app-header'>
  <div class='app-title'>📊 VIX & S&P 500</div>
  <div class='app-subtitle'>{dates[-1]} 기준 · 매시간 자동 갱신</div>
</div>
""", unsafe_allow_html=True)

# ── 신호 배지 ─────────────────────────────────────────
st.markdown(f"""
<div style='text-align:center; margin: 10px 0;'>
  <span class='badge' style='background:{signal_bg}; color:{signal_color}; border: 2px solid {signal_border}; font-size:20px; padding: 8px 28px;'>
    {signal_label}
  </span>
</div>
""", unsafe_allow_html=True)

# ── 지표 카드 ─────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class='card' style='border-left-color:{vix_color};'>
      <div class='card-label'>VIX 지수</div>
      <div class='card-value' style='color:{vix_color};'>{latest_vix:.2f}</div>
      <div class='card-delta' style='color:{vix_color};'>{vix_arrow} {abs(vix_change):.2f} 전일대비</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='card' style='border-left-color:{sp_color};'>
      <div class='card-label'>S&P 500</div>
      <div class='card-value' style='color:{sp_color};'>{latest_sp:,.0f}</div>
      <div class='card-delta' style='color:{sp_color};'>{sp_arrow} {abs(sp_pct):.2f}% 전일대비</div>
    </div>
    """, unsafe_allow_html=True)

# ── 차트 ──────────────────────────────────────────────
tick_vals, tick_texts = make_tick_vals_for_recent(recent_dates)

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    subplot_titles=("① VIX 변동성 지수", "② S&P 500"),
    vertical_spacing=0.12,
    row_heights=[0.5, 0.5]
)

for y0, y1, color in [(0,15,"#2E7D32"),(15,25,"#F9A825"),(25,35,"#E64A19"),(35,100,"#B71C1C")]:
    fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.05, row=1, col=1, line_width=0)

for level, color, label in [(15,"#2E7D32","15"),(25,"#E64A19","25"),(35,"#B71C1C","35")]:
    fig.add_hline(
        y=level, line_dash="dot", line_color=color, line_width=1, opacity=0.5,
        row=1, col=1,
        annotation_text=label,
        annotation_position="right",
        annotation_font_size=9,
        annotation_font_color=color
    )

fig.add_trace(go.Scatter(
    x=recent_dates, y=recent_vix_vals, name="VIX",
    line=dict(color="#E85A2A", width=2.5),
    fill="tozeroy", fillcolor="rgba(232,90,42,0.08)",
    hovertemplate="<b>%{x}</b><br>VIX: %{y:.2f}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=recent_dates, y=recent_sp_vals, name="S&P 500",
    line=dict(color="#1565C0", width=2.5),
    fill="tozeroy", fillcolor="rgba(21,101,192,0.08)",
    hovertemplate="<b>%{x}</b><br>S&P: %{y:,.0f}<extra></extra>"
), row=2, col=1)

fig.add_vline(x=recent_dates[-1], line_dash="dash", line_color="#999", line_width=1)

fig.update_layout(
    height=520,
    hovermode="x unified",
    legend=dict(orientation="h", y=1.04, x=0, font=dict(size=11)),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=40, r=40, t=50, b=70),
    font=dict(size=11)
)

fig.update_xaxes(
    showgrid=True, gridcolor="#f0f0f0",
    tickangle=0, tickfont=dict(size=10),
    tickmode="array", tickvals=tick_vals, ticktext=tick_texts,
)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                 title_text="VIX", title_font=dict(size=10),
                 range=axis_range(recent_vix_vals), row=1, col=1)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                 title_text="S&P", title_font=dict(size=10),
                 range=axis_range(recent_sp_vals), row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── 평균 테이블 ───────────────────────────────────────
vix_avgs = calc_averages(dates, vix_vals)
sp_avgs  = calc_averages(dates, sp_vals)

st.markdown("""
<div style='font-size:14px; font-weight:700; margin: 14px 0 6px; color:#333;'>
  📈 기간별 평균 수치
</div>
""", unsafe_allow_html=True)

avg_html = """<div class='avg-table'>"""
avg_html += """<div class='avg-row' style='font-weight:700; color:#333; border-bottom:2px solid #ddd;'>
  <span>기간</span><span class='avg-vix'>VIX 평균</span><span class='avg-sp'>S&P 평균</span>
</div>"""
for label in ["1개월", "6개월", "1년", "5년"]:
    avg_html += f"""<div class='avg-row'>
      <span class='avg-period'>최근 {label}</span>
      <span class='avg-vix'>{vix_avgs[label]:.2f}</span>
      <span class='avg-sp'>{sp_avgs[label]:,.0f}</span>
    </div>"""
avg_html += "</div>"
st.markdown(avg_html, unsafe_allow_html=True)

# 현재값 vs 평균 비교
vix_vs_1y = (latest_vix - vix_avgs["1년"]) / vix_avgs["1년"] * 100 if vix_avgs["1년"] else 0
sp_vs_1y  = (latest_sp  - sp_avgs["1년"])  / sp_avgs["1년"]  * 100 if sp_avgs["1년"] else 0

vix_vs_color = "#B71C1C" if vix_vs_1y > 0 else "#1B5E20"
sp_vs_color  = "#1B5E20" if sp_vs_1y  > 0 else "#B71C1C"

st.markdown(f"""
<div style='font-size:12px; color:#666; padding: 4px 4px 12px;'>
  💡 현재값 vs 1년 평균 비교 — 
  VIX <span style='color:{vix_vs_color}; font-weight:700'>{vix_vs_1y:+.1f}%</span> · 
  S&P <span style='color:{sp_vs_color}; font-weight:700'>{sp_vs_1y:+.1f}%</span>
</div>
""", unsafe_allow_html=True)

# ── 투자 조언 ─────────────────────────────────────────
st.markdown(f"""
<div class='advice-box' style='background:{signal_bg}; border-left: 4px solid {signal_color};'>
  <div style='font-size:13px; font-weight:700; color:{signal_color}; margin-bottom:6px;'>
    📋 VIX-S&P 역방향 분석
  </div>
  <div style='color:#333; margin-bottom:6px;'>{direction}</div>
  <div style='color:#555;'>{core}</div>
</div>
<div style='text-align:center; font-size:11px; color:#bbb; margin-top:10px;'>
  ※ 투자 권유 아님 · 최종 판단은 본인 책임
</div>
""", unsafe_allow_html=True)

# ── 새로고침 ──────────────────────────────────────────
st.markdown("<div style='margin-top:16px;'>", unsafe_allow_html=True)
if st.button("🔄 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
