import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(
    page_title="VIX & S&P 500 대시보드",
    page_icon="📊",
    layout="wide"
)

# ── 데이터 로드 ───────────────────────────────────────
@st.cache_data(ttl=3600)  # 1시간 캐시 (매시간 자동 갱신)
def load_data():
    end   = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=183)).strftime("%Y-%m-%d")

    vix_df = yf.download("^VIX",  start=start, end=end, progress=False)
    sp_df  = yf.download("^GSPC", start=start, end=end, progress=False)

    if isinstance(vix_df.columns, pd.MultiIndex):
        vix = vix_df["Close"]["^VIX"]
        sp  = sp_df["Close"]["^GSPC"]
    else:
        vix = vix_df["Close"]
        sp  = sp_df["Close"]

    dates    = []
    vix_vals = []
    sp_vals  = []

    for idx in vix.index:
        key = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10]
        v = vix[idx]
        s = sp.get(idx, None)
        if pd.notna(v) and s is not None and pd.notna(s):
            dates.append(key)
            vix_vals.append(round(float(v), 2))
            sp_vals.append(round(float(s), 2))

    return dates, vix_vals, sp_vals

# ── 신호 판단 ─────────────────────────────────────────
def get_signal(v):
    if v < 15:   return "탐욕 😊",      "#2E7D32", "#E8F5E9"
    elif v < 25: return "중립 😐",      "#E65100", "#FFF3E0"
    elif v < 35: return "공포 😨",      "#B71C1C", "#FFEBEE"
    else:        return "극단 공포 🔴", "#4A0000", "#FFCDD2"

def get_advice(vix_val, vix_change, sp_pct):
    vix_up = vix_change > 0
    sp_up  = sp_pct > 0

    if vix_up and not sp_up:
        direction = "📉 VIX↑ S&P↓ — 전형적인 공포 신호"
    elif not vix_up and sp_up:
        direction = "📈 VIX↓ S&P↑ — 전형적인 안정/상승 신호"
    elif vix_up and sp_up:
        direction = "⚠️ VIX↑ S&P↑ — 비전형적 동반 상승, 단기 과열 주의"
    else:
        direction = "⚠️ VIX↓ S&P↓ — 비전형적 동반 하락, 추가 확인 필요"

    if vix_val < 15:
        core = "시장이 매우 안정적입니다. 탐욕 구간에서는 신규 매수보다 기존 포지션 유지 또는 분할 매도를 고려하세요."
    elif vix_val < 25:
        core = "보통 변동성 구간입니다. 포트폴리오 균형을 유지하며 추가 신호를 관망하세요."
    elif vix_val < 35:
        core = "공포 구간입니다. 역발상 관점에서 우량주 분할 매수 기회일 수 있으나, 추가 하락 가능성도 존재합니다."
    else:
        core = "극단적 공포 구간입니다. 역사적으로 이 구간 이후 반등 사례가 많지만, 변동성이 매우 크므로 신중히 접근하세요."

    return direction, core

def make_tick_vals(dates):
    recent_7  = dates[-7:]
    older     = dates[:-7]
    tick_vals, tick_texts = [], []

    week_seen = set()
    for d in older:
        dt       = datetime.strptime(d, "%Y-%m-%d")
        week_key = dt.isocalendar()[:2]
        if week_key not in week_seen:
            week_seen.add(week_key)
            tick_vals.append(d)
            tick_texts.append(d[5:])

    for d in recent_7:
        tick_vals.append(d)
        tick_texts.append(d[5:])

    return tick_vals, tick_texts

# ── 메인 UI ───────────────────────────────────────────
st.title("📊 VIX & S&P 500 대시보드")
st.caption(f"최근 6개월 실제 데이터 · 매시간 자동 갱신 · {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준")

with st.spinner("데이터 불러오는 중..."):
    try:
        dates, vix_vals, sp_vals = load_data()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()

if not dates:
    st.error("데이터가 없습니다.")
    st.stop()

latest_vix  = vix_vals[-1]
latest_sp   = sp_vals[-1]
prev_vix    = vix_vals[-2] if len(vix_vals) > 1 else latest_vix
prev_sp     = sp_vals[-2]  if len(sp_vals)  > 1 else latest_sp
vix_change  = latest_vix - prev_vix
sp_change   = latest_sp  - prev_sp
sp_pct      = sp_change / prev_sp * 100

