import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import numpy as np
import time
import akshare as ak

# =========================================================================
#  1. 页面基础配置
# =========================================================================
st.set_page_config(page_title="量化决策终端V17.1", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- 股票清单 ---
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

# --- 核心算法 ---
def calculate_advanced_scr(df_part):
    try:
        df_sorted = df_part.sort_values(by='Close')
        df_sorted['CumVol'] = df_sorted['Volume'].cumsum()
        total_vol = df_sorted['Volume'].sum()
        p05 = df_sorted.iloc[df_sorted['CumVol'].searchsorted(total_vol * 0.05)]['Close']
        p95 = df_sorted.iloc[min(df_sorted['CumVol'].searchsorted(total_vol * 0.95), len(df_sorted)-1)]['Close']
        return (p95-p05)/(p95+p05)*100, p95
    except: return 999, 0

@st.cache_data(ttl=3600)
def load_base_data():
    # 1. 批量获取 A 股最新的每股净资产 (来自东财接口)
    try:
        df_spot = ak.stock_zh_a_spot_em()
        # 建立 股票代码 -> 净资产 的快速字典
        asset_map = {row['代码']: row['每股净资产'] for _, row in df_spot.iterrows()}
    except:
        asset_map = {}

    yahoo_tickers = [item['code'][2:] + (".SS" if item['code'].startswith('sh') else ".SZ") for item in stock_list]
    
    # 2. 批量获取历史K线
    data = yf.download(" ".join(yahoo_tickers), period="6mo", progress=False)
    results = {}
    
    for y_code, item in zip(yahoo_tickers, stock_list):
        try:
            raw_code = item['code'][2:]
            net_asset = asset_map.get(raw_code, 1.0) # 如果查不到，默认1.0避免报错
            
            s_close = data['Close'][y_code] if isinstance(data.columns, pd.MultiIndex) else data['Close']
            s_vol = data['Volume'][y_code] if isinstance(data.columns, pd.MultiIndex) else data['Volume']
            df = pd.DataFrame({'Close': s_close, 'Volume': s_vol}).dropna()
            
            if len(df) > 0:
                df_calc = df.iloc[-120:]
                scr90, cost90 = calculate_advanced_scr(df_calc)
                results[item['code']] = {
                    'h_close': df_calc['Close'].values, 
                    'h_vol': df_calc['Volume'].values,
                    'ma120': float(df_calc['Close'].mean()), 
                    'scr90': scr90, 
                    'cost_90': cost90,
                    'net_asset': float(net_asset) if net_asset else 1.0
                }
        except: pass
    return results

# =========================================================================
#  样式引擎
# =========================================================================
def apply_style(row):
    styles = ['text-align: center; vertical-align: middle;'] * len(row)
    c = {col: i for i, col in enumerate(row.index)}
    star_val = row['STAR_RAW']
    pb_val = row['PB']
    
    # 核心高亮：止盈或高星
    if star_val >= 5: styles = ['background-color: #FFF2F2; color: #D70000; font-weight: bold; text-align: center;'] * len(row)
    
    # PB 8折提醒
    if 0 < pb_val <= 0.8:
        styles[c['PB']] += 'background-color: #FFD700; color: #000; font-weight: bold;'
        styles[c['当前决策']] += 'border: 2px solid #FFD700;'

    # 现价红绿
    if row['现价'] >= row['MA120_RAW']: styles[c['现价']] += 'color: #D70000; font-weight: bold;'
    else: styles[c['现价']] += 'color: #008000; font-weight: bold;'
    
    return styles

# --- 主程序 ---
st.title("🚀 A股量化决策终端 V17.1")
st.caption("数据引擎：实时价格(新浪) | 历史筹码(Yahoo) | 财务净资产(东财)")

if 'model_data' not in st.session_state:
    with st.status("正在校准数据引擎...", expanded=True) as status:
        st.write("正在从东财抓取净资产数据...")
        st.session_state.model_data = load_base_data()
        status.update(label="引擎校准完成!", state="complete", expanded=False)

placeholder = st.empty()

while True:
    data_rows = []
    # 模拟实时数据获取
    for item in stock_list:
        try:
            res = requests.get(f"http://hq.sinajs.cn/list={item['code']}", headers={'Referer': 'http://finance.sina.com.cn'}, timeout=1)
            elements = res.text.split(',')
            if len(elements) > 3:
                curr = float(elements[3]) if float(elements[3]) != 0 else float(elements[2])
                m = st.session_state.model_data.get(item['code'])
                if not m: continue
                
                # 计算逻辑
                pb = curr / m['net_asset']
                profit = (m['h_vol'][m['h_close'] <= curr].sum() / m['h_vol'].sum() * 100)
                dist_buy = (curr-item['buy'])/item['buy']*100
                
                # 决策
                decision = "⏳ 正常震荡"
                star_score = 2
                if curr >= item['sell']: decision = "💰 止盈出局"; star_score = 6
                elif curr <= item['buy']: decision = "⚡ 触发买入"; star_score = 5.5
                elif pb <= 0.8: decision = "💎 破净特价"; star_score = 4.5
                elif m['scr90'] < 7: decision = "🚀 筹码高度集中"; star_score = 4
                
                data_rows.append({
                    "股票": item['name'], "现价": curr, "今日涨跌": (curr-float(elements[2]))/float(elements[2])*100,
                    "MA120_RAW": m['ma120'], "STAR_RAW": star_score,
                    "每股净资产": m['net_asset'], "PB": pb,
                    "获利盘": profit, "集中度90": m['scr90'],
                    "当前决策": decision, "距买点": dist_buy
                })
        except: pass

    if data_rows:
        df = pd.DataFrame(data_rows).sort_values("STAR_RAW", ascending=False)
        with placeholder.container():
            st.dataframe(
                df.style.hide(axis='index')
                .format("{:.2f}", subset=["现价", "每股净资产", "PB"])
                .format("{:+.2f}%", subset=["今日涨跌", "距买点"])
                .format("{:.2f}%", subset=["获利盘", "集中度90"])
                .apply(apply_style, axis=1),
                column_order=("股票", "现价", "今日涨跌", "每股净资产", "PB", "获利盘", "集中度90", "当前决策", "距买点"),
                use_container_width=True, height=800
            )
    time.sleep(5)
