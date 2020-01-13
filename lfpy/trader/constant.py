# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 15:26:55 2019

@author: Administrator
"""

from enum import Enum

class SelectMode1(Enum):
    """"""
    LONG_SHORT = "多空"
    LONG = "做多"
    SHORT = "做空"
    
class SelectMode2(Enum):
    """"""
    NUM = "数量"
    PCT = "比例"
    
class Interval(Enum):
    """"""
    MINUTE = "分钟"
    HOUR = "小时"
    DAY = "天"
    WEEK = "周"
    MONTH = "月"
    
class StrategyMode(Enum):
    """"""
    Standard = "标准化"
    Flexible = "Flexible"
    
class OrderMode(Enum):
    """"""
    ChangePos = "change_pos"
    TargetPos = "target_pos"
    ChangeValue = "change_value"
    TargetValue = "target_value"
    
class OpenClose(Enum):
    """"""
    Open = "open"
    Close = "close"
    Both = "Both"