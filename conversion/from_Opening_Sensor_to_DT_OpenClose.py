# -*- coding: utf-8 -*-

def from_Opening_Sensor_to_DT_OpenClose(x):
    # "0" - "1" inverse  to 1- 0
    if int(x) == 0 : return 1
    else : return 0
