import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import numpy as np
import time

# 页面配置
st.set_page_config(page_title="A股量化决策终端", layout="wide")

# 强制隐藏Streamlit默认的菜单和页脚
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# --- 股票清单 (V12.0) ---
stock_list =[
    {"code": "sz002100", "name": "天康生物", "buy": 7.0,   "sell": 10.0},
    {"code": "sh603977", "name": "国泰集团", "buy": 12.0,  "sell": 20.0},
    {"code": "sz002408", "name": "齐翔腾达", "buy": 5.0,   "sell": 10.0},
    {"code": "sz301058", "name": "中粮科工", "buy": 10.0,  "sell": 18.0},
    {"code": "sz000928", "name": "中钢国际", "buy": 6.5,   "sell": 10.0},
    {"code": "sh600500", "name": "中化国际", "buy": 4.0,   "sell": 10.0},
    {"code": "sz300034", "name": "钢研高纳", "buy": 16.0,  "sell": 25.0},
    {"code": "sh601118", "name": "海南橡胶", "buy": 6.0,   "sell": 10.0},
    {"code": "sh603227", "name": "雪峰科技", "buy": 8.0,   "sell": 12.0},
    {"code": "sh600459", "name": "贵研铂业", "buy": 18.5,  "sell": 25.0},
    {"code": "sz000731", "name": "四川美丰", "buy": 5.5,   "sell": 10.0},
    {"code": "sz000707", "name": "双环科技", "buy": 6.0,   "sell": 10.0},
    {"code": "sz002783", "name": "凯龙股份", "buy": 8.5,   "sell": 15.0},
    {"code": "sz002237", "name": "恒邦股份", "buy": 14.0,  "sell": 18.0},
    {"code": "sh688707", "name": "振华新材", "buy": 10.0,  "sell": 20.0},
    {"code": "sz300527", "name": "中船应急", "buy": 7.5,   "sell": 12.0},
    {"code": "sh600299", "name": "安迪苏",   "buy": 9.5,   "sell": 15.0},
    {"code": "sz002556", "name": "辉隆股份", "buy": 5.3,   "sell": 8.0},
    {"code": "sh600298", "name": "安琪酵母", "buy": 36.0,  "sell": 55.0},
    {"code": "sh603970", "name": "中农立华", "buy": 11.0,  "sell": 18.0},
    {"code": "sz300470", "name": "中密控股", "buy": 34.0,  "sell": 60.0},
    {"code": "sh600731", "name": "湖南海利", "buy": 6.0,   "sell": 10.0},
    {"code": "sz002136", "name": "安纳达",   "buy": 12.0,  "sell": 20.0},
    {"code": "sh601618", "name": "中国中冶", "buy": 3.0,   "sell": 10.0},
]

# --- 核心计算逻辑 ---
def calculate_concentration(df_part):
    try:
        df_sorted = df_part.sort_values(by='Close')
        df_sorted['CumVol'] = df_sorted['Volume'].cumsum()
        total_vol = df_sorted['Volume'].sum()
        # 寻找5%和95%分位点的价格
        p05_idx = df_sorted['CumVol'].searchsorted(total_vol * 0.05)
        p95_idx = df_sorted['CumVol'].searchsorted(total_vol * 0.95)
        p05 = df_sorted.iloc[min(p05_idx, len(df_sorted)-1)]['Close']
        p95 = df_sorted.iloc[min(p95_idx, len(df_sorted)-1)]['Close']
        return (p95 - p05) / (p95 + p05) * 100, p95
    except: return 999, 0

@st.cache_data(ttl=3600) # 历史建模每小时刷新一次
def load_base_data():
    yahoo_tickers = [item['code'][2:] + (".SS" if item['code'].startswith('sh') else ".SZ") for item in stock_list]
    data = yf.download(" ".join(yahoo_tickers), period="6mo", progress=False)
    results = {}
    for y_code, item in zip(yahoo_tickers, stock_list):
        try:
            # 兼容多只股票下载后的MultiIndex列名
            if isinstance(data.columns, pd.MultiIndex):
                s_close = data['Close'][y_code]
                s_vol = data['Volume'][y_code]
            else:
                s_close = data['Close']
                s_vol = data['Volume']
            
            df = pd.DataFrame({'Close': s_close, 'Volume': s_vol}).dropna()
            if len(df) > 0:
                df_calc = df.iloc[-120:]
                ma_val = df_calc['Close'].mean()
                conc, cost90 = calculate_concentration(df_calc)
                results[item['code']] = {
                    'history_close': df_calc['Close'].values,
                    'history_vol': df_calc['Volume'].values,
                    'ma120': ma_val, 'concentration': conc, 'cost_90': cost90
                }
        except: pass
    return results

