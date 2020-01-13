# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 09:49:40 2019

@author: Administrator
"""

from datetime import datetime

from .basics import basic_factors
from .stringtrans import body, repair
from .factor_compute import FactorCompute

class ComputeEngine:
    
    def __init__(self):
        
        self.factors = []
        
        self.factor_ftrans_map = {}
        self.factor_value_map = {}
        self.ftrans_value_map = {}
        
        self.init_compute_engine()
                
    def init_compute_engine(self):
        """初始化因子计算类"""
        self.factor_compute = FactorCompute()
        name_trans = {}
        for i in basic_factors:
            name_trans[i] = repair(body(i))
        self.name_trans = name_trans
        
    def set_basic_factor(self, factor: list):
        """设置基本元"""
        self.factor_compute.set_basic_factor(factor)
        
    def add_basic_factor(self, factor):
        """添加基本元"""
        self.factor_compute.add_basic_factor(factor)
        
    def remove_basic_factor(self, factor):
        """删除基本元"""
        self.factor_compute.remove_basic_factor(factor)
    
    def get_basic_factor(self):
        """获取基本元"""
        return self.factor_compute.get_basic_factor()
    
    def set_basics_trans(self, name_trans: dict):
        """设置名称转换字典"""
        self.name_trans = name_trans
        
    def add_basics_trans(self, name, trans_name):
        """添加名称转换"""
        self.name_trans[name] = trans_name
        
    def remove_basics_trans(self, name):
        """删除名称转换"""
        del self.name_trans[name]
        
    def compute_factor(self, factor: str):
        """因子计算"""
        self.factors.append(factor)
        
        factor_trans = repair(body(factor))
        self.factor_ftrans_map[factor] = factor_trans
        
        value = self.factor_compute.compute(factor)
        self.factor_value_map[factor] = value
        self.ftrans_value_map[factor] = value
        self.factor_compute.remove_value()          #计算完因子后将除基本元以外的数据删除，避免影响新因子计算的效率
        return value
    
    def get_local_basics_data(self, data: dict):
        """获取本地基本元数据"""
        for name in data:
            if name in self.name_trans:
                trans_name = self.name_trans[name]
                if not isinstance(data[name].index[0], datetime):
                    data[name].index = self.stand_index(data[name].index)
                self.factor_compute.set_value(trans_name, data[name])
            
            elif name in self.name_trans.values():
                if not isinstance(data[name].index[0], datetime):
                    data[name].index = self.stand_index(data[name].index)
                self.factor_compute.set_value(name, data[name])
                
    def stand_index(self, datelist):
        """
        将导入的数据的时间索引改成datetime格式
        """
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
        result=[]
        append=result.append
        
        for i in datelist:
            try:
                append(_stand_date1(i))
            except:
                try:
                    append(_stand_date2(i))
                except:
                    try:
                        append(_stand_date3(i))
                    except:
                        append(_stand_date4(i))
        result = sorted(result)
        return result