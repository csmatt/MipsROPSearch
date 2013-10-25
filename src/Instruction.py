import re

class Instruction:
    firstLinePattern = re.compile(r'^([0-9a-f]+) <(.+)>\:')
    #                                     |offset        |   |hex inst |      |optr  |      |opd|
    instructionLinePattern = re.compile(r'\s*([a-f0-9]+)\:\s+[a-f0-9]{8}\s+(?:([a-z]+)(?:\s+(.+))?)')
    operandsPattern = re.compile(r'[, ]')

    ARITHMETIC = ['add', 'addu', 'addi', 'addiu', 'div', 'divu', 'mult', 'multu', 'sub', 'subu']
    SHIFT = ['sra', 'srav', 'srl', 'srlv', 'sll', 'sllv']
    LOGICAL = ['and', 'andi', 'nor', 'or', 'ori', 'xor', 'xori']
    COMPARISON = ['slt', 'slti', 'sltiu', 'sltu']
    BRANCH = ['beq', 'bgtz', 'blez', 'bne','beqz','bnez','b','bltz','bgez','bltzal','bgezal']
    JUMP = ['j', 'jal', 'jalr', 'jr']
    LOAD = ['lb', 'lbu', 'lh', 'lhu', 'lw','li','lui','move', 'mflo', 'mfhi']
    STORE = ['sb', 'sh', 'sw']
    OTHER = ['nop', 'rdhwr', 'sync', 'll', 'sc', 'bal', 'syscall', 'break', 'clz', 'negu', 'teq', 'mul', 'mtlo', 'mthi', 'movz', 'movn', 'swl', 'swr', 'seb', 'ror', 'seh', 'mfc', 'mtc', 'mov', 'ext', 'sdc', 'ldc', 'c', 'bc', 'swc', 'lwc', 'cfc', 'ctc', 'ins', 'lwl', 'lwr', 'movf', 'cvt', 'madd', 'trunc']

    NOT_FOUND = []

    CHANGE_OPS = ['ARITHMETIC', 'SHIFT', 'LOGICAL', 'LOAD']
    OPERATOR_TO_TYPE = {}

    @staticmethod
    def buildOperatorToTypeMap():
        for operatorType in ['ARITHMETIC', 'SHIFT', 'LOGICAL', 'COMPARISON', 'BRANCH', 'JUMP', 'LOAD', 'STORE', 'OTHER']:
            for operator in Instruction.__dict__[operatorType]:
                Instruction.OPERATOR_TO_TYPE[operator] = operatorType

    def __init__(self, line):
        offset, operator, operands = Instruction.instructionLinePattern.findall(line)[0]
        self.offset = offset
        self.operator = operator
        try:
            self.operatorType = Instruction.OPERATOR_TO_TYPE[self.operator]
        except(KeyError):
            self.operatorType = "NOT_FOUND"
            if self.operator not in Instruction.NOT_FOUND:
                Instruction.NOT_FOUND.append(self.operator)
                print "Unknown operator: %s. Please submit a bug report." % self.operator
        self.operands = Instruction.operandsPattern.split(operands)

    def __repr__(self):
        return "%s: %s %s" % (self.offset, self.operator, ",".join(self.operands))

Instruction.buildOperatorToTypeMap() # todo: find out how to run this statically