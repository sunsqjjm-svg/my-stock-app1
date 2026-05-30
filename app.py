import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import numpy as np
import time
import akshare as ak

# =========================================================================
#  1. 页面配置与样式
# =========================================================================
st.set_page_config(page_title="量化决策终端 V17.5", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
    .stDataFrame {border: 1px solid #e6e9ef;}
    </style>
""", unsafe_allow_html=True)

# --- 股票清单 (25只) ---
stock_list =[
    {"code": "sz002100", "name": "天康生物", "buy": 7.0,   "sell": 10.0},
    {"code": "sh603977", "name": "国泰集团", "buy": 13.0,  "sell": 20.0},
    {"code": "sz002408", "name": "齐翔腾达", "buy": 5.5,   "sell": 10.0},
    {"code": "sz301058", "name": "中粮科工", "buy": 10.0,  "sell": 18.0},
    {"code": "sz000928", "name": "中钢国际", "buy": 6.75,   "sell": 10.0},
    {"code": "sh600500", "name": "中化国际", "buy": 4.0,   "sell": 10.0},
    {"code": "sz300034", "name": "钢研高纳", "buy": 20.0,  "sell": 30.0},
    {"code": "sh601118", "name": "海南橡胶", "buy": 6.0,   "sell": 10.0},
    {"code": "sh603227", "name": "雪峰科技", "buy": 8.0,   "sell": 12.0},
    {"code": "sh600459", "name": "贵研铂业", "buy": 18.5,  "sell": 25.0},
    {"code": "sz000731", "name": "四川美丰", "buy": 7.2,   "sell": 10.0},
    {"code": "sz000707", "name": "双环科技", "buy": 6.15,   "sell": 10.0},
    {"code": "sz000819", "name": "岳阳兴长", "buy": 14.0,   "sell": 30.0},
    {"code": "sz002783", "name": "凯龙股份", "buy": 9.0,    "sell": 15.0},
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
    {"code": "sh600409", "name": "三友化工",   "buy": 6.0,  "sell": 12.0},
    {"code": "sh601618", "name": "中国中冶", "buy": 3.15,   "sell": 10.0},
]

# =========================================================================
#  2. 核心计算逻辑
# =========================================================================
def calculate_scr(df_part):
    try:
        df_sorted = df_part.sort_values(by='Close')
        df_sorted['CumVol'] = df_sorted['Volume'].cumsum()
        total_vol = df_sorted['Volume'].sum()
        p05 = df_sorted.iloc[df_sorted['CumVol'].searchsorted(total_vol * 0.05)]['Close']
        p95 = df_sorted.iloc[min(df_sorted['CumVol'].searchsorted(total_vol * 0.95), len(df_sorted)-1)]['Close']
        return (p95-p05)/(p95+p05)*100, p95
    except: return 99.9, 0

@st.cache_data(ttl=3600)
def load_financial_data():
    """获取净资产与历史数据"""
    results = {}
    try:
        # 获取全市场快照，用于提取净资产
        df_spot = ak.stock_zh_a_spot_em()
        df_spot['代码'] = df_spot['代码'].astype(str).str.zfill(6)
        # 将净资产转为浮点数
        df_spot['每股净资产'] = pd.to_numeric(df_spot['每股净资产'], errors='coerce')
        asset_map = dict(zip(df_spot['代码'], df_spot['每股净资产']))
    except:
        asset_map = {}

    yahoo_tickers = [item['code'][2:] + (".SS" if item['code'].startswith('sh') else ".SZ") for item in stock_list]
    
    # 批量下载历史行情
    try:
        hist_data = yf.download(" ".join(yahoo_tickers), period="6mo", progress=False)
    except:
        hist_data = pd.DataFrame()

    for y_ticker, item in zip(yahoo_tickers, stock_list):
        raw_code = item['code'][2:]
        net_asset = asset_map.get(raw_code, np.nan) # 找不到则为 NaN
        
        m_info = {'net_asset': net_asset, 'ma120': 0, 'scr90': 99.9, 'cost90': 0, 'h_close': [], 'h_vol': []}
        
        try:
            if not hist_data.empty:
                s_close = hist_data['Close'][y_ticker] if isinstance(hist_data.columns, pd.MultiIndex) else hist_data['Close']
                s_vol = hist_data['Volume'][y_ticker] if isinstance(hist_data.columns, pd.MultiIndex) else hist_data['Volume']
                df_hist = pd.DataFrame({'Close': s_close, 'Volume': s_vol}).dropna()
                
                if len(df_hist) > 0:
                    recent = df_hist.iloc[-120:]
                    scr, cost = calculate_scr(recent)
                    m_info.update({
                        'ma120': float(recent['Close'].mean()),
                        'scr90': scr, 'cost90': cost,
                        'h_close': recent['Close'].values,
                        'h_vol': recent['Volume'].values
                    })
        except: pass
        results[item['code']] = m_info
    return results

# =========================================================================
#  3. 视觉样式定义
# =========================================================================
def apply_style(row):
    styles = ['text-align: center; vertical-align: middle;'] * len(row)
    c = {col: i for i, col in enumerate(row.index)}
    
    # 1. 8折特价高亮
    if 0 < row['PB'] <= 0.8:
        styles = ['background-color: #FFF9E6; border-bottom: 1px solid #FFD700;'] * len(row)
        styles[c['PB']] += 'background-color: #FFD700; color: #000; font-weight: bold; border-radius: 4px;'
        styles[c['当前决策']] += 'color: #B8860B; font-weight: bold;'

    # 2. 价格红绿表现
    if row['现价'] >= row['MA120_RAW']: styles[c['现价']] += 'color: #D70000; font-weight: bold;'
    else: styles[c['现价']] += 'color: #008000;'
    
    # 3. 星级逻辑
    if row['STAR_RAW'] >= 5: 
        styles = ['background-color: #FFF2F2; color: #D70000; font-weight: bold;'] * len(row)

    return styles

# =========================================================================
#  4. 主程序界面
# =========================================================================
st.title("🚀 A股量化决策终端 V17.5")
st.caption("同步状态：实时价格(新浪) | 财务估值(东财) | 筹码分布(Yahoo Finance)")

if 'static_data' not in st.session_state:
    with st.status("正在建立数据链路...", expanded=True) as status:
        st.write("正在连接东财 API 获取最新每股净资产...")
        st.session_state.static_data = load_financial_data()
        status.update(label="链路连接成功!", state="complete", expanded=False)

placeholder = st.empty()

while True:
    rows = []
    for item in stock_list:
        try:
            # 实时价格接口 (新浪)
            resp = requests.get(f"http://hq.sinajs.cn/list={item['code']}", 
                                headers={'Referer': 'http://finance.sina.com.cn'}, timeout=1)
            parts = resp.text.split(',')
            if len(parts) <= 3: continue
            
            curr = float(parts[3]) if float(parts[3]) != 0 else float(parts[2])
            prev_close = float(parts[2])
            m = st.session_state.static_data.get(item['code'])
            
            # 核心计算
            net_asset = m['net_asset']
            pb = curr / net_asset if (net_asset and net_asset > 0) else np.nan
            
            profit = 0
            if len(m['h_close']) > 0:
                profit = (m['h_vol'][m['h_close'] <= curr].sum() / m['h_vol'].sum() * 100)
            
            # 决策决策引擎
            decision = "⏳ 震荡蓄势"; star = 2
            if curr >= item['sell']: decision = "💰 建议止盈"; star = 6
            elif curr <= item['buy']: decision = "⚡ 破位/低吸点"; star = 5.5
            elif 0 < pb <= 0.8: decision = "💎 破净特价"; star = 5
            elif m['scr90'] < 8: decision = "🚀 筹码高度锁定"; star = 4
            elif profit > 90: decision = "🔥 极度强势"; star = 4.5

            rows.append({
                "股票": item['name'], "现价": curr, 
                "今日涨跌": (curr - prev_close)/prev_close * 100,
                "每股净资产": net_asset, "PB": pb,
                "获利盘": profit, "集中度90": m['scr90'],
                "当前决策": decision, "距买点": (curr-item['buy'])/item['buy']*100,
                "MA120_RAW": m['ma120'], "STAR_RAW": star
            })
        except: pass

    if rows:
        df = pd.DataFrame(rows).sort_values("STAR_RAW", ascending=False)
        with placeholder.container():
            st.dataframe(
                df.style.hide(axis='index')
                .format("{:.2f}", subset=["现价", "每股净资产", "PB"])
                .format("{:+.2f}%", subset=["今日涨跌", "距买点"])
                .format("{:.1f}%", subset=["获利盤", "集中度90"])
                .apply(apply_style, axis=1),
                column_order=("股票", "现价", "今日涨跌", "每股净资产", "PB", "获利盘", "集中度90", "当前决策", "距买点"),
                use_container_width=True, height=800
            )
    
    time.sleep(5)
