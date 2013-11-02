import re


class Instruction:
    FIRST_LINE_PATTERN = re.compile(r'^([0-9a-f]+) <(.+)>\:')
    #                                     |offset        |   |hex inst |      |optr       |      |opd|
    INSTRUCTION_LINE_PATTERN = re.compile(r'\s*([a-f0-9]+)\:\s+[a-f0-9]{8}\s+(?:([a-z0-9]+)(?:\s+(.+))?)')

    OP_TYPES = {
        'ARITHMETIC': ['add', 'addu', 'addi', 'addiu', 'div', 'divu', 'mult', 'multu', 'sub', 'subu'],
        'SHIFT': ['sra', 'srav', 'srl', 'srlv', 'sll', 'sllv'],
        'LOGICAL': ['and', 'andi', 'nor', 'or', 'ori', 'xor', 'xori'],
        'COMPARISON': ['slt', 'slti', 'sltiu', 'sltu'],
        'BRANCH': ['bltz', 'bgezal', 'b', 'bnez', 'beq', 'bgez', 'bltzal', 'blez', 'beqz', 'bal', 'bgtz', 'bne'],
        'JUMP': ['j', 'jal', 'jalr', 'jr'],
        'LOAD': ['lb', 'lbu', 'lh', 'lhu', 'lw', 'lui', 'li', 'move', 'mflo', 'mfhi', 'mfc', 'mfc1', 'cfc', 'lwc0', 'lwc1', 'lwl', 'lwr'],
        'STORE': ['sb', 'sh', 'sw', 'swc'],
        'SYSCALL': ['syscall'],
        'OTHER': ['ctc', 'mtc', 'mtc1', 'lwc0', 'swc0', 'break', 'cvt', 'negu', 'swl', 'swr', 'mov', 'swc1', 'mul', 'c', 'bc1f', 'bc1t', 'cfc1', 'ctc1', 'mtlo', 'mthi']
    }

    NOT_FOUND = []

    CHANGE_OPS = ['ARITHMETIC', 'SHIFT', 'LOGICAL', 'LOAD']
    OPERATOR_TO_TYPE = {}

    @staticmethod
    def buildOperatorToTypeDict():
        """Builds a static dict mapping operator names to their types for easy lookup"""
        for operatorType in Instruction.OP_TYPES:
            for operator in Instruction.OP_TYPES[operatorType]:
                Instruction.OPERATOR_TO_TYPE[operator] = operatorType

    def __init__(self, line):
        """Initializes a new Instuction object

        line -- string consisting of a line from a function in objdump output that contains its offset, operator, and operands
        """
        offset, operator, operands = Instruction.INSTRUCTION_LINE_PATTERN.findall(line)[0]
        self.offset = offset
        self.operands = operands.split(',')
        self.operator = operator
        try:
            self.operatorType = Instruction.OPERATOR_TO_TYPE[self.operator]
        except(KeyError):
            self.operatorType = "NOT_FOUND"
            if self.operator not in Instruction.NOT_FOUND:
                Instruction.NOT_FOUND.append(self.operator)
                if not self.operator.startswith('0x'):
                    print "Unknown operator: %s at %s. Please submit a bug report." % (self.operator, self.offset)

    def __repr__(self):
        return "%s: %s %s" % (self.offset, self.operator, ",".join(self.operands))

Instruction.buildOperatorToTypeDict() #TODO: find out how to run this statically