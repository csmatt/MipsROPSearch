import re
import Utils
from Instruction import Instruction

class ObjdumpFunction:
    # looks for operator and operands expression in string from command line arg
    INSTRUCTION_EXPRESSION_PATTERN = re.compile(r'(?P<operator>[a-z]+)\s(?P<operandExpression>[a-z0-9\*]{2}).*')

    def __init__(self, firstLine):
        """Initializes a new ObjdumpFunction object

        firstLine -- string from the first line of a function from objdump output that contains its name and start offset
        """
        self.start, self.name = Instruction.FIRST_LINE_PATTERN.findall(firstLine)[0]
        self.instructions = []
        self.jumpBlocks = []

    def addInstruction(self, line):
        """Adds an Instruction object (initialized from line) to self.instructions

        line -- string from objdump output with which to instantiate a new instruction object
        """
        self.instructions.append(Instruction(line))

    # TODO: this can probably be done while we're adding lines
    def extractJumpBlocks(self):
        """Extracts suitable subsets from self.instructions and stores them in self.jumpBlocks

         Suitable instruction subsets end in a jump instruction (plus branch delay slot instruction)
         and do not contain branch instructions.
         """
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
        """Returns True if an instruction in instList changes the value of any registers in regList

        instList -- list of Instruction objects
        regList -- list of register name strings
        """
        for inst in instList:
            if inst.operatorType in Instruction.CHANGE_OPS and inst.operands[0] in regList:
                return True
        return False

    def searchForRegisterChangeInJumpBlock(self, block, operator, regDesired, regLastChange, disallowedRegisters, ropGadgets):
        """Adds jump block to ropGadgets if criteria is met

        Criteria: operator and regDesired match an instruction,
                  no register in disallowedRegisters has its value changed after matching instruction

        block -- jump block (list of Instruction objects)
        operator -- string that a qualifying instruction's operator will match
        regDesired -- string that a qualifying instruction's destination register operand will match
        regLastChanged -- dict mapping register names to the index in block where that register's value was updated (closest to the jump)
        disallowedRegisters -- list of registers whose values cannot be changed in instructions after a qualifying instruction
        ropGadgets -- list to add this block or the qualifying portion of it to if all criteria is met
        """
        # there's a chance that the last time our register is changed is the instruction after the jump.
        # if that's the case, we also need to include the jump in the ropBlock, so set startFrom to the jump instruction, otherwise, start from where the register is last changed
        ropGadgetStart = len(block)-2 if regLastChange[regDesired] == len(block)-1 else regLastChange[regDesired]

        if block[regLastChange[regDesired]].operator == operator:
            # cool, the register we wanted changed was changed and by the operator we wanted
            ropBlock = block[ropGadgetStart:]
            # however, we want to make sure that none of the registers we didn't want changed were affected.
            # that will be the final determining factor in whether this is a good rop gadget
            if not self.checkChanged(ropBlock, disallowedRegisters):
                ropGadgets.append(ropBlock)

    def search(self, patternStr, disallowedRegisters=None, jumpRegister=None):
        """Searches for and returns portions of jump blocks that match criteria

        Criteria: match instruction pattern in patternStr,
                  none of disallowedRegisters changed after instruction,
                  jump instruction must jump to jumpRegister (if not None)

        patternStr -- user input string containing the operator and an expression to match the first operand against
        disallowedRegisters -- optional list of registers that must not be changed in instructions after a patternStr match
        jumpRegister -- optional string name of the register the jump instruction must jump to
        """
        if not disallowedRegisters: disallowedRegisters = []

        pMatch = ObjdumpFunction.INSTRUCTION_EXPRESSION_PATTERN.match(patternStr)
        pattern = {'operator': pMatch.group('operator'), 'operandExpression': pMatch.group('operandExpression')}
        ropGadgets = []

        # get the destination register from the incoming string
        regDesiredStr = pattern.get('operandExpression')

        if regDesiredStr[1] == "*":
            # handle wildcard destination register ("**" for all a,s,and t registers or the register group and a "*"- ex: "s*")
            regesDesired = Utils.buildRegisterListFromPattern("a*,s*,t*,ra" if regDesiredStr[0] == "*" else regDesiredStr)
        else:
            regesDesired = [regDesiredStr]

        for block in self.jumpBlocks:
            # if jumpRegister is specified, make sure this block jumps to that register. if it doesn't, move on to the next block
            if jumpRegister and block[-2].operands[0] != jumpRegister:
                continue

            regLastChange = {}
            # go through the instructions in reverse order to find the last time a particular register is changed in a jump block
            # put that register in regLastChange and map it to the index of the instruction where it's last changed
            for instIndex in xrange(len(block)-1, 0, -1):
                if block[instIndex].operatorType in Instruction.CHANGE_OPS:
                    if block[instIndex].operands[0] not in regLastChange:
                        regLastChange[block[instIndex].operands[0]] = instIndex

            for regDesired in regesDesired:
                if Instruction.OPERATOR_TO_TYPE.get(pattern.get('operator')) in Instruction.CHANGE_OPS:
                    # if the destination register we're looking for isn't in this jump block, this block is useless, so continue

                    if regDesired in regLastChange and block[regLastChange[regDesired]].operator == pattern.get('operator'):
                        self.searchForRegisterChangeInJumpBlock(block, pattern.get('operator'), regDesired, regLastChange, disallowedRegisters, ropGadgets)
                else:
                    ropGadgetStart = 0
                    for reg in regLastChange:
                        if reg in disallowedRegisters:
                            if regLastChange.get(reg) > ropGadgetStart:
                                ropGadgetStart = regLastChange.get(reg)

                    if ropGadgetStart > 0:
                        # add 1 to start at the instruction after the disallowed register's value change occurred
                        ropGadgetStart += 1

                    # loop through the instructions and add instructions from block
                    # starting from an instruction containing a matching operator and operand
                    for instIndex in xrange(ropGadgetStart, len(block)):
                        if pattern.get('operator') == block[instIndex].operator and regDesired == block[instIndex].operands[0]:
                            # if we're on the last instruction, we need to start the block from 1 prior to include the jump
                            blockStartIndex = instIndex - 1 if instIndex == len(block) - 1 else instIndex
                            ropGadgets.append(block[blockStartIndex:])
                            break

        Utils.printList(ropGadgets)