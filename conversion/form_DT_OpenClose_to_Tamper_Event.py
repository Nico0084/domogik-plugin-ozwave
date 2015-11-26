# -*- coding: utf-8 -*-

def form_DT_OpenClose_to_Tamper_Event(x):
    #   0 - 1 translated to "0" Close - "17" Open
    if int(x) == 0 : return "Close"
    else : return "Open"
