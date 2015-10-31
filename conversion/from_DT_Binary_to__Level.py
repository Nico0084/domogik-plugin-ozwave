# -*- coding: utf-8 -*-

def from_DT_Binary_to_Level(x):
    # 0 - 1 translated to 0 - 255
    if x == 0: return 0
    else : return 255