# --- 样式引擎 ---
def apply_style(row):
    # 基础对齐
    styles = ['text-align: center; vertical-align: middle; font-family: monospace;'] * len(row)
    c = {col: i for i, col in enumerate(row.index)}
    decision = row['当前决策']
    
    # 核心背景逻辑
    if "止盈" in decision: return ['background-color: #F8F0FF; color: #6A1B9A; font-weight: bold; text-align: center;'] * len(row)
    if "点火" in decision: return ['background-color: #FFF9F9; color: #D70000; font-weight: bold; text-align: center;'] * len(row)
    
    # 现价红绿
    if row['现价'] >= row['120日线']: styles[c['现价']] += 'color: #D70000; font-weight: bold;'
    else: styles[c['现价']] += 'color: #008000; font-weight: bold;'
    
    # 决策胶囊样式
    pill = 'display: inline-block; width: 140px; padding: 2px; border-radius: 12px; font-size: 12px; border: 1px solid;'
    if "黄金地窖" in decision: styles[c['当前决策']] += pill + 'background-color: #F0F7FF; color: #0077ED; border-color: #D6E9FF;'
    elif "点火起飞" in decision: styles[c['当前决策']] += pill + 'background-color: #FFE6E6; color: #D00000; border-color: #FFCCCC;'
    elif "极致洗盘" in decision: styles[c['当前决策']] += pill + 'background-color: #F2FFF0; color: #008F00; border-color: #D9FFD6;'
    elif "正常震荡" in decision: styles[c['当前决策']] += pill + 'background-color: #F8F9FA; color: #777; border-color: #E9ECEF;'
    elif "乌合之众" in decision: styles[c['当前决策']] += pill + 'background-color: #F8F9FA; color: #BBB; border-color: #F1F3F5;'
    
    # 增加逻辑分割线
    styles[c['获利盘']] += 'border-right: 2px solid #2C3E50 !important; font-weight: bold;'
    return styles

# --- 主界面 ---
st.title("📈 A股量化决策终端 V12.0")

if 'model_data' not in st.session_state:
    with st.spinner("正在初始化量化模型..."):
        st.session_state.model_data = load_base_data()

placeholder = st.empty()

# 自动刷新主循环
while True:
    data_rows = []
    for item in stock_list:
        try:
            res = requests.get(f"http://hq.sinajs.cn/list={item['code']}", headers={'Referer': 'http://finance.sina.com.cn'}, timeout=2)
            elements = res.text.split(',')
            if len(elements) > 3:
                curr = float(elements[3]) if float(elements[3]) != 0 else float(elements[2])
                pre_close = float(elements[2])
                m = st.session_state.model_data.get(item['code'])
                if not m: continue
                
                profit = (m['history_vol'][m['history_close'] <= curr].sum() / m['history_vol'].sum() * 100)
                
                decision = "--"
                if curr >= item['sell']: decision = "💰 止盈出局 🚀🚀🚀"
                elif m['concentration'] > 10: decision = "⚠️ 乌合之众"
                elif m['concentration'] < 7:
                    if curr > m['cost_90']: decision = "🚀 点火起飞 ⭐⭐⭐⭐⭐"
                    elif profit < 30: decision = "💎 黄金地窖 ⭐⭐⭐⭐"
                    else: decision = "🧘 极致洗盘 ⭐⭐⭐"
                else: decision = "⏳ 正常震荡 ⭐⭐"
                if curr <= item['buy'] and "止盈" not in decision: decision += " (买点!)"

                data_rows.append({
                    "股票": item['name'], "现价": curr, "今日涨跌": (curr-pre_close)/pre_close*100,
                    "120日线": m['ma120'], "集中度": m['concentration'], "获利盘": profit,
                    "当前决策": decision, "阻力位": m['cost_90'], 
                    "距阻力": (curr-m['cost_90'])/m['cost_90']*100,
                    "距买点": (curr-item['buy'])/item['buy']*100, "需涨幅": (item['sell']-curr)/curr*100
                })
        except: pass

    if data_rows:
        df = pd.DataFrame(data_rows).sort_values("距买点")
        with placeholder.container():
            st.caption(f"数据实时刷新中 (5秒/次) | 更新时间: {time.strftime('%H:%M:%S')}")
            # 应用样式和格式化
            st.dataframe(
                df.style.hide(axis='index')
                .hide(subset=["120日线"], axis="columns") # 此处已修正
                .bar(subset=['获利盘'], color='#FFC1C1', vmin=0, vmax=100)
                .format("{:.2f}", subset=["现价", "阻力位"])
                .format("{:+.2f}%", subset=["今日涨跌", "距阻力", "距买点", "需涨幅"])
                .format("{:.2f}%", subset=["集中度", "获利盘"])
                .apply(apply_style, axis=1),
                use_container_width=True, height=800
            )
    time.sleep(5)