signal_label, signal_color, signal_bg = get_signal(latest_vix)
direction, core = get_advice(latest_vix, vix_change, sp_pct)

# ── 상단 지표 카드 ────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

vix_delta_color = "inverse" if vix_change > 0 else "normal"
sp_delta_color  = "normal"  if sp_change  > 0 else "inverse"

with col1:
    st.metric("VIX 지수", f"{latest_vix:.2f}",
              delta=f"{vix_change:+.2f}",
              delta_color=vix_delta_color)
with col2:
    st.metric("S&P 500", f"{latest_sp:,.0f}",
              delta=f"{sp_change:+.1f} ({sp_pct:+.2f}%)",
              delta_color=sp_delta_color)
with col3:
    st.metric("공포/탐욕 신호", signal_label)
with col4:
    st.metric("최신 거래일", dates[-1])

st.divider()

# ── 차트 ──────────────────────────────────────────────
def axis_range(vals, factor=1.5):
    mn, mx = min(vals), max(vals)
    mid    = (mn + mx) / 2
    half   = (mx - mn) / 2 * factor
    return [max(0, mid - half), mid + half]

tick_vals, tick_texts = make_tick_vals(dates)

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    subplot_titles=("① VIX 변동성 지수", "② S&P 500"),
    vertical_spacing=0.10,
    row_heights=[0.5, 0.5]
)

for y0, y1, color in [(0,15,"#2E7D32"),(15,25,"#F9A825"),(25,35,"#E64A19"),(35,100,"#B71C1C")]:
    fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.04, row=1, col=1, line_width=0)

for level, color, label in [(15,"#2E7D32","탐욕 15"),(25,"#E64A19","공포 25"),(35,"#B71C1C","극단 35")]:
    fig.add_hline(
        y=level, line_dash="dot", line_color=color, line_width=1.2, opacity=0.6,
        row=1, col=1,
        annotation_text=f" {label}",
        annotation_position="right",
        annotation_font_size=10,
        annotation_font_color=color
    )

fig.add_trace(go.Scatter(
    x=dates, y=vix_vals, name="VIX",
    line=dict(color="#E85A2A", width=2),
    fill="tozeroy", fillcolor="rgba(232,90,42,0.07)",
    hovertemplate="<b>%{x}</b><br>VIX: %{y:.2f}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=dates, y=sp_vals, name="S&P 500",
    line=dict(color="#1565C0", width=2),
    fill="tozeroy", fillcolor="rgba(21,101,192,0.07)",
    hovertemplate="<b>%{x}</b><br>S&P 500: %{y:,.0f}<extra></extra>"
), row=2, col=1)

fig.add_vline(x=dates[-1], line_dash="dash", line_color="gray", line_width=1, opacity=0.4)

fig.update_layout(
    height=600,
    hovermode="x unified",
    legend=dict(orientation="h", y=1.02, x=0),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=90, t=60, b=60),
)

fig.update_xaxes(
    showgrid=True, gridcolor="#f0f0f0",
    tickangle=45, tickfont=dict(size=9),
    tickmode="array",
    tickvals=tick_vals,
    ticktext=tick_texts,
)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                 title_text="VIX", range=axis_range(vix_vals), row=1, col=1)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                 title_text="S&P 500", range=axis_range(sp_vals), row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── 하단 투자 조언 ────────────────────────────────────
st.divider()
st.subheader("📋 VIX-S&P 역방향 분석 투자 조언")

col_a, col_b = st.columns([1, 2])
with col_a:
    st.markdown(f"""
    | 항목 | 값 |
    |------|-----|
    | VIX 현재 | **{latest_vix:.2f}** |
    | 전일 대비 | **{vix_change:+.2f}** |
    | S&P 현재 | **{latest_sp:,.0f}** |
    | 전일 대비 | **{sp_pct:+.2f}%** |
    | 신호 | **{signal_label}** |
    """)

with col_b:
    st.info(f"**방향 분석**\n\n{direction}")
    st.warning(f"**투자 조언**\n\n{core}")

st.caption("※ 이 정보는 투자 권유가 아닙니다. 최종 판단은 본인 책임입니다.")

# 새로고침 버튼
if st.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()
