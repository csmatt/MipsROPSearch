import re

def printList(l,depth=0,lastWasList=False):
    if type(l) == list:
        for i in l:
            printList(i,depth+1,True)
        if lastWasList:
            print ""
    else:
        print "%s%s" % ("\t"*depth, l)

def buildRegisterListFromPattern(registerListPattern):
    reThrough = re.compile(r'([a-z])([0-9])\-[a-z]([0-9])')
    reAllGroup = re.compile(r'([a-z])\*')
    reSingle = re.compile(r'([a-z0-9]{2})')
    registerListParts = registerListPattern.split(',')
    registerList = []
    for part in registerListParts:
        if reThrough.match(part):
            regGroup, regNumFrom, regNumTo = reThrough.findall(part)[0]
            for regNum in range(int(regNumFrom), int(regNumTo)+1):
                registerList.append("%s%s" % (regGroup, regNum))
        elif reAllGroup.match(part):
            regGroup = reAllGroup.findall(part)[0]
            for regNum in range(0, 10):
                registerList.append("%s%s" % (regGroup, regNum))
        elif reSingle.match(part):
            registerList.append(reSingle.findall(part)[0])
    return registerList