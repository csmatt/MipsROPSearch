import re
import Utils
from Instruction import Instruction

class ObjdumpFunction:

    def __init__(self, firstLine):
        self.start, self.name = Instruction.firstLinePattern.findall(firstLine)[0]
        self.instructions = []
        self.jumpBlocks = []

    def addLine(self, line):
        self.instructions.append(Instruction(line))

    # TODO: this can probably be done while we're adding lines
    def extractJumpBlocks(self):
        i = 0
        block = []
        while i < len(self.instructions)-1:
            inst = self.instructions[i]
            block.append(inst)
            if inst.operatorType in ["JUMP","BRANCH"]:
                # also grab the instruction after the jump or branch and increment the counter
                block.append(self.instructions[i+1])
                i += 1
                if inst.operatorType == "JUMP":
                    # only add jump blocks since branches would add complexity
                    # TODO: make exclusion of branches configurable?
                    self.jumpBlocks.append(block)
                block = []
            i += 1

    def checkChanged(self, instList, regList):
        for inst in instList:
            if inst.operatorType in Instruction.CHANGE_OPS and inst.operands[0] in regList:
                return True
        return False

    def search(self, patternStr, disallowedRegisters=[], jumpRegister=None):
        p = re.compile(r'(?P<operator>[a-z]+)\s(?P<reg>[a-z0-9\*]{2}).*')
        pMatch = p.match(patternStr)
        pattern = {'operator': pMatch.group('operator'), 'reg': pMatch.group('reg')}
        ropGadgets = []

        for block in self.jumpBlocks:
            # if jumpRegister is specified, make sure this block jumps to that register. if it doesn't, move on to the next block
            if jumpRegister and block[-2].operands[0] != jumpRegister: continue

            regLastChange = {}
            # go through the instructions in reverse order to find the last time a particular register is changed in a jump block
            # put that register in regLastChange and map it to the index of the instruction where it's last changed
            for instIndex in range(len(block)-1,0,-1):
                if block[instIndex].operatorType in Instruction.CHANGE_OPS:
                    if block[instIndex].operands[0] not in regLastChange:
                        regLastChange[block[instIndex].operands[0]] = instIndex

            # get the destination register from the incoming string
            regDesiredStr = pattern.get('reg')

            if regDesiredStr[1] == "*":
                # handle wildcard destination register ("**" for all a,s,and t registers or the register group and a "*"- ex: "s*")
                regesDesired = Utils.buildRegisterListFromPattern( "a*,s*,t*,ra" if regDesiredStr[0] == "*" else regDesiredStr )
            else:
                regesDesired = [regDesiredStr]

            for regDesired in regesDesired:
                # if the destination register we're looking for isn't in this jump block, this block is useless, so continue
                if regDesired not in regLastChange or block[regLastChange[regDesired]].operator != pattern.get('operator'): continue

                # there's a chance that the last time our register is changed is the instruction after the jump.
                # if that's the case, we also need to include the jump in the ropBlock, so set startFrom to the jump instruction, otherwise, start from where the register is last changed
                ropGadgetStart = len(block)-2 if regLastChange[regDesired] == len(block)-1 else regLastChange[regDesired]

                if block[regLastChange[regDesired]].operator == pattern.get('operator'):
                    # cool, the register we wanted changed was changed and by the operator we wanted
                    ropBlock = block[ropGadgetStart:len(block)]
                    # however, we want to make sure that none of the registers we didn't want changed were affected.
                    # that will be the final determining factor in whether this is a good rop gadget
                    if not self.checkChanged(ropBlock,disallowedRegisters):
                        ropGadgets.append(ropBlock)
        Utils.printList(ropGadgets)