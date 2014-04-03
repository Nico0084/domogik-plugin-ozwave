# -*- coding: utf-8 -*-

def form_Tamper_Event_to_DT_OpenClose(x):
    # "0" - "17" translated to 0 - 1
    if x == "0" : return int(0)
    elif x=="17" : return int(1)
    return 0
