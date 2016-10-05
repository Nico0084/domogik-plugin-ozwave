def from_DT_HeatingPilotWire_to_Level(x):
    if x == u"6":
        return 10
    if x == u"5":
        return 20
    if x == u"4":
        return 30
    if x == u"3":
        return 40
    if x == u"2":
        return 50
    if x == u"1":
        return 99
