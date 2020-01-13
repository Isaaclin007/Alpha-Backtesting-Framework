# -*- coding: utf-8 -*-
"""
Created on Wed Jan  1 18:37:39 2020

@author: Administrator
"""
"""初始化回测引擎"""
from lfpy.AlphaBacktesting.BacktestingEngine import BacktestingEngine
#from lfpy.AlphaBacktesting.Strategies.A_Strategy import A_Strategy
self = BacktestingEngine()

"""导入数据"""
self.get_local_basics_data()
data = self.get_basics_data()

"""通用性回测"""
"""
strategy = self.add_strategy(A_Strategy)
start =time.time()
self.runBacktesting("A_Strategy")
end = time.time()
print(end-start)
"""
"""因子回测"""
factor = "tsmean(Close/Open,10)"
self.add_factor(factor)
self.select_stock(factor)
self.calculate_result(factor)

"""验证因子值，证明无误"""
from datetime import datetime
factor_data = self.origin_factor_dict[factor]
a = factor_data.loc[datetime(2018,1,10),:].sort_values(ascending=False)

"""验证mask,证明无误"""
s = self.select_stock_dict[factor]
b = s.selection
c = b.loc[datetime(2018,1,10)]
c[c>0].sort_index()

"""最后计算过程"""
#d = s.result_stat.selected_return_df
d = s.result_stat.return_per_bar
#d = s.result_stat.weight_df