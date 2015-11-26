# -*- coding: utf-8 -*-

def form_Tamper_Event_to_DT_OpenClose(x):
    # "0" - "17" translated to 0 - 1
    if x in ["0", 0, "Close"] : return 0
    elif x in ["17", 17, "Open"] : return 1
    return 0
