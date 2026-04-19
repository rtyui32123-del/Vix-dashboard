import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(
    page_title="VIX 대시보드",
    page_icon="📊",
    layout="centered"   # 모바일: centered가 더 적합
)

# ── 모바일 최적화 CSS ─────────────────────────────────
st.markdown("""
<style>
/* 전체 폰트 크기 */
html, body, [class*="css"] { font-size: 15px; }

/* 상단 여백 줄이기 */
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }

/* 지표 카드 */
.card {
    background: #f8f9fa;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 5px solid #ccc;
}
.card-label { font-size: 12px; color: #888; margin-bottom: 2px; }
.card-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.card-delta { font-size: 13px; margin-top: 2px; }

/* 신호 배지 */
.badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 16px;
    font-weight: 700;
}

/* 조언 박스 */
.advice-box {
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 8px;
    font-size: 14px;
    line-height: 1.6;
}

/* Streamlit 기본 여백 조정 */
div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────
@st.cache_data(ttl=3600)
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

    dates, vix_vals, sp_vals = [], [], []
    for idx in vix.index:
        key = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10]
        v = vix[idx]
        s = sp.get(idx, None)
        if pd.notna(v) and s is not None and pd.notna(s):
            dates.append(key)
            vix_vals.append(round(float(v), 2))
            sp_vals.append(round(float(s), 2))

    return dates, vix_vals, sp_vals

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

def make_tick_vals(dates):
    tick_vals, tick_texts = [], []
    week_seen = set()
    for d in dates[:-7]:
        dt = datetime.strptime(d, "%Y-%m-%d")
        wk = dt.isocalendar()[:2]
        if wk not in week_seen:
            week_seen.add(wk)
            tick_vals.append(d)
            tick_texts.append(d[5:])
    for d in dates[-7:]:
        tick_vals.append(d)
        tick_texts.append(d[5:])
    return tick_vals, tick_texts

def axis_range(vals, factor=1.5):
    mn, mx = min(vals), max(vals)
    mid  = (mn + mx) / 2
    half = (mx - mn) / 2 * factor
    return [max(0, mid - half), mid + half]

# ── 데이터 fetch ──────────────────────────────────────
with st.spinner("최신 데이터 불러오는 중..."):
    try:
        dates, vix_vals, sp_vals = load_data()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()

latest_vix  = vix_vals[-1]
latest_sp   = sp_vals[-1]
prev_vix    = vix_vals[-2] if len(vix_vals) > 1 else latest_vix
prev_sp     = sp_vals[-2]  if len(sp_vals)  > 1 else latest_sp
vix_change  = latest_vix - prev_vix
sp_change   = latest_sp  - prev_sp
sp_pct      = sp_change / prev_sp * 100

signal_label, signal_color, signal_bg, signal_border = get_signal(latest_vix)
direction, core = get_advice(latest_vix, vix_change, sp_pct)

sp_arrow  = "▲" if sp_change  >= 0 else "▼"
vix_arrow = "▲" if vix_change >= 0 else "▼"
sp_color  = "#1B5E20" if sp_change  >= 0 else "#B71C1C"
vix_color = "#B71C1C" if vix_change >= 0 else "#1B5E20"

# ── 헤더 ──────────────────────────────────────────────
st.markdown(f"""
<div style='text-align:center; padding: 8px 0 4px;'>
  <div style='font-size:22px; font-weight:700;'>📊 VIX & S&P 500</div>
  <div style='font-size:12px; color:#999; margin-top:2px;'>
    {dates[-1]} 기준 · 매시간 자동 갱신
  </div>
</div>
""", unsafe_allow_html=True)

# ── 신호 배지 (가장 크게, 중앙) ───────────────────────
st.markdown(f"""
<div style='text-align:center; margin: 10px 0;'>
  <span class='badge' style='background:{signal_bg}; color:{signal_color}; border: 2px solid {signal_border}; font-size:20px; padding: 8px 28px;'>
    {signal_label}
  </span>
</div>
""", unsafe_allow_html=True)

# ── 지표 카드 2개 나란히 ──────────────────────────────
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
tick_vals, tick_texts = make_tick_vals(dates)

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
    x=dates, y=vix_vals, name="VIX",
    line=dict(color="#E85A2A", width=2.5),
    fill="tozeroy", fillcolor="rgba(232,90,42,0.08)",
    hovertemplate="<b>%{x}</b><br>VIX: %{y:.2f}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=dates, y=sp_vals, name="S&P 500",
    line=dict(color="#1565C0", width=2.5),
    fill="tozeroy", fillcolor="rgba(21,101,192,0.08)",
    hovertemplate="<b>%{x}</b><br>S&P: %{y:,.0f}<extra></extra>"
), row=2, col=1)

fig.add_vline(x=dates[-1], line_dash="dash", line_color="#999", line_width=1)

fig.update_layout(
    height=480,
    hovermode="x unified",
    legend=dict(orientation="h", y=1.04, x=0, font=dict(size=11)),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=40, r=40, t=50, b=40),
    font=dict(size=11)
)

fig.update_xaxes(
    showgrid=True, gridcolor="#f0f0f0",
    tickangle=45, tickfont=dict(size=9),
    tickmode="array", tickvals=tick_vals, ticktext=tick_texts,
)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                 title_text="VIX", title_font=dict(size=10),
                 range=axis_range(vix_vals), row=1, col=1)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                 title_text="S&P", title_font=dict(size=10),
                 range=axis_range(sp_vals), row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── 투자 조언 박스 ────────────────────────────────────
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

# ── 새로고침 버튼 ─────────────────────────────────────
st.markdown("<div style='margin-top:16px;'>", unsafe_allow_html=True)
if st.button("🔄 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
