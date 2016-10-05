def from_Level_to_DT_HeatingPilotWire(x):
    if int(x) <= 10:
        return u"6"
    if int(x) <= 20:
        return u"5"
    if int(x) <= 30:
        return u"4"
    if int(x) <= 40:
        return u"3"
    if int(x) <= 50:
        return u"2"
    if int(x) <= 99:
        return u"1"
    return "6"
