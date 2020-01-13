# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 11:21:04 2019

@author: Administrator
"""

import numpy as np
import pandas as pd
from copy import deepcopy

from lfpy.trader.constant import (SelectMode1,
                                  SelectMode2
                                  )

from .ResultStatistic import ResultStatistic

class SelectStock:
    
    parameters = ["n_long",
				"n_short",
				"pct_long",
				"pct_short",
				"freq",
				"select_mode1",
				"select_mode2",
              "stock_pool",
				"mask"]
    
    def __init__(self, backtesting_engine, factor):
        """一个SelectStock接受单因子"""
        """选股参数"""
        self.n_long = 50                              #做多组合的股票数量
        self.n_short = 0                              #做空组合的股票数量
        self.pct_long = 0.2                           #做多组合的股票比例
        self.pct_short = 0                            #做空组合的股票比例
        self.freq = 1                                 #换仓频率
        self.select_mode1 = SelectMode1.LONG          #LONG:仅做多，SHORT:仅做空，LONG_SHORT:多空
        self.select_mode2 = SelectMode2.NUM           #NUM:按数量选股，PCT:按比例选股
        self.stock_pool = "all"                       #股票池
        self.mask = ""                                #mask:筛选字符串，符合mask条件的股票会被删去
        
        self.backtesting_engine = backtesting_engine
      
        self.compute_engine = self.backtesting_engine.compute_engine               #因子计算引擎
        self.result_stat = ResultStatistic(self)
        
        self.factor = factor
        self.origin_factor_data = self.backtesting_engine.origin_factor_dict[factor]
        self.factor_data = self.backtesting_engine.factor_dict[factor]
        
        self.init_zero_df()
        
    def init_stock_pool(self):
        if self.stock_pool == "all":
            self.stock_pool_df = deepcopy(self.backtesting_engine.get_basics_data("Open()"))
            self.stock_pool_df[~np.isnan(self.stock_pool_df)] = 1.0
            self.stock_pool_df.fillna(0.0,inplace=True)
        else:
            self.stock_pool_df = deepcopy(self.backtesting_engine.get_basics_data(self.stock_pool))
            self.stock_pool_df.fillna(0.0,inplace=True)
        
    def result_stats(self):
        self.result_stat.return_cal()
        self.result_stat.calculate_indice()
        return self.result_stat.indices
    
    def show_chart(self):
        self.result_stat.plot()
	
    @property
    def datetime_list(self):
        return self.backtesting_engine.datetime_list 
	
    def compute_factor(self, factor):
        """计算因子"""
        value = self.compute_engine.compute_factor(factor)
        return value
    
    def set_parameters(self):
        """"""
        for name in self.parameters:
            setattr(self, name, getattr(self.strategy, name))
    
    def init_zero_df(self):
        self.init_zero_df = pd.DataFrame(np.zeros(self.factor_data.shape),index=self.factor_data.index,columns=self.factor_data.columns)
    
    def mask_filter(self):
        """
        筛选条件过滤,
        将被筛选掉的股票的因子值设置为缺失值，
        这样后续选股的时候就不会被选中,
        这也意味着该步骤必须先于因子选股运行。
        """
        mask = self.mask
        
        if mask == "":
            mask_value = self.init_zero_df
            self.mask_value = mask_value
            
        else:
            mask_value = self.compute_factor(mask)
            self.mask_value = mask_value.fillna(1.0)
        
        self.init_stock_pool()
        self.mask_value[self.stock_pool_df == 0.0] = 1.0
			
        self.update_factor(self.factor, self.mask_value)

        return mask_value
		
    def update_factor(self, factor, mask_value):
        self.backtesting_engine.factor_dict[factor][mask_value == 1.0] = np.nan
        self.factor_data[mask_value == 1.0] = np.nan
	
    def init_num(self):
        """"""
        factor_data = self.factor_data
        lens = len(self.datetime_list)
        
        n_long = self.n_long
        n_short = self.n_short
        
        """每一个Bar的可选股票数目"""
        number = factor_data.count(axis=1)
        self.number = number
        
        """selection是从第几个Bar开始有计数的"""
        isnan=np.isnan
        for i in range(len(factor_data.index)):
            if len(factor_data.values[i,:][isnan(factor_data.values[i,:])])<len(factor_data.columns):
                print(i)
                temp=i
                self.temp=temp
                break
        
        if self.select_mode2 == SelectMode2.NUM:
            
            if self.select_mode1 == SelectMode1.LONG:
                n1 = pd.Series([n_long]*lens,index=number.index)
                n2 = pd.Series([0.0]*lens,index=number.index)
                
            elif self.select_mode1 == SelectMode1.SHORT:
                n1 = pd.Series([0.0]*lens,index=number.index)
                n2 = pd.Series([n_short]*lens,index=number.index)
                
            elif self.select_mode1 == SelectMode1.LONG_SHORT:
                n1 = pd.Series([n_long]*lens,index=number.index)
                n2 = pd.Series([n_short]*lens,index=number.index)
                
        elif self.select_mode2 == SelectMode2.PCT:
            
            if self.select_mode1 == SelectMode1.LONG:
                n1 = np.floor(number*self.pct_long)
                n2 = pd.Series([0.0]*lens,index=number.index)
          
            elif self.select_mode1 == SelectMode1.SHORT:
                n1 = pd.Series([0.0]*lens,index=number.index)
                n2 = np.floor(number*self.pct_short)
                
            elif self.select_mode1 == SelectMode1.LONG_SHORT:
                n1 = np.floor(number*self.pct_long)
                n2 = np.floor(number*self.pct_short)
                
        """将n1+n2大于可选股票的情况设置空仓"""
        judge = pd.Series([1.0]*len(number),index=number.index)
        judge[n1+n2>number] = 0.0
        n1[judge == 0.0] = 0.0
        n2[judge == 0.0] = 0.0
        
        self.n1 = n1
        self.n2 = n2
        self.lens = self.n1 + self.n2
        
        return n1, n2
    
    def sort_factor(self):
        """生成初步排序结果（没有根据调仓频率调整选股）"""
        
        n1 = self.n1
        n2 = self.n2
        
        factor_data = self.factor_data
        factor_long_data = deepcopy(factor_data)
        factor_short_data = -deepcopy(factor_data)
        
        factor_n1 = factor_long_data.fillna(-np.inf)
        select_n1 = factor_n1.rank(axis=1,method="first")
        
        selection = pd.DataFrame(np.zeros(factor_data.shape),index=factor_data.index,columns=factor_data.columns)
        
        selection[(select_n1.T>=len(select_n1.columns)-n1+1).T] = 1.0
        
        factor_n2 = factor_short_data.fillna(-np.inf)
        select_n2 = factor_n2.rank(axis=1,method="first")
        
        selection[(select_n2.T>=len(select_n2.columns)-n2+1).T] = -1.0
        
        self.selection = selection
        return selection
    
    def freq_temp_adjust(self):
        
        freq = self.freq
        temp = self.temp
                
        def group_func(n: int):
            if n>=0 and n<freq:
                return 0
            else:
                return int((n+freq-temp)/freq)
            
        selection = self.selection
        selection["num"] = [group_func(i) for i in range(len(selection))]
        cols = [i for i in selection.columns if i not in ["num"]]
        selection_d = selection[cols]
        adj_selection = selection_d.groupby(selection["num"]).first().add_prefix("adjusted_")
        selection = pd.merge(selection, adj_selection, left_on = "num", right_index = True)
        
        del selection["num"]
        selection = selection.loc[:,adj_selection.columns[0]:]
        selection.columns = [i.replace("adjusted_","") for i in selection.columns]
        
        selection[np.isnan(self.origin_factor_data)] = 0.0
        
        self.selection = selection
        
        return selection

    def cross_select(self):
        """"""
        self.mask_filter()
        self.init_num()
        
        factor_data = self.factor_data
        selection = pd.DataFrame(np.zeros(factor_data.shape),index=factor_data.index,columns=factor_data.columns)
        self.selection = selection
        
        self.sort_factor()
        self.freq_temp_adjust()    
       
        self.backtesting_engine.selection_dict[self.factor] = self.selection
        
        return self.selection
        
    def get_daily_select(self, date):
        """获取某一天的选股状况"""
        daily_selection = self.selection.loc[date, :]
        long_selection = list(daily_selection.loc[daily_selection == 1.0].dropna().index)
        short_selection = list(daily_selection.loc[daily_selection == -1.0].dropna().index)
        
        return long_selection, short_selection
    
    