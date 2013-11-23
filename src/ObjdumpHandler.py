import re
from Instruction import Instruction
from InstructionSequence import InstructionSequence


def extract_functions_from_objdump_lines(objdump_lines):
    """Returns a list of ObjdumpFunctions created by parsing lines from objdump output's .text section"""
    # we only care about the .text section, so we'll find where it is so we know where to start from
    start_of_text_section = 0
    for i in xrange(len(objdump_lines)):
        if objdump_lines[i] == "Disassembly of section .text:\n":
            start_of_text_section = i+2
            break

    functions = []
    function = None
    for line in objdump_lines[start_of_text_section:]:
        if ObjdumpFunction.FIRST_LINE_PATTERN.match(line):
            function = ObjdumpFunction(line)
        elif Instruction.INSTRUCTION_LINE_PATTERN.match(line):
            function.add_instruction(line)
        elif line == "\n":
            # no long in a function block
            if function:
                # if we were in the process of building a function, add it to the list and reset it
                function.extract_jump_blocks()
                functions.append(function)
                function = None
        elif line.startswith("Disassembly of section"):
            # we hit a section that isn't .text, we're done here
            break
    return functions


class ObjdumpFunction(InstructionSequence):
    FIRST_LINE_PATTERN = re.compile(r'^([0-9a-f]+) <(.+)>:')
    # looks for operator and operands expression in string from command line arg
    INSTRUCTION_EXPRESSION_PATTERN = re.compile(r'(?P<operator>[a-z]+)\s(?P<operandExpression>[a-z0-9\*]{2}).*')

    def __init__(self, first_line):
        """Initializes a new ObjdumpFunction object

        first_line -- string from the first line of a function from objdump output that contains its name and start offset
        """
        InstructionSequence.__init__(self)
        self.start, self.name = ObjdumpFunction.FIRST_LINE_PATTERN.findall(first_line)[0]
        self.jump_blocks = []

    def add_instruction(self, line):
        """Adds an instruction object (initialized from line) to self.instructions

        line -- string from objdump output with which to instantiate a new instruction object
        """
        self.instructions.append(Instruction(line))

    # todo: this can probably be done while we're adding lines
    def extract_jump_blocks(self):
        """Extracts suitable subsets from self.instructions and stores them in self.jump_blocks

         Suitable instruction subsets end in a jump instruction (plus branch delay slot instruction)
         and do not contain branch instructions.
         """
        i = 0
        block = []
        while i < len(self.instructions)-1:
            inst = self.instructions[i]
            block.append(inst)
            if inst.operator_type in ["JUMP", "BRANCH"]:
                # also grab the instruction after the jump or branch and increment the counter
                block.append(self.instructions[i+1])
                i += 1
                if inst.operator_type == "JUMP":
                    # only add jump blocks since branches would add complexity
                    # todo: make exclusion of branches configurable?
                    self.jump_blocks.append(block)
                block = []
            i += 1