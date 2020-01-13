# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 14:54:19 2019

@author: Administrator
"""
from lfpy.trader.constant import (
									SelectMode1,
									SelectMode2,
                                OpenClose)
from ..Template import Template

class A_Strategy(Template):
    
    def __init__(self, backtesting_engine, strategy_name):
        super(A_Strategy, self).__init__(backtesting_engine, strategy_name)
        
    def initialize(self):
        settings = {
					"start": "2015-01-01",
					"end": "2020-01-01",
					"n_long": 50,
					"n_short": 0,
					"pct_long": 0,
					"pct_short": 0,
					"select_mode1": SelectMode1.LONG,
					"select_mode2": SelectMode2.NUM,
					"mask": "tsmean(DealAmount,5)<50000000",
					"deal": "close",
					"rate": 0.002,
					"data_lens": 4,
                "stock_pool":"I000010()",
                "benchmark":"IF",
                "open_close": OpenClose.Open,
					}
					
        self.set_strategy_params(settings)
        
        self.add_factor("tsmean(Open/Close,5)")
        self.add_factor("Open/Close")
    
    def handle_bar_start(self):
        """在一根Bar开始时调用"""
        
        """测试数据提取接口"""
        #print(self.current_time)
        #print(self.current_date)
        #print(self.last_date)
        #print(self.get_history_data(["Open", "tsmean(Open/close)"]))
        #print(self.get_history_data(["Open"]))
        #print(self.current_stock_pool)
        #print(self.Open)
        #print(self.High)
        #print(self.Low)
        #print(self.Close)
        #print(self.IfBenchmarkOpen)
        #print(self.IfBenchmarkClose)
        #print(self.IcBenchmarkOpen)
        #print(self.IfBenchmarkClose)
        
        """一些方法"""
        #self.stock_pool
        #data_shape = self.data_shape
        #all_datetime_list = self.all_datetime_list
        #self.mask_filter("Open/Close")
        """一些下单接口"""
        current_stock_pool = self.current_stock_pool
        pos = {i:1000 if current_stock_pool.loc[i]>0 else 0 for i in current_stock_pool.index}
        #print(len([1 for i in current_stock_pool.index if current_stock_pool.loc[i]>0]))
        if self.current_date == self.datetime_list[0] and self.current_time.hour == 9:
            self.change_pos("current_bar", pos)
        self.output(self.pos.bars_record_df[self.last_time]["capital"])
        #self.Open
		
    def handle_bar_end(self):
        """在一根Bar结束时调用"""
        pass
        #print(self.current_time)
		
		
        