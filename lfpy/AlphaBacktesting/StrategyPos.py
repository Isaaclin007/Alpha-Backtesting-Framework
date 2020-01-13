# -*- coding: utf-8 -*-
"""
Created on Fri Jan  3 20:38:49 2020

@author: Administrator
"""
import numpy as np
from pandas import DataFrame
from datetime import datetime
import matplotlib.pyplot as plt
from collections import defaultdict

from lfpy.trader.constant import OpenClose

plt.rcParams['font.sans-serif']=['SimHei'] #用来正常显示中文标签
plt.rcParams['axes.unicode_minus']=False #用来正常显示负号

class StrategyPos:
    
    def __init__(self, backtesting_engine, strategy):
        """"""
        self.backtesting_engine = backtesting_engine
        self.strategy = strategy      #策略实例
        self.rate = strategy.rate     #手续费
        
        self.init_pos_df = {}           #每个回测时间点开始时持有每只股票的手数
        self.pos_df = {}                #每个回测时间点结束时持有每只股票的手数
        self.init_value_df = {}         #每个回测时间点开始时持有每只股票的价值
        self.value_df = {}              #每个回测时间点结束时持有每只股票的价值
        self.trading_pos_df = {}        #每个回测时间点每只股票的交易手数
        self.trading_value_df = {}      #每个回测时间点每只股票的交易价值
        self.commission_df = {}         #每个回测时间点每只股票的交易手续费
        self.slippage_df = {}           #每个回测时间点每只股票的交易滑点
        
        self.bars_record_df = {}        #每个回测时间点的汇总信息: 
                                        #init_capital, capital, init_cash, cash, 
                                        #init_portfolio, portfolio, commission
                                          
        self.result_df = DataFrame()      #回测结果记录

        self.series_orders = defaultdict(list) #每个回测时间点的委托单
        
    def calculate_result(self):
        
        if self.strategy.open_close != OpenClose.Open:
            index = [i for i in self.bars_record_df.index if i.hour==15]
        else:
            index = [i for i in self.bars_record_df.index if i.hour==9]
        total_bars_record_df = self.bars_record_df
        bars_record_df = self.bars_record_df.loc[index]
        total_days = len(self.strategy.datetime_list)
        capital = bars_record_df.capital
        
        if self.strategy.open_close != OpenClose.Open:
            if self.strategy.benchmark == "IF":
                benchmark = self.strategy.history_data["IfBenchmarkClose()"]
            elif self.strategy.benchmark == "IH":
                benchmark = self.strategy.history_data["IhBenchmarkClose()"]
            elif self.strategy.benchmark == "IC":
                benchmark = self.strategy.history_data["IcBenchamrkClose()"]
            benchmark.index = [i.replace(hour=15,minute=0) for i in benchmark.index]
        else:
            if self.strategy.benchmark == "IF":
                benchmark = self.strategy.history_data["IfBenchmarkOpen()"].shift(-1)
            elif self.strategy.benchmark == "IH":
                benchmark = self.strategy.history_data["IhBenchmarkOpen()"].shift(-1)
            elif self.strategy.benchmark == "IC":
                benchmark = self.strategy.history_data["IcBenchamrkOpen()"].shift(-1)
            benchmark.index = [i.replace(hour=9,minute=30) for i in benchmark.index]
            
        highlevel = capital.cummax()
        drawdown = capital - highlevel
        
        returns = (capital/capital.shift(1)-1).fillna(0)
        if self.strategy.open_close != OpenClose.Open:
            bench_returns = (benchmark/benchmark.shift(1)-1).fillna(0).Close
        else:
            bench_returns = (benchmark/benchmark.shift(1)-1).fillna(0).Open
        excess_returns = returns - bench_returns
        
        
        cum_returns = (returns+1).cumprod()
        cum_bench_returns = (bench_returns+1).cumprod()
        cum_excess_returns = (excess_returns+1).cumprod()
        
        ddpercent = drawdown/highlevel
        excess_ddpercent = (excess_returns-excess_returns.cummax())/excess_returns.cummax()
        
        max_ddpercent = ddpercent.min()
        max_excess_ddpercent = excess_ddpercent.min()
        
        total_excess_return = cum_excess_returns.iloc[-1]-1
        daily_excess_return = total_excess_return/total_days
        annual_excess_return = total_excess_return/total_days*250
        
        
        self.result_df["balance"] = capital
        self.result_df["ddpercent"] = ddpercent
        self.result_df["excess_ddpercent"] = excess_ddpercent
        self.result_df["return"] = returns
        self.result_df["bench_return"] = bench_returns
        self.result_df["excess_return"] = excess_returns
        self.result_df["cum_return"] = cum_returns
        self.result_df["cum_bench_return"] = cum_bench_returns
        self.result_df["cum_excess_return"] = cum_excess_returns
        
        end_capital = capital.iloc[-1]
        max_drawdown = drawdown.min()
        
        
        total_net_pnl = total_bars_record_df["capital"].iloc[-1]-total_bars_record_df["capital"].iloc[0]
        daily_net_pnl = total_net_pnl/total_days
        
        total_commission = total_bars_record_df["commission"].sum()
        daily_commission = total_commission/total_days
        
        total_slippage = total_bars_record_df["slippage"].sum()
        daily_slippage = total_slippage/total_days
        
        total_turnover = total_bars_record_df["turnover"].sum()
        daily_turnover = total_turnover/total_days
        annual_turnover = daily_turnover*250
        
        total_return = total_bars_record_df["capital"].iloc[-1]/total_bars_record_df["capital"].iloc[0]-1
        annual_return = total_return/total_days*250
        daily_return = returns.mean()
        
        
        return_std = returns.std()
        
        if return_std:
            sharpe_ratio = daily_return/return_std*np.sqrt(250)
        else:
            sharpe_ratio = 0
        
        return_drawdown_ratio = -annual_return/max_ddpercent
        
        self.output("_" *30)
        self.output(f"回测起始日期:\t{self.strategy.actual_start}")
        self.output(f"回测结束日期:\t{self.strategy.actual_end}")
            
        self.output(f"总交易日:\t{total_days}")

        self.output(f"起始资金：\t{self.strategy.capital:,.2f}")
        self.output(f"结束资金：\t{end_capital:,.2f}")

        self.output(f"总收益率：\t{total_return:,.2f}")
        self.output(f"年化收益：\t{annual_return:,.2f}")
        self.output(f"最大回撤: \t{max_drawdown:,.2f}")
        self.output(f"百分比最大回撤: \t{max_ddpercent:,.2f}")
        self.output(f"百分比超额最大回撤:\t{max_excess_ddpercent:,.2f}")
        self.output(f"总超额收益：\t{total_excess_return:,.2f}")
        self.output(f"日均超额收益：\t{daily_excess_return:,.2f}")
        self.output(f"年化超额收益：\t{annual_excess_return:,.2f}")

        self.output(f"总盈亏：\t{total_net_pnl:,.2f}")
        self.output(f"总手续费：\t{total_commission:,.2f}")
        self.output(f"总滑点：\t{total_slippage:,.2f}")
        
        self.output(f"总换手率：\t{total_turnover:,.2f}")
        self.output(f"年换手率：\t{annual_turnover:,.2f}")
        self.output(f"日均换手率：\t{daily_turnover:,.2f}")

        self.output(f"日均盈亏：\t{daily_net_pnl:,.2f}")
        self.output(f"日均手续费：\t{daily_commission:,.2f}")
        self.output(f"日均滑点：\t{daily_slippage:,.2f}")

        self.output(f"日均收益率：\t{daily_return:,.2f}%")
        self.output(f"收益标准差：\t{return_std:,.2f}%")
        self.output(f"Sharpe_Ratio：\t{sharpe_ratio:,.2f}")
        self.output(f"收益回撤比：\t{return_drawdown_ratio:,.2f}")

        statistics = {
            "start_date": self.strategy.actual_start,
            "end_date": self.strategy.actual_end,
            "total_days": total_days,
            "capital": self.strategy.capital,
            "end_balance": end_capital,
            "max_drawdown": max_drawdown,
            "max_ddpercent": max_ddpercent,
            "max_excess_ddpercent": max_excess_ddpercent,
            "total_net_pnl": total_net_pnl,
            "daily_net_pnl": daily_net_pnl,
            "total_commission": total_commission,
            "daily_commission": daily_commission,
            "total_slippage": total_slippage,
            "daily_slippage": daily_slippage,
            "total_turnover": total_turnover,
            "daily_turnover": daily_turnover,
            "annual_turnover":annual_turnover,
            "total_return": total_return,
            "annual_return": annual_return,
            "daily_return": daily_return,
            "total_excess_return": total_excess_return,
            "daily_excess_return": daily_excess_return,
            "annual_excess_return": annual_excess_return,
            "return_std": return_std,
            "sharpe_ratio": sharpe_ratio,
            "return_drawdown_ratio": return_drawdown_ratio,
        }
        self.statistics = statistics
        return statistics
    
    def output(self, msg):
        print(f"{datetime.now()} ——INFO—— {msg}")
    
    def show_chart(self):
        """"""
        #plt.figure(figsize=(10, 16))
        
        df = self.result_df
        
        """
        balance_plot = plt.subplot(4, 1, 1)
        balance_plot.set_title("Balance")
        self.bars_record_df["capital"].plot(legend=True)

        drawdown_plot = plt.subplot(4, 1, 2)
        drawdown_plot.set_title("Drawdown")
        drawdown_plot.fill_between(range(len(df)), df["drawdown"].values)
        """
        df1 = df[["cum_return","cum_bench_return","cum_excess_return"]]
        df1.plot(figsize=(15,10),legend=["总收益","基准收益","超额收益"])
        
        df2 = df[["ddpercent","excess_ddpercent"]]
        df2.plot(figsize=(15,16),legend=["回撤","超额回撤"])
        
class SeriesOrder:
    
    def __init__(self, order_time, order_mode, order_data):
        self.order_time = order_time
        self.order_mode = order_mode
        self.order_data = order_data
        
    