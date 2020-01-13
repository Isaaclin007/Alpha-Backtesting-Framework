# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 14:42:13 2019

@author: Administrator
"""
import os
import pickle
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from functools import lru_cache

from lfpy.trader.stringtrans import body, repair
from lfpy.trader.main_compute import ComputeEngine
from lfpy.trader.constant import SelectMode1, StrategyMode, OrderMode, OpenClose
from lfpy.AlphaBacktesting.StrategyPos import StrategyPos, SeriesOrder
from lfpy.AlphaBacktesting.SelectStock import SelectStock

warnings.filterwarnings('ignore')

class BacktestingEngine:
    """"""
    
    def __init__(self):
        """"""
        self.compute_engine = ComputeEngine()   #初始化因子计算引擎
		
        self.strategy_dict = {}                 #字典，策略实例名：策略实例
        self.pos_dict = {}                      #字典，策略实例名：每日盈亏
        self.factor_dict = {}                   #字典，因子名：因子值
        self.factor_list = []                   #列表，因子名
        self.origin_factor_dict = {}
        self.select_stock_dict = {}
        self.selection_dict = {}           
        
        self.datetime_list = None
        
        self.data_path = Path(__file__).parent.parent.joinpath("trader/data")
        self.stock_data_path = self.data_path.joinpath("stock_data")
        self.index_fut_data_path = self.data_path.joinpath("index_fut_data")
        self.index_weight_data_path = self.data_path.joinpath("index_weight_data")
        
        self.last_date = None
        self.current_date = None
        self.last_time = None
        self.current_time = None
        
    def set_data_path(self, path):
        self.data_path = Path(path)
        self.stock_data_path = self.data_path.joinpath("stock_data")
        self.index_fut_data_path = self.data_path.joinpath("index_fut_data")
        self.index_weight_data_path = self.data_path.joinpath("index_weight_data")
        
    def get_data_path(self):
        return str(self.data_path)
		
    def add_factor(self, factor):
        """添加因子"""
        value = self.compute_factor(factor)
        self.update_factor(factor, value)
        return value
		
    def update_factor(self, factor, value):
        self.factor_dict[factor] = value
        self.origin_factor_dict[factor] = value
        self.factor_list.append(factor)
        self.select_stock_dict[factor] = SelectStock(self, factor)
	
    @lru_cache(maxsize=10)
    def compute_factor(self, factor: str):
        """"""
        value = self.compute_engine.compute_factor(factor)
        return value
    
    def add_strategy(self, strategy_class):
        
        strategy_name = strategy_class.__name__
        strategy = strategy_class(self, strategy_name)
        strategy.pos = StrategyPos(self, strategy)
        self.strategy_dict[strategy_name] = strategy
        self.pos_dict[strategy_name] = strategy.pos
        self.output(f"{strategy_name} has been inited")
        return strategy
		
    def dec_start_end(self, strategy):
        """管理回测起止时间"""
        start = strategy.start
        end = strategy.end
        start0 = self.datetime_list[0] #历史数据起始时间点
        end0 = self.datetime_list[-1]  #历史数据结束时间点
        """设定的起止时间超出范围，那么根据数据起止时间设置回测起止时间"""
        if start<start0:
            start = start0
        if end>end0:
            end = end0
        
        """如果时间没有在历史数据的时间点中"""
        array = np.sort(np.array(list(self.datetime_list)))
        if start not in self.datetime_list:
            start = array[array>strategy.start][0]
        if end not in self.datetime_list:
            end = array[array<strategy.end][-1]
            
        """设定最终的self.datetime_list"""
        strategy.actual_start = start
        strategy.actual_end = end
        
        try:
            strategy.datetime_list = self.datetime_list[self.datetime_list.index(start): self.datetime_list.index(end)+1]
        except:
            strategy.datetime_list = self.datetime_list[self.datetime_list.index(start): self.datetime_list.index(end)]
        self.output(f"时间戳已经调整完毕, start={strategy.actual_start}, end={strategy.actual_end}")
        return start, end, strategy.datetime_list
    
    def load_local_data(self, data_path):
        data_path = str(data_path)
        file_list = os.listdir(data_path)
        data = {}
        for file_name in file_list:
            name = file_name.replace(".pkl", "")
            file_path = data_path+"\\"+file_name
            with open(file_path,"rb") as f:
                data[name] = pickle.load(f)
        return data
    
    def get_local_basics_data(self, data: dict = None, align: str = "Open"):
        """获取本地基本元数据"""
        self.output("Loading data starts...")
        if not data:
            data = {}
            data.update(self.load_local_data(self.stock_data_path))
            data.update(self.load_local_data(self.index_fut_data_path))
            data.update(self.load_local_data(self.index_weight_data_path))
        
        self.compute_engine.get_local_basics_data(data)
        self.output("Loading data finishes")
        if align:
            self.align_all_data(align)
        key_0 = list(data.keys())[0]
        self.datetime_list = list(data[key_0].index)
        
    def align_basics_data(self, field1: str, field2: str, data = None, index_join = "outer", column_join = "outer", inplace=False):
        """如果两个field的数据的股票池没有一致，则一致化， 两种方式: outer并集，inner交集"""
        if not data:
            data1 = self.get_basics_data(field1)
            data2 = self.get_basics_data(field2)
        else:
            data1 = data[field1]
            data2 = data[field2]
        #先横向对齐
        data1, data2 = data1.align(data2, axis=1, join = column_join)
        data1, data2 = data1.align(data2, axis=0, join = index_join)
        if inplace and not data:
            self.update_basics_data({field1:data1})
            self.update_basics_data({field2:data2})
        elif inplace and data:
            raise ValueError("data cannot be replaced")
        return data1, data2
    
    def update_basics_data(self, data: dict):
        self.compute_engine.get_local_basics_data(data)
        
    def align_all_data(self, align_base="Open"):
        """将除指数以外的数据一致化"""
        data = self.get_basics_data()
        if align_base not in data.keys():
            align_base = repair(body(align_base))
        if align_base not in data.keys():
            raise ValueError(f"Align base {align_base} cannot be found")
        for field in data:
            if field == align_base:
                continue
            elif field in ["IcBenchmarkOpen()","IcBenchmarkClose()","IfBenchmarkOpen()",
                            "IfBenchmarkClose()","IhBenchmarkOpen()","IhBenchmarkClose()"]:
                continue
            else:
                self.align_basics_data(field1=align_base, field2=field, index_join="left",column_join="left",inplace=True)
        self.output("Align all data finishes")
        
    def get_history_data(self, strategy_name, field):
        if strategy_name not in self.strategy_dict:
            raise ValueError(f"There is no strategy named {strategy_name}")
            
        if not self.strategy_dict[strategy_name].history_data:
            self.init_history_data(strategy_name)
        
        strategy = self.strategy_dict[strategy_name]
        history_data = self.history_data
        #current_date = strategy.current_date
        current_time = strategy.current_time
        data = {}
        for name in field:
            name_1 = repair(body(name))
            if name_1 in history_data:
                if current_time.hour == 9 and current_time.minute == 30:
                    if "High" not in name and "Low" not in name and "Close" not in name and "Volume" not in name and "opeinterest" not in name:
                        data[name] = history_data[name_1].loc[strategy.data_begin_date:strategy.data_end_date]
                    else:
                        data[name] = history_data[name_1].loc[strategy.data_begin_date:strategy.data_yes_date]
                else:
                    data[name] = history_data[name_1].loc[strategy.data_begin_date:strategy.end_date]
        return data
    
    def dec_data_date(self, strategy):
        """确定可取的历史数据的起止时间"""
        if self.datetime_list.index(strategy.current_date)-strategy.data_lens+1>=0:
            strategy.data_begin_date = self.datetime_list[self.datetime_list.index(strategy.current_date)-strategy.data_lens+1]
        else:
            strategy.data_begin_date = self.datetime_list[0]
        strategy.data_end_date = self.datetime_list[self.datetime_list.index(strategy.current_date)]
        strategy.data_yes_date = self.datetime_list[self.datetime_list.index(strategy.current_date)-1]
		
    def init_history_data(self, strategy_name):
        if strategy_name not in self.strategy_dict:
            raise ValueError(f"There is no strategy named {strategy_name}")
        elif self.strategy_dict[strategy_name].history_data:
            return
        else:
            strategy = self.strategy_dict[strategy_name]
            strategy.initialize()
            """管理回测起止时间"""
            actual_start, actual_end, datetime_list = self.dec_start_end(strategy)                  #修正回测起止时间
		
            """获取历史数据并处理"""
            history_data = self.get_basics_data()         #获取历史数据
            self.history_data = history_data
            for name in history_data: 					  #处理基本元数据和因子数据
                history_data[name] = history_data[name].loc[actual_start:actual_end,:]
            for name in strategy.factor_dict:
                history_data[repair(body(name))] = strategy.factor_dict[name].loc[actual_start:actual_end,:]
            key_0 = list(history_data.keys())[0]
            strategy.datetime_list = list(history_data[key_0].index)
            strategy.history_data = history_data
            
            strategy.init_stock_pool()
            strategy.init_data_shape()
            strategy.init_all_datetime_list()
            
            
            self.output(f"The history data of {strategy_name} has been inited")
            return history_data
			
    def runBacktesting(self, strategy_name):
        """Flexible模式下回测"""
        strategy = self.strategy_dict[strategy_name]  #提取策略
        if not strategy.history_data:
            self.init_history_data(strategy_name)
        strategy.bars_since_start = 0                 #回测计数归零
        if not strategy.strategy_mode == StrategyMode.Flexible:
            raise TypeError("Only a flexible strategy can backtest in this way.")
        
        self.init_history_data(strategy_name)
        
        """开始回测"""
        self.output("Backtesting starting......")
        key_0 = list(strategy.history_data.keys())[0]
        base = strategy.history_data[key_0]
        datetime_list = strategy.datetime_list
        for k in base.itertuples():
            
            """先更新时间"""
            i = k[0]
            if i == datetime_list[0]:
                strategy.current_date = i.replace(hour=0,minute=0)
                strategy.last_date = i.replace(hour=0,minute=0)
            else:
                strategy.last_date = deepcopy(strategy.current_date)
                strategy.current_date = i.replace(hour=0,minute=0)
            
            """确定可取的历史数据的起止时间点"""
            self.dec_data_date(strategy)
            
            """回测处理"""
            self.new_bar(strategy)
        
        """回测结果分析"""
        strategy.pos.init_pos_df = pd.DataFrame(strategy.pos.init_pos_df).T
        strategy.pos.pos_df = pd.DataFrame(strategy.pos.pos_df).T
        strategy.pos.init_value_df = pd.DataFrame(strategy.pos.init_value_df).T
        strategy.pos.value_df = pd.DataFrame(strategy.pos.value_df).T
        strategy.pos.trading_pos_df = pd.DataFrame(strategy.pos.trading_pos_df).T
        strategy.pos.trading_value_df = pd.DataFrame(strategy.pos.trading_value_df).T
        strategy.pos.commission_df = pd.DataFrame(strategy.pos.commission_df).T
        strategy.pos.slippage_df = pd.DataFrame(strategy.pos.slippage_df).T
        strategy.pos.bars_record_df = pd.DataFrame(strategy.pos.bars_record_df).T
            
        self.output("Backtesting finishes......")
        self.output("开始计算策略统计指标")
        strategy.pos.calculate_result()
        strategy.pos.show_chart()
                      
    def new_bar(self, strategy):
        strategy.update_stock_pool()
        if strategy.open_close != OpenClose.Close:
            if strategy.bars_since_start == 0:
                strategy.last_time = strategy.current_date.replace(hour=9,minute=30)
                strategy.current_time = strategy.current_date.replace(hour=9,minute=30)          #开盘时刻
                strategy.init_strategy_value_df()
            else:
                strategy.last_time = deepcopy(strategy.current_time)
                strategy.current_time = strategy.current_date.replace(hour=9,minute=30)
            strategy.bars_since_start += 1
            strategy.handle_bar_start()   
            self.cross_order(strategy)
        
        if strategy.open_close != OpenClose.Open:
            strategy.last_time = deepcopy(strategy.current_time)
            strategy.current_time = strategy.current_date.replace(hour=15,minute=0)          #收盘时刻
            strategy.bars_since_start += 1
            strategy.handle_bar_end()                                                        #收盘回调函数
            self.cross_order(strategy)
    
    def cross_order(self, strategy):
        
        """
        计算回测时间点开始时的相关情况（已进入当前Bar，但是尚未交易）：
        1.每只股票的手数  init_pos_df
        2.每只股票的价值  init_value_df
        3.init_capital
        4.init_cash
        5.init_portfolio
        """
        #当前时间
        
        #获取回测时间点开始时的每只股票的手数
        if strategy.bars_since_start == 1:
            init_current_series_pos = strategy.pos.pos_df[strategy.current_time].fillna(0)
            init_current_cash = strategy.pos.bars_record_df[strategy.current_time]["cash"]      
            init_current_portfolio = strategy.pos.bars_record_df[strategy.current_time]["portfolio"]
        else:
            init_current_series_pos = strategy.pos.pos_df[strategy.last_time].fillna(0)   #交易前的每只股票持仓手数
            init_current_cash = strategy.pos.bars_record_df[strategy.last_time]["cash"]
            init_current_portfolio = strategy.pos.bars_record_df[strategy.last_time]["portfolio"]
        
        current_series_pos = deepcopy(init_current_series_pos)                 #用于计算交易后的每只股票持仓手数
        
        #获取当前股票价格
        if strategy.current_time.hour == 9:
            current_stock_price = strategy.history_data["Open()"].loc[strategy.current_date]
        elif strategy.current_time.hour == 15:
            current_stock_price = strategy.history_data["Close()"].loc[strategy.current_date]
        
        #获取回测时间点开始时的每只股票的价值
        init_current_series_value = current_stock_price*current_series_pos*100 #交易前的每只股票持仓价值
        current_series_value = deepcopy(init_current_series_value)             #用于计算交易后的每只股票持仓价值
        
        #获得回测时间点开始时的cash
        current_cash = deepcopy(init_current_cash)                             #用于计算交易后的现金
        
        #获得回测时间点开始时的portfolio
        current_portfolio = deepcopy(init_current_portfolio)                             #用于计算交易后的总持仓价值
        
        #获得回测时间点开始时的capital
        init_current_capital = init_current_cash+init_current_portfolio        #交易前的总价值
        current_capital = deepcopy(init_current_capital)                       #用于计算交易后的总价值
        
        """
        当前回测时间点的交易，未考虑做空保证金
        并记录：
        1.current_series_pos, 交易后的每只过票手数
        2.current_series_value，交易后的每只股票持仓价值
        """
        
        for series_order in strategy.pos.series_orders[strategy.current_time]:
            order_mode = series_order.order_mode
            order_data = series_order.order_data

            if order_mode == OrderMode.ChangePos:
                current_series_pos += order_data
                series_trade_value = order_data*current_stock_price*100
                current_series_value += series_trade_value
                #如果仅做多，则需要适当调整（每一步都需要调整）
                if strategy.select_mode1 == SelectMode1.LONG:
                    current_series_pos[current_series_pos<0] = 0
                    current_series_value[current_series_value<0] = 0.0
                
            elif order_mode == OrderMode.ChangeValue:
                #先将买卖量调节为整数手，正数的向下取整，负数的向上取整
                current_series_pos += np.modf(order_data/(current_stock_price*100))[1]
                series_trade_value = (np.modf(order_data/(current_stock_price*100))[1])*current_stock_price*100
                current_series_value += series_trade_value
                #如果仅做多，则需要适当调整（每一步都需要调整）
                if strategy.select_mode1 == SelectMode1.LONG:
                    current_series_pos[current_series_pos<0] = 0
                    current_series_value[current_series_value<0] = 0.0
                
            elif order_mode == OrderMode.TargetPos:
                #先将target_pos调整为整数手，正数的向下取整，负数的向上取整
                order_data = np.modf(order_data)[1]
                #如果只做多，则需要将负值变为0
                if strategy.select_mode1 == SelectMode1.LONG:
                    order_data[order_data<0] = 0.0
                current_series_pos = deepcopy(order_data)
                current_series_value = order_data*current_stock_price*100
                
            elif order_mode == OrderMode.TargetValue:
                #先将target_pos调整为整数手，正数的向下取整，负数的向上取整
                current_series_pos = np.modf(order_data/(current_stock_price*100))[1]
                current_series_value = (np.modf(order_data/(current_stock_price*100))[1])*current_stock_price*100
                if strategy.select_mode1 == SelectMode1.LONG:
                    current_series_pos[current_series_pos<0] = 0
                    current_series_value[current_series_value<0] = 0.0
        
        """
        汇总：
        1.补充init_pos_df,init_value_df,init_cash,init_portfolio,init_capital
        2.补充pos_df, value_df, cash, portfolio, capital
        3.补充trading_pos_df, trading_value_df
        4.补充commission_df, commission,slippage_df,slippage
        """
        
        #trading_pos_df
        series_trading_pos = current_series_pos - init_current_series_pos
        #trading_value_df
        series_trading_value = current_series_value - init_current_series_value
        #slippage_df
        series_slippage = np.abs(series_trading_pos)*strategy.slippage
        #turnover
        if not init_current_portfolio:
            turnover = 0
        else:
            turnover = series_trading_pos.sum()/init_current_series_pos.sum()
        #slippage
        slippage = series_slippage.sum()
        #commission_df
        series_commission = np.abs(series_trading_value)*strategy.rate
        #commission
        commission = series_commission.sum()
        #portfolio
        current_portfolio = current_series_value.sum()
        #cash
        current_cash = init_current_cash-series_trading_value.sum()-commission
        #capital
        current_capital = current_cash+current_portfolio
        #bars_record_df
        bar_record = pd.Series([init_current_capital,current_capital,init_current_cash,current_cash,
                                    init_current_portfolio,current_portfolio,commission,slippage,turnover],
                                    index=["init_capital","capital","init_cash","cash","init_portfolio","portfolio","commission","slippage","turnover"])
        
        if strategy.bars_since_start == 1:
            strategy.pos.init_pos_df[strategy.current_time] = init_current_series_pos
            strategy.pos.pos_df[strategy.current_time] = current_series_pos
            strategy.pos.init_value_df[strategy.current_time] = init_current_series_value
            strategy.pos.value_df[strategy.current_time] = current_series_value
            strategy.pos.trading_pos_df[strategy.current_time] = series_trading_pos
            strategy.pos.trading_value_df[strategy.current_time] = series_trading_value
            strategy.pos.commission_df[strategy.current_time] = series_commission
            strategy.pos.slippage_df[strategy.current_time] = series_slippage
            
            strategy.pos.bars_record_df[strategy.current_time] = bar_record
        else:
            """方法一"""
            strategy.pos.init_pos_df[strategy.current_time] = init_current_series_pos
            strategy.pos.pos_df[strategy.current_time] = current_series_pos
            strategy.pos.init_value_df[strategy.current_time] = init_current_series_value
            strategy.pos.value_df[strategy.current_time] = current_series_value
            strategy.pos.trading_pos_df[strategy.current_time] = series_trading_pos
            strategy.pos.trading_value_df[strategy.current_time] = series_trading_value
            strategy.pos.commission_df[strategy.current_time] = series_commission
            strategy.pos.slippage_df[strategy.current_time] = series_slippage
            strategy.pos.bars_record_df[strategy.current_time] = bar_record
        
    def get_trade_time(self, strategy, trade_mode):
        """"""
        current_time = strategy.current_time
        current_date = strategy.current_date
        if trade_mode == "current_bar":
            return current_time
        elif trade_mode == "next_bar":
            if current_time.hour == 9:
                trade_time = current_date.replace(hour=15,minute=0)
                return trade_time
            elif current_time.hour == 15:
                trade_time == strategy.datetime_list[strategy.datetime_list.index(current_date)+1].replace(hour=9,minute=30)
                return trade_time
        elif trade_mode == "next_two_bar":
            trade_time = strategy.datetime_list[strategy.datetime_list.index(current_date)+1].replace(hour=current_time.hour,minute=current_time.minute)
            return trade_time
            
    def change_pos(self, strategy, trade_mode, pos_dict):
        """"""
        trade_time = self.get_trade_time(strategy, trade_mode)
        pos_series = pd.Series(pos_dict)
        series_order = SeriesOrder(trade_time,OrderMode.ChangePos,pos_series)
        strategy.pos.series_orders[trade_time].append(series_order)
    
    def target_pos(self, strategy, trade_mode, target_pos_dict):
        """"""
        trade_time = self.get_trade_time(strategy, trade_mode)
        pos_series = pd.Series(target_pos_dict)
        series_order = SeriesOrder(trade_time,OrderMode.TargetPos,pos_series)
        strategy.pos.series_orders[trade_time].append(series_order)

    def change_value(self, strategy, trade_mode, value_dict: dict):
        """"""
        trade_time = self.get_trade_time(strategy, trade_mode)
        pos_series = pd.Series(value_dict)
        series_order = SeriesOrder(trade_time,OrderMode.ChangeValue,pos_series)
        strategy.pos.series_orders[trade_time].append(series_order)
    
    def target_value(self, strategy, trade_mode, target_value_dict: dict):
        """"""
        trade_time = self.get_trade_time(strategy, trade_mode)
        pos_series = pd.Series(target_value_dict)
        series_order = SeriesOrder(trade_time,OrderMode.TargetValue,pos_series)
        strategy.pos.series_orders[trade_time].append(series_order)

    def get_basics_data(self, factor = None):
        """获取基本元数据"""
        value = self.compute_engine.factor_compute.get_value(factor)
        return value
		
    def output(self, msg):
        print(f"{datetime.now()} ——INFO—— {msg}")
        
    def select_stock(self, factor, settings=None):
        if factor not in self.factor_list:
            self.add_factor(factor)
        select_stock = self.select_stock_dict[factor]
        if settings:
            select_stock.set_parameters(settings)
        selection = select_stock.cross_select()
        return selection
    
    def calculate_result(self, factor, settings=None):
        select_stock = self.select_stock_dict[factor]
        if settings:
            select_stock.result_stat.set_parameters(settings)
        result = select_stock.result_stats()
        select_stock.result_stat.plot()
        return result