import re

REGISTER_LIST_THROUGH_PATTERN = re.compile(r'([a-z])([0-9])\-[a-z]([0-9])')
REGISTER_LIST_ALL_GROUP_PATTERN = re.compile(r'([a-z])\*')
REGISTER_LIST_SINGLE_PATTERN = re.compile(r'([a-z0-9]{2})')


def buildRegisterListFromPattern(registerListPattern):
    """Returns a list of register names created by expanding expressions defining one or more register names"""
    registerListParts = registerListPattern.split(',')
    registerList = []
    for part in registerListParts:
        if REGISTER_LIST_THROUGH_PATTERN.match(part):
            regGroup, regNumFrom, regNumTo = REGISTER_LIST_THROUGH_PATTERN.findall(part)[0]
            for regNum in xrange(int(regNumFrom), int(regNumTo)+1):
                registerList.append("%s%s" % (regGroup, regNum))
        elif REGISTER_LIST_ALL_GROUP_PATTERN.match(part):
            regGroup = REGISTER_LIST_ALL_GROUP_PATTERN.findall(part)[0]
            for regNum in xrange(0, 10):
                registerList.append("%s%s" % (regGroup, regNum))
        elif REGISTER_LIST_SINGLE_PATTERN.match(part):
            registerList.append(REGISTER_LIST_SINGLE_PATTERN.findall(part)[0])
    return registerList


def printList(l, depth=0, lastWasList=False):
    """Recursively prints contents of lists of lists"""
    if type(l) == list:
        for i in l:
            printList(i, depth+1, True)
        if lastWasList:
            print ""
    else:
        print "%s%s" % ("\t"*depth, l)