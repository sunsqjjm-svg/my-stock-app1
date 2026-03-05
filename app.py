import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import numpy as np
import time

# =========================================================================
#  1. 页面基础配置
# =========================================================================
st.set_page_config(page_title="量化决策终端V16.0", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- 股票清单 (24只) ---
stock_list =[
    {"code": "sz002100", "name": "天康生物", "buy": 7.0,   "sell": 10.0},
    {"code": "sh603977", "name": "国泰集团", "buy": 13.0,  "sell": 20.0},
    {"code": "sz002408", "name": "齐翔腾达", "buy": 5.5,   "sell": 10.0},
    {"code": "sz301058", "name": "中粮科工", "buy": 10.0,  "sell": 18.0},
    {"code": "sz000928", "name": "中钢国际", "buy": 6.75,   "sell": 10.0},
    {"code": "sh600500", "name": "中化国际", "buy": 4.0,   "sell": 10.0},
    {"code": "sz300034", "name": "钢研高纳", "buy": 20.0,  "sell": 25.0},
    {"code": "sh601118", "name": "海南橡胶", "buy": 6.0,   "sell": 10.0},
    {"code": "sh603227", "name": "雪峰科技", "buy": 8.0,   "sell": 12.0},
    {"code": "sh600459", "name": "贵研铂业", "buy": 18.5,  "sell": 25.0},
    {"code": "sz000731", "name": "四川美丰", "buy": 7.2,   "sell": 10.0},
    {"code": "sz000707", "name": "双环科技", "buy": 6.15,   "sell": 10.0},
    {"code": "sz002783", "name": "凯龙股份", "buy": 9,   "sell": 15.0},
    {"code": "sz002237", "name": "恒邦股份", "buy": 14.0,  "sell": 18.0},
    {"code": "sh688707", "name": "振华新材", "buy": 13.0,  "sell": 20.0},
    {"code": "sz300527", "name": "中船应急", "buy": 7.5,   "sell": 12.0},
    {"code": "sh600299", "name": "安迪苏",   "buy": 9.5,   "sell": 15.0},
    {"code": "sz002556", "name": "辉隆股份", "buy": 5.3,   "sell": 8.0},
    {"code": "sh600298", "name": "安琪酵母", "buy": 36.0,  "sell": 55.0},
    {"code": "sh603970", "name": "中农立华", "buy": 11.0,  "sell": 18.0},
    {"code": "sz300470", "name": "中密控股", "buy": 34.0,  "sell": 60.0},
    {"code": "sh600731", "name": "湖南海利", "buy": 6.0,   "sell": 10.0},
    {"code": "sz002136", "name": "安纳达",   "buy": 12.0,  "sell": 20.0},
    {"code": "sh601618", "name": "中国中冶", "buy": 3.15,   "sell": 10.0},
]

# --- 核心算法 ---
def calculate_advanced_scr(df_part):
    try:
        df_sorted = df_part.sort_values(by='Close')
        df_sorted['CumVol'] = df_sorted['Volume'].cumsum()
        total_vol = df_sorted['Volume'].sum()
        p05 = df_sorted.iloc[df_sorted['CumVol'].searchsorted(total_vol * 0.05)]['Close']
        p95 = df_sorted.iloc[min(df_sorted['CumVol'].searchsorted(total_vol * 0.95), len(df_sorted)-1)]['Close']
        p15 = df_sorted.iloc[df_sorted['CumVol'].searchsorted(total_vol * 0.15)]['Close']
        p85 = df_sorted.iloc[min(df_sorted['CumVol'].searchsorted(total_vol * 0.85), len(df_sorted)-1)]['Close']
        return (p95-p05)/(p95+p05)*100, (p85-p15)/(p85+p15)*100, p95
    except: return 999, 999, 0

@st.cache_data(ttl=3600)
def load_base_data():
    yahoo_tickers = [item['code'][2:] + (".SS" if item['code'].startswith('sh') else ".SZ") for item in stock_list]
    data = yf.download(" ".join(yahoo_tickers), period="6mo", progress=False)
    results = {}
    for y_code, item in zip(yahoo_tickers, stock_list):
        try:
            s_close = data['Close'][y_code] if isinstance(data.columns, pd.MultiIndex) else data['Close']
            s_vol = data['Volume'][y_code] if isinstance(data.columns, pd.MultiIndex) else data['Volume']
            df = pd.DataFrame({'Close': s_close, 'Volume': s_vol}).dropna()
            if len(df) > 0:
                df_calc = df.iloc[-120:]
                scr90, scr70, cost90 = calculate_advanced_scr(df_calc)
                results[item['code']] = {
                    'h_close': df_calc['Close'].values, 'h_vol': df_calc['Volume'].values,
                    'ma120': float(df_calc['Close'].mean()), 'scr90': scr90, 'scr70': scr70, 'cost_90': cost90
                }
        except: pass
    return results

# =========================================================================
#  V16.0 样式引擎：逻辑分权，视觉降噪
# =========================================================================
def apply_style(row):
    styles = ['text-align: center; vertical-align: middle; font-family: monospace;'] * len(row)
    c = {col: i for i, col in enumerate(row.index)}
    decision = str(row['当前决策'])
    star_val = row['STAR_RAW'] # 获取隐藏的内部星级分
    
    # 1. 核心行背景：5星起飞(粉红) / 止盈(紫色)
    if "止盈" in decision: return ['background-color: #F8F0FF; color: #6A1B9A; font-weight: bold; text-align: center;'] * len(row)
    if star_val >= 5: return ['background-color: #FFF2F2; color: #D70000; font-weight: bold; text-align: center;'] * len(row)
    
    # 2. 潜伏行背景：4-4.5星顶级筹码 (浅香槟金，低饱和度，优雅降噪)
    if 4 <= star_val < 5:
        styles = ['background-color: #FFFAF0; text-align: center; vertical-align: middle;'] * len(row)
    
    # 3. 垃圾信号降噪：1星 (灰暗处理)
    if star_val <= 1:
        styles = ['color: #BBBBBB; text-align: center; vertical-align: middle; opacity: 0.7;'] * len(row)

    # 4. 现价红绿
    if row['现价'] >= row['MA120_RAW']: styles[c['现价']] += 'color: #D70000; font-weight: bold;'
    else: styles[c['现价']] += 'color: #008000; font-weight: bold;'
    
    # 5. 今日涨跌
    if row['今日涨跌'] > 0: styles[c['今日涨跌']] += 'color: #D70000;'
    elif row['今日涨跌'] < 0: styles[c['今日涨跌']] += 'color: #008000;'
    
    # 6. 【核心修复】买点亮灯逻辑：仅3星以上才亮金灯，1-2星不亮灯防止干扰
    if abs(row['距买点']) <= 3 and star_val >= 3: 
        styles[c['距买点']] += 'background-color: #FFD700; color: #D70000; font-weight: 900; border: 2px solid red;'
    elif abs(row['距买点']) <= 10:
        styles[c['距买点']] += 'color: #D70000; font-weight: bold;'

    # 7. 决策胶囊颜色
    pill = 'display: inline-block; width: 155px; padding: 2px; border-radius: 12px; font-size: 11px; border: 1px solid;'
    if star_val >= 5: styles[c['当前决策']] += pill + 'background-color: #D70000; color: white;'
    elif star_val >= 4: styles[c['当前决策']] += pill + 'background-color: #B8860B; color: white;'
    elif "洗盘" in decision: styles[c['当前决策']] += pill + 'background-color: #F2FFF0; color: #008F00; border-color: #D9FFD6;'
    elif "聚拢" in decision: styles[c['当前决策']] += pill + 'background-color: #E0F7FA; color: #00838F; border-color: #B2EBF2;'
    elif star_val <= 1: styles[c['当前决策']] += pill + 'background-color: #F8F9FA; color: #BBB;'
    
    styles[c['获利盘']] += 'border-right: 2px solid #2C3E50 !important; font-weight: bold;'
    return styles

# --- 主程序 ---
st.title("🚀 A股量化决策终端 V16.0")
st.info("💡 系统进化：V16.0 引入'精英准入制'。仅 3★ 以上优质形态亮起'临界买点'金灯，1★ 乌合之众自动进入'降噪模式'。")

if 'model_data' not in st.session_state:
    with st.spinner("正在校准 V16.0 精英决策引擎..."):
        st.session_state.model_data = load_base_data()

placeholder = st.empty()

while True:
    data_rows = []
    for item in stock_list:
        try:
            res = requests.get(f"http://hq.sinajs.cn/list={item['code']}", headers={'Referer': 'http://finance.sina.com.cn'}, timeout=2)
            elements = res.text.split(',')
            if len(elements) > 3:
                curr = float(elements[3]) if float(elements[3]) != 0 else float(elements[2])
                m = st.session_state.model_data.get(item['code'])
                if not m: continue
                profit = (m['h_vol'][m['h_close'] <= curr].sum() / m['h_vol'].sum() * 100)
                dist_buy = (curr-item['buy'])/item['buy']*100
                
                # --- V16.0 深度分权引擎 ---
                decision = "--"; star_score = 2 
                
                if curr >= item['sell']: 
                    decision = "💰 止盈出局 🚀🚀🚀"; star_score = 6
                elif curr <= item['buy']: 
                    decision = "⚡ 触发买入 [Buy Now]"; star_score = 5.5
                
                # A：顶级筹码
                elif m['scr90'] < 7:
                    if curr > m['cost_90']: decision = "🚀 点火起飞 [5★]"; star_score = 5
                    elif profit > 90: decision = "💥 临界爆发 [4.5★]"; star_score = 4.8
                    elif profit < 40: decision = f"💎 黄金地窖 [{'4.5★' if m['scr90'] < 5 else '4★'}]"; star_score = 4.5 if m['scr90'] < 5 else 4.2
                    else: decision = f"🧘 极致洗盘 [{'4.5★' if m['scr90'] < 5 else '3.5★'}]"; star_score = 4.5 if m['scr90'] < 5 else 3.5
                
                # B：趋势走强
                elif profit > 95 and curr > m['cost_90']:
                    decision = "📈 趋势走强 [4★]"; star_score = 4
                
                # C：核心聚拢
                elif m['scr70'] < 7:
                    decision = "🎯 核心聚拢 [3★]"; star_score = 3
                
                # D：涣散垃圾
                elif m['scr90'] > 10:
                    decision = "⚠️ 乌合之众 [1★]"; star_score = 1
                else:
                    decision = "⏳ 正常震荡 [2★]"; star_score = 2

                # --- 临界买点逻辑：精英准入 ---
                if 0 < dist_buy <= 3 and star_score >= 3:
                    decision += " | 🔥 临界"

                data_rows.append({
                    "股票": item['name'], "现价": curr, "今日涨跌": (curr-float(elements[2]))/float(elements[2])*100,
                    "MA120_RAW": m['ma120'], "STAR_RAW": star_score,
                    "集中度90": m['scr90'], "集中度70": m['scr70'], "获利盘": profit,
                    "当前决策": decision, "阻力位": m['cost_90'], "距阻力": (curr-m['cost_90'])/m['cost_90']*100,
                    "距买点": dist_buy, "需涨幅": (item['sell']-curr)/curr*100
                })
        except: pass

    if data_rows:
        df = pd.DataFrame(data_rows).sort_values("距买点")
        with placeholder.container():
            st.dataframe(
                df.style.hide(axis='index')
                .bar(subset=['获利盘'], color='#FFC1C1', vmin=0, vmax=100)
                .format("{:.2f}", subset=["现价", "阻力位"])
                .format("{:+.2f}%", subset=["今日涨跌", "距阻力", "距买点", "需涨幅"])
                .format("{:.2f}%", subset=["集中度90", "集中度70", "获利盘"])
                .apply(apply_style, axis=1),
                column_order=("股票", "现价", "今日涨跌", "集中度90", "集中度70", "获利盘", "当前决策", "阻力位", "距阻力", "距买点", "需涨幅"),
                hide_index=True, use_container_width=True, height=800
            )
    time.sleep(5)

