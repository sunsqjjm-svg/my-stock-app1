# ... (前面的代码保持不变，仅修改 check_stocks 里的决策引擎部分) ...

                # --- V14.1 战术级决策引擎 (逻辑优先级优化) ---
                decision = "--"
                if curr >= item['sell']: 
                    decision = "💰 止盈出局 🚀🚀🚀"
                elif curr <= item['buy']: 
                    decision = "⚡ 触发买入 [Buy Now]"
                
                # 情况 A：筹码已经 90% 绝对集中
                elif m['scr90'] < 7:
                    if curr > m['cost_90']: 
                        decision = "🚀 点火起飞 [5★]"
                    elif profit < 30: 
                        decision = "💎 黄金地窖 [4★]" # 优先判定地窖
                    else:
                        decision = "🧘 极致洗盘 [3.5★]"
                
                # 情况 B：只有核心 70% 筹码集中 (90% 还没跟上)
                elif m['scr70'] < 7:
                    decision = "🎯 核心聚拢 [4.5★]" # 紧跟起飞信号
                
                # 情况 C：筹码涣散
                elif m['scr90'] > 10 and m['scr70'] > 7: 
                    decision = "⚠️ 乌合之众 [1★]"
                else: 
                    decision = "⏳ 正常震荡 [2★]"

# ... (后面样式部分保持不变) ...
