# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 14:46:14 2019

@author: Administrator
"""
import numpy as np
import pandas as pd
from abc import abstractmethod
from functools import lru_cache

from lfpy.trader.constant import (
									SelectMode1,
									SelectMode2,
                                StrategyMode,
									Interval,
                                OpenClose,
                                )
from datetime import datetime
from .BacktestingEngine import BacktestingEngine
from .SelectStock import SelectStock

class Template:
    
    parameters = ["start",
				  "end",
				  "n_long",
                  "n_short",
                  "pct_long",
                  "pct_short",
                  "freq",
                  "select_mode1",
                  "select_mode2",
				  "strategy_mode",
                  "mask",
                  "deal",
                  "rate",
                  "slippage",
                  "Interval",
                  "benchmark",
				  "data_lens",
                  "stock_pool",
                  "capital",
                  "open_close",
                  ]
    
    def __init__(self, backtesting_engine: BacktestingEngine, strategy_name):
        """一个引擎，多个策略"""
        self.backtesting_engine = backtesting_engine   #回测引擎
        self.strategy_name = strategy_name             #策略实例名称
        
        self.strategy_mode = StrategyMode.Flexible
		
        """回测参数"""
        self.start = 0.0                               #回测起始时间
        self.end = 0.0                                 #回测结束时间
        self.actual_start = 0.0						     #实际回测起始时间
        self.actual_end = 0.0                          #实际回测结束时间
        self.n_long = 50                               #多头股票数量
        self.n_short = 50                              #空头股票数量
        self.pct_long = 0.2                            #多头股票比例
        self.pct_short = 0.2                           #空头股票比例
        self.freq = 1                                  #调仓周期
        self.select_mode1 = SelectMode1.LONG           #选股模式1：多头、空头、多空
        self.select_mode2 = SelectMode2.NUM            #选股模式2：按数量、按比例
        self.mask = ""                                 #筛选条件：1：筛掉，2：放入待选股票池
        self.deal = "open"                             #成交价格，在Flexible模式下则自己设定
        self.rate = 0.0                                #手续费
        self.slippage = 0.0                            #滑点，单位:元
        self.Interval = Interval.DAY                   #数据频率
        self.benchmark = "IF"                          #策略基准，IF,IH,IC
        self.data_lens = 10                            #获取历史数据长度
        self.stock_pool = "all"                        #"all"表示所有股票，其他按index_list来
        self.capital = 10000000                        #初始资金
        self.open_close = OpenClose.Open               #回测按开盘时还是收盘时，还是两者都要
        
        """适应多因子的情况"""
        self.origin_factor_dict = {}
        self.factor_dict = {}                          #字典，因子名：因子值df
        self.factor_list = []                          #列表，因子名
        self.daily_pos = None                          #盈亏管理
		
        self.datetime_list = None                      #回测时间点
        self.history_data = None                       #历史数据
        self.stock_pool = None
        self.data = {}                                 #用于计算的历史数据
        self.current_time = None                       #当前时间点
        self.last_date = None                          #昨天
        self.current_date = None                       #今天
        
        self.data_inited = False
        
        self.selection_dict = {}
        
        self.pos = None
        self.bars_since_start = 0
									   
    def set_strategy_params(self, settings: dict):
        """设置策略参数"""
        for name in settings:
            if name in self.parameters:
                if name == "start" or name == "end":
                    setattr(self, name, self.stand_date(settings[name]))
                else:
                    setattr(self, name, settings[name])
													  
    @abstractmethod
    def initialize(self):
        raise NotImplementedError
    
    @abstractmethod
    def handle_bar_start(self):       #新一个bar开始时，一般就是新的交易日开盘时，此时最新的数据是当前bar的开盘价
        raise NotImplementedError
	
    @abstractmethod
    def handle_bar_end(self):         #新一个bar结束时，一般就是新的交易日收盘时，此时最新的数据是当前bar的收盘价
        raise NotImplementedError
	
    @lru_cache(maxsize=999)
    def init_data_shape(self):
        self.data_shape = self.backtesting_engine.get_basics_data("Open()").shape
        return self.data_shape
    
    def update_stock_pool(self):
        self.current_stock_pool = self.stock_pool_df.loc[self.current_date]
            
    @lru_cache(maxsize=999)
    def init_stock_pool(self):
        if self.stock_pool == "all":
            self.stock_pool_df = self.backtesting_engine.get_basics_data("Open()")
            self.stock_pool_df[~np.isnan(self.stock_pool_df)] = 1.0
            self.stock_pool_df.fillna(0.0,inplace=True)
        else:
            self.stock_pool_df = self.backtesting_engine.get_basics_data(self.stock_pool)
            self.stock_pool_df.fillna(0.0,inplace=True)
            
    @lru_cache(maxsize=999)
    def init_all_datetime_list(self):
        self.all_datetime_list = list(self.backtesting_engine.get_basics_data("Open()").index)
        return self.all_datetime_list
    
    @property
    def IfBenchmarkOpen(self):
        return self.history_data["IfBenchmarkOpen()"].loc[self.data_begin_date:self.data_end_date,:]
    
    @property
    def IfBenchmarkClose(self):
        if self.current_time.hour == 9:
            return self.history_data["IfBenchmarkClose()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["IfBenchmarkClose()"].loc[self.data_begin_date:self.data_end_date,:]
        
    @property
    def IcBenchmarkOpen(self):
        return self.history_data["IcBenchmarkOpen()"].loc[self.data_begin_date:self.data_end_date,:]
    
    @property
    def IcBenchmarkClose(self):
        if self.current_time.hour == 9:
            return self.history_data["IcBenchmarkClose()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["IcBenchmarkClose()"].loc[self.data_begin_date:self.data_end_date,:]
	
    @property
    def Open(self):
        return self.history_data["Open()"].loc[self.data_begin_date:self.data_end_date,:]
	
    @property
    def High(self):
        if self.current_time.hour == 9:
            return self.history_data["High()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["High()"].loc[self.data_begin_date:self.data_end_date,:]
	
    @property
    def Low(self):
        if self.current_time.hour == 9:
            return self.history_data["Low()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["Low()"].loc[self.data_begin_date:self.data_end_date,:]
		
    @property
    def Close(self):
        if self.current_time.hour == 9:
            return self.history_data["Close()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["Close()"].loc[self.data_begin_date:self.data_end_date,:]
		
    @property
    def Volume(self):
        if self.current_time.hour == 9:
            return self.history_data["Volume()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["Volume()"].loc[self.data_begin_date:self.data_end_date,:]
		
    @property
    def DealAmount(self):
        if self.current_time.hour == 9:
            return self.history_data["DealAmount()"].loc[self.data_begin_date:self.data_yes_date,:]
        elif self.current_time.hour == 15:
            return self.history_data["DealAmount()"].loc[self.data_begin_date:self.data_end_date,:]
			
    def mask_filter(self, factor):
        self.select_stock_dict[factor].mask_filter()
    
    def add_factor(self, factor: str):
        value = self.backtesting_engine.add_factor(factor)
        self.update_factor(factor, value)
        return value
		
    def update_factor(self, factor, value):
        self.factor_dict[factor] = value
        self.origin_factor_dict[factor] = value
        self.factor_list.append(factor)
        self.backtesting_engine.select_stock_dict[factor] = SelectStock(self.backtesting_engine, factor)
		
    def get_history_data(self, field):
        return self.backtesting_engine.get_history_data(self.strategy_name, field)
    
    def change_pos(self, trade_mode, pos_dict: dict):
        """"""
        self.backtesting_engine.change_pos(self, trade_mode, pos_dict)
        
    def target_pos(self, trade_mode, target_pos_dict: dict):
        """"""
        self.backtesting_engine.target_pos(self, trade_mode, target_pos_dict)
        
    def change_value(self, trade_mode, value_dict: dict):
        """"""
        self.backtesting_engine.change_value(self, trade_mode, value_dict)
        
    def target_value(self, trade_mode, target_value_dict: dict):
        """"""
        self.backtesting_engine.target_value(self, trade_mode, target_value_dict)
        
    def init_strategy_value_df(self):
        """第一个回测时间点初始化仓位"""
        if self.bars_since_start == 0:
            current_time = self.current_time
            stock_pool_lens = len(self.current_stock_pool)
            initial_value_df = pd.Series(np.zeros((stock_pool_lens,)),index=list(self.current_stock_pool.index))
            
            self.pos.init_pos_df[current_time] = initial_value_df
            self.pos.pos_df[current_time] = initial_value_df
            self.pos.init_value_df[current_time] = initial_value_df
            self.pos.value_df[current_time] = initial_value_df
            self.pos.trading_pos_df[current_time] = initial_value_df
            self.pos.trading_value_df[current_time] = initial_value_df
            self.pos.commission_df[current_time] = initial_value_df
            self.pos.slippage_df[current_time] = initial_value_df
            
            self.pos.bars_record_df[current_time] = pd.Series([self.capital, self.capital, self.capital, self.capital, 0.0, 0.0, 0.0,0.0,0.0],
                                                   index=["init_capital","capital","init_cash","cash","init_portfolio","portfolio","commission","slippage","turnover"])
   
    def output(self, msg):
        print(f"{datetime.now()}——INFO——{self.current_time}——{msg}")
        
    def stand_date(self, date: str):
        def _stand_date1(date):#将日期形式转化成标准的datetime形式
            try:
                return datetime.strptime(date,"%Y-%m-%d")
            except:
                try:
                    return datetime.strptime(date,"%Y-%m-%d %H:%M")
                except:
                    return datetime.strptime(date,"%Y-%m-%d %H:%M:%S")
            
        def _stand_date2(date):#将tb的时间转化为有效的datetime的形式
            try:
                return datetime.strptime(date,'%Y/%m/%d %H:%M')
            except:
                try:
                    return datetime.strptime(date,'%Y/%m/%d')
                except:
                    return datetime.strptime(date,"%Y/%m/%d %H:%M:%S")
                
        def _stand_date3(date):
            try:
                return datetime.strptime(date,"%Y\%m\%d %H:%M")
            except:
                try:
                    return datetime.strptime(date,"%Y\%m\%d")
                except:
                    return datetime.strptime(date,"%Y\%m\%d %H:%M:%S")
        
        def _stand_date4(date):
            try:
                return datetime.strptime(date,"%m/%d/%Y")
            except:
                try:
                    return datetime.strptime(date,"%m/%d/%Y %H:%M")
                except:
                    return datetime.strptime(date,"%m/%d/%Y %H:%M:%S")
                
        try:
            return _stand_date1(date)
        except:
            try:
               return  _stand_date2(date)
            except:
                try:
                    return _stand_date3(date)
                except:
                    return _stand_date4(date)
    