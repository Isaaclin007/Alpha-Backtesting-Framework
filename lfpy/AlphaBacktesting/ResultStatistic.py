# -*- coding: utf-8 -*-
"""
Created on Wed Aug  7 11:11:40 2019

@author: Administrator
"""
import warnings
import numpy as np
import pandas as pd
from copy import deepcopy
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif']=['SimHei'] #用来正常显示中文标签
plt.rcParams['axes.unicode_minus']=False #用来正常显示负号
warnings.filterwarnings('ignore')

from lfpy.trader.constant import Interval

class ResultStatistic:
    """因子回测结果统计"""
    
    parameters = ["deal","rate","Interval","benchmark","weight"]
    
    def __init__(self, select_stock):
        """"""
        """回测结果统计参数"""
        self.deal = "Open"                 #成交价格:Open开盘价,Avg日均成交价,Close收盘价
        self.rate = 0.000                   #交易费用
        self.Interval = Interval.DAY       #数据的频率
        self.benchmark = "IF"              #基准:IF,IH,IC
        self.weight = "equal"              #组合权重：equal等价值
        
        self.indices = {}
        
        self.select_stock = select_stock
        
    def set_parameters(self, setting):
        """设置参数"""
        for name in setting:
            if name in self.parameters:
                setattr(self, name, setting[name])
    
    @property
    def selection(self):
        """获取选股结果"""
        return self.select_stock.selection
        
    
    def init_returns(self):
        """
        初始化股票和基准收益率，
        避免了在计算策略
        收益率时再计算收益率导致反复计算
        
        注：所有收益率的索引都是以收益率开始的时间为准。
        例如：用2008-03-05到2008-03-06的收盘价计算的收益率的索引为2008-03-05,
        因此selection也要对应：
        Open: select_corr = selection.shift(1)
        Avg: select_corr = selection.shift(1)
        Close: select_corr = deepcopy(selection)
        """
        
        """股票收益率"""
        if hasattr(self, "return_df") and hasattr(self, "bench_return"):
            print("收益率已经初始化")
            return self.return_df, self.bench_return
        
        if self.deal == "Open":
            returns = "delta(Open,1)/delay(Open,1)"
            return_df = self.compute_factor(returns).shift(-1)
        elif self.deal == "Avg":
            returns = "delta(Avg,1)/delay(Avg,1)"
            return_df = self.compute_factor(returns).shift(-1)
        elif self.deal == "Close":
            returns = "delta(Close,1)/delay(Close,1)"
            return_df = self.compute_factor(returns).shift(-1)
        
        """基准收益率"""
        if self.benchmark == "IF":
            bench_return = self.get_basics_value("IfBenchmarkClose()").pct_change(1).shift(-1).iloc[:,0]
        elif self.benchmark == "IC":
            bench_return = self.get_basics_value("IcBenchmarkClose()").pct_change(1).shift(-1).iloc[:,0]
        elif self.benchmark == "IH":
            bench_return = self.get_basics_value("IhBenchmarkClose()").pct_change(1).shift(-1).iloc[:,0]
        
        
        index = sorted(list(set((return_df.index))&set(bench_return.index)))
        return_df = return_df.loc[index]
        bench_return = bench_return.loc[index]
        self.return_df = return_df
        self.bench_return = bench_return
        return return_df, bench_return
        
    def compute_factor(self, factor):
        """因子计算，计算收益率时用"""
        value = self.select_stock.compute_factor(factor)
        return value
    
    def get_basics_value(self, basic_factor):
        """获取基本元数据"""
        return self.select_stock.compute_engine.factor_compute.get_value(basic_factor)
    
    def get_portfolio_num(self):
        """获取做多和做空的股票数量"""
        select_stock = self.select_stock
        return select_stock.n1, select_stock.n2

    def cal_turnover_rate(self):
        """计算换手率"""
        if not hasattr(self, "selection"):
            raise ValueError("Selection cannot be found")
        if not hasattr(self, "weight_df"):
            raise ValueError("Weight cannot be found")
        select_corr = self.selection.shift(1)                                  
        """
        计算换手率的过程中需要关注一个问题：
        就是权重变化原则
        """
        turnover_rate = (np.abs(select_corr-select_corr.shift(1))*self.weight_df).sum(axis=1)
        self.turnover_rate = turnover_rate
        return turnover_rate
        
    def cal_weight(self):
        """计算权重"""
        if not hasattr(self, "selection"):
            raise ValueError("Selection cannot be found")
        selection = self.selection
        n1, n2 = self.get_portfolio_num()
        if self.deal != "Close":
            select_corr = selection.shift(1)
        else:
            select_corr = deepcopy(selection)
        if self.weight == "equal":        #等价值
            weight_df = ((select_corr.fillna(0).T)/(n1+n2).fillna(0)).T
        self.weight_df = weight_df
        return weight_df
    
    def return_cal(self):
        """
        收益率计算：包括总收益率、基准收益率和超额收益率
        """
        self.init_returns()
        self.cal_weight()
        self.cal_turnover_rate()
            
        weight_df = self.weight_df                                             #选股权重dataframe
        return_df = self.return_df                                             #收益率dataframe
        bench_return = self.bench_return                                       #基准收益series
     
        n1, n2 = self.get_portfolio_num()                                      #n1:做多股票数量,n2:做空股票数量
        
        self.selected_return_df = return_df*weight_df
        return_per_bar = (return_df*weight_df).sum(axis=1)
        return_per_bar[return_per_bar == np.inf] = 0.0
        return_per_bar[return_per_bar == -np.inf] = 0.0
        
        self.return_per_bar = return_per_bar
        
        def func_cum(Series):
            if isinstance(Series, pd.Series):
                Series = Series+1
                Series_ = Series.shift(1)
                Series_.iloc[0] = 1
                cum_return_result = Series_.cumprod()
            elif isinstance(Series, pd.DataFrame):
                df = Series+1
                df_ = df.shift(1)
                df_.iloc[0,:] = 1
                cum_return_result = df_.cumprod()
            return cum_return_result
        
        turnover_rate = self.turnover_rate
        total_return = return_per_bar - turnover_rate*2*self.rate
        excess_return = total_return - bench_return
        
        cum_total_return = func_cum(total_return)
        if self.benchmark:
            cum_bench_return = func_cum(bench_return)
            cum_excess_return = func_cum(excess_return)
        
        self.total_return = total_return
        if self.benchmark:
            self.excess_return = excess_return
        
        self.cum_total_return = cum_total_return
        if self.benchmark:
            self.cum_bench_return = cum_bench_return
            self.cum_excess_return = cum_excess_return
        
        self.calculate_indice()
        
        return cum_total_return, cum_bench_return, cum_excess_return
    
    def calculate_indice(self):
        
        """策略指标的计算"""
        
        cum_total_return = self.cum_total_return
        cum_bench_return = self.cum_bench_return
        cum_excess_return = self.cum_excess_return
        
        total_return = self.total_return
        bench_return = self.bench_return
        excess_return = self.excess_return
        
        turnover_rate = self.turnover_rate
        
        interval = self.Interval
        if interval == Interval.MINUTE:
            times = 60000
        elif interval == Interval.HOUR:
            times = 1000
        elif interval == Interval.DAY:
            times = 250
        elif interval == Interval.WEEK:
            times = 36
        elif interval == Interval.MONTH:
            times = 12
        
        """年化收益"""
        annual_total_return = cum_total_return.iloc[-1]**(times/len(cum_total_return.index))-1
        annual_bench_return = cum_bench_return.iloc[-1]**(times/len(cum_bench_return.index))-1
        annual_excess_return = cum_excess_return.iloc[-1]**(times/len(cum_excess_return.index))-1
        
        """最大回撤"""
        total_drawdown = (cum_total_return.cummax()-cum_total_return)/cum_total_return.cummax()
        bench_drawdown = (cum_bench_return.cummax()-cum_bench_return)/cum_bench_return.cummax()
        excess_drawdown = (cum_excess_return.cummax()-cum_excess_return)/cum_excess_return.cummax()
        
        self.total_drawdown = total_drawdown
        self.bench_drawdown = bench_drawdown
        self.excess_drawdown = excess_drawdown
        
        total_max_drawdown = max(total_drawdown)
        bench_max_drawdown = max(bench_drawdown)
        excess_max_drawdown = max(excess_drawdown)
        
        """夏普比率"""
        total_sharpe = total_return.mean()/total_return.std()*np.sqrt(times)
        bench_sharpe = bench_return.mean()/bench_return.std()*np.sqrt(times)
        excess_sharpe = excess_return.mean()/excess_return.std()*np.sqrt(times)
        
        """年换手率"""
        annual_turnover_rate = turnover_rate.sum()*times/len(turnover_rate.index)
        
        """每笔盈利"""
        every_total_profit = annual_total_return/annual_turnover_rate
        every_excess_profit = annual_excess_return/annual_turnover_rate
        
        self.indices["总年化收益"] = annual_total_return
        self.indices["基准年化收益"] = annual_bench_return
        self.indices["超额年化收益"] = annual_excess_return
        
        self.indices["总最大回撤"] = total_max_drawdown
        self.indices["基准最大回撤"] = bench_max_drawdown
        self.indices["超额最大回撤"] = excess_max_drawdown
        
        self.indices["总夏普比率"] = total_sharpe
        self.indices["基准夏普比率"] = bench_sharpe
        self.indices["超额夏普比率"] = excess_sharpe
        
        self.indices["年换手率"] = annual_turnover_rate
        
        self.indices["总每笔盈利"] = every_total_profit
        self.indices["超额每笔盈利"] = every_excess_profit
        
    def plot(self):
        """画图"""
        cum_total_return = self.cum_total_return
        cum_bench_return =self.cum_bench_return
        cum_excess_return = self.cum_excess_return
        
        all_return_df = pd.concat([cum_total_return,cum_bench_return,cum_excess_return],axis=1)
        all_return_df.columns = ["总累积收益","基准累积收益","超额累积收益"]

        all_return_df.plot(figsize=(20,8),logy=True)