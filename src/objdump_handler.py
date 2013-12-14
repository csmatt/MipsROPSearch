import re
import utils

ALL_JUMP_BLOCKS = []
OBJDUMP_FUNCTIONS = []


def parse_objdump_output_file(file_path):
    f = open(file_path, 'r')
    objdump_lines = f.readlines()
    f.close()
    extract_functions_from_objdump_lines(objdump_lines)


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
        if Function.FIRST_LINE_PATTERN.match(line):
            function = Function(line)
        elif Instruction.INSTRUCTION_LINE_PATTERN.match(line):
            function.add_instruction(line)
        elif line == "\n":
            # no longer in a function block
            if function:
                # if we were in the process of building a function, add it to the list and reset it
                function.extract_jump_blocks()
                functions.append(function)
                function = None
        elif line.startswith("Disassembly of section"):
            # we hit a section that isn't .text, we're done here
            break

    global OBJDUMP_FUNCTIONS
    OBJDUMP_FUNCTIONS = functions
    return functions


def find_function(name):
    """Returns a function in OBJDUMP_FUNCTIONS with the name specified"""
    for fxn in OBJDUMP_FUNCTIONS:
        if fxn.name == name:
            return fxn


def search(pattern_str, disallowed_registers=None, desired_jump_register=None):
    """Uses pattern_str to search for and return all matching """
    results = []
    pattern = InstructionSequence.extract_search_criteria(pattern_str)
    for instruction_sequence in ALL_JUMP_BLOCKS:
        result = instruction_sequence.search(pattern, disallowed_registers, desired_jump_register)
        if result:
            results.append(result)

    return results


class Function(object):
    """Provides a storage structure for functions extracted from objdump's output"""

    FIRST_LINE_PATTERN = re.compile(r'^([0-9a-f]+) <(.+)>:')

    def __init__(self, first_line):
        """
        first_line -- first line of a function from objdump output that contains its name and start offset
        """
        self.start, self.name = Function.FIRST_LINE_PATTERN.findall(first_line)[0]
        self.jump_blocks = []
        self.instructions = []

    def add_instruction(self, line):
        """Adds an instruction object (initialized from line) to self.instructions

        line -- string from objdump output with which to instantiate a new instruction object
        """
        self.instructions.append(Instruction(line))

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
                    self.jump_blocks.append(InstructionSequence(block))
                block = []
            i += 1

        global ALL_JUMP_BLOCKS
        ALL_JUMP_BLOCKS.extend(self.jump_blocks)


class Instruction(object):
    #                                          |offset   |    |raw inst   |    |optr       |      |opds|
    INSTRUCTION_LINE_PATTERN = re.compile(r'\s*([a-f0-9]+):\s+([a-f0-9]{8})\s+(?:([a-z0-9]+)(?:\s+(.+))?)')

    OP_TYPES = {
        'ARITHMETIC': ['add', 'addu', 'addi', 'addiu', 'div', 'divu', 'mult', 'multu', 'sub', 'subu'],
        'SHIFT': ['sra', 'srav', 'srl', 'srlv', 'sll', 'sllv'],
        'LOGICAL': ['and', 'andi', 'nor', 'or', 'ori', 'xor', 'xori'],
        'COMPARISON': ['slt', 'slti', 'sltiu', 'sltu'],
        'BRANCH': ['bltz', 'bgezal', 'b', 'bnez', 'beq', 'bgez', 'bltzal', 'blez', 'beqz', 'bal', 'bgtz', 'bne'],
        'JUMP': ['j', 'jal', 'jalr', 'jr'],
        'LOAD': ['lb', 'lbu', 'lh', 'lhu', 'lw', 'lui', 'li', 'move', 'mflo',
                 'mfhi', 'mfc', 'mfc1', 'cfc', 'lwc0', 'lwc1', 'lwl', 'lwr'],
        'STORE': ['sb', 'sh', 'sw', 'swc'],
        'SYSCALL': ['syscall'],
        'OTHER': ['nop', 'ctc', 'mtc', 'mtc1', 'lwc0', 'swc0', 'break', 'cvt', 'negu', 'swl', 'swr',
                  'mov', 'swc1', 'mul', 'c', 'bc1f', 'bc1t', 'cfc1', 'ctc1', 'mtlo', 'mthi']
    }

    NOT_FOUND = []

    CHANGE_OP_TYPES = ['ARITHMETIC', 'SHIFT', 'LOGICAL', 'LOAD']
    COPY_OPS = ['move', 'lw']
    OPERATOR_TO_TYPE = {}

    @staticmethod
    def _build_operator_to_type_dict():
        """Builds a static dict mapping operator names to their types for easy lookup"""
        for operator_type in Instruction.OP_TYPES:
            for operator in Instruction.OP_TYPES[operator_type]:
                Instruction.OPERATOR_TO_TYPE[operator] = operator_type

    def __init__(self, line):
        """
        line -- string consisting of a line from a function in objdump output that contains
                its offset, operator, and operands
        """
        offset, raw, operator, operands = Instruction.INSTRUCTION_LINE_PATTERN.findall(line)[0]
        self.offset = offset
        self.raw = raw
        self.operands = operands.split(',')
        self.operator = operator
        try:
            self.operator_type = Instruction.OPERATOR_TO_TYPE[self.operator]
        except KeyError:
            self.operator_type = "NOT_FOUND"
            if self.operator not in Instruction.NOT_FOUND:
                Instruction.NOT_FOUND.append(self.operator)
                if not self.operator.startswith('0x'):
                    print "Unknown operator: %s at %s. Please submit a bug report." % (self.operator, self.offset)

    def __repr__(self):
        return "%s: %s %s" % (self.offset, self.operator, ",".join(self.operands))

    def check_other_operands_match(self, desired_operands):
        """Returns true if self.operands[1:] match all operands specified in desired_operands[1:] in order

        For a match, strings in desired_operands do not have to match exactly, they only have to be a substring

        desired_operands -- list of strings to match in order against self.operands
        """
        instruction_operands_length = len(self.operands)
        desired_operands_length = len(desired_operands)

        if desired_operands_length > instruction_operands_length:
            # there's no way there's a match if the instruction doesn't have enough operands, return False
            return False

        for operand_index in xrange(1, desired_operands_length):
            if not desired_operands[operand_index] in self.operands[operand_index]:
                return False
        return True

Instruction._build_operator_to_type_dict()


class InstructionSequence(list):
    """Subclass of list specifically to store Instruction objects in order."""

    def __init__(self, instructions):
        """
        instructions -- list of Instruction objects ending with a jump and branch delay slot
        """
        list.__init__(self, instructions)

        # dict mapping register names to the index in self where that register's value was updated (closest to the jump)
        self.register_changes = {}
        # the register this sequence will eventually jump to
        self.jump_register = self[-2].operands[0]

        self._store_register_changes()

    def _store_register_changes(self):
        """Iterates over instructions in reverse order to find the last time a register is changed and stores the
        register name to the instruction's index in self.register_changes.
        """
        for inst_index in xrange(len(self)-1, -1, -1):
            if self[inst_index].operator_type in Instruction.CHANGE_OP_TYPES:
                if self[inst_index].operands[0] not in self.register_changes:
                    self.register_changes[self[inst_index].operands[0]] = inst_index

    @staticmethod
    def _makes_changes(instructions, register_list):
        """Returns True if an instruction in instructions changes the value of any registers in register_list

        instructions -- list of Instruction objects
        register_list -- list of register name strings
        """
        for inst in instructions:
            if inst.operator_type in Instruction.CHANGE_OP_TYPES and inst.operands[0] in register_list:
                return True
        return False

    @staticmethod
    def _is_copy_to_jump_register(instruction, jump_register):
        """Returns True if instruction is copying a value into jump_register in a way that allows for controlling jumps

        Ex: move t9,s0
        Ex: lw ra,172(sp)

        instruction -- an Instruction object
        jump_register -- the name of the register jumped to in the InstructionSequence containing instruction
        """
        if instruction.operator == 'move' and instruction.operands[0] == jump_register:
            return True
        if instruction.operator == 'lw' and instruction.operands[0] == jump_register and 'sp' in instruction.operands[1]:
            return True
        return False

    def _include_copy_to_jump_register(self, potential_match, disallowed_registers):
        """Tries to include a instruction that controls where this sequence will jump to, if possible.

        If an instruction controlling the jump exists and including it along with the instructions between it and
        potential_match does not change any disallowed registers, that list of instructions is returned.
        Or, if none of the disallowed registers were changed, the original list of instructions is returned.
        If disallowed registers were changed, None is returned.

        potential_match -- list of Instructions
        disallowed_registers -- list of registers that must not be changed in the list of Instructions returned
        """
        match = None
        start_index = len(self)-len(potential_match)
        new_start_index = self._get_last_change_to_jump_register(start_index)
        new_potential_match = self[new_start_index:]
        if (
            new_start_index != start_index and
            not InstructionSequence._makes_changes(new_potential_match, disallowed_registers)
        ):
            match = new_potential_match
        else:
            # there were no qualifying moves into the jump register prior to the matching instruction
            # make sure potential_match doesn't change disallowed registers
            if not self._makes_changes(potential_match, disallowed_registers):
                match = potential_match

        return match

    def _get_last_change_to_jump_register(self, index):
        """Attempts to find and return the index of the instruction closest to the jump that changed the jump register

        index -- the index to return if a qualifying move instruction is not found
        """
        last_change_of_jump_register = self.register_changes.get(self.jump_register)
        if (
            last_change_of_jump_register is not None and
            InstructionSequence._is_copy_to_jump_register(self[last_change_of_jump_register], self.jump_register) and
            index > last_change_of_jump_register
        ):
            return last_change_of_jump_register
        return index

    @staticmethod
    def extract_search_criteria(search_str):
        """Extracts the desired operator and operands, expanding a pattern for the first operand
           into a list of registers for the first operand.

        Returns a tuple (referred to as a 'search criteria tuple') of:
            operator, list of register names from expanding first operand pattern, list of original search operands

        search_str -- a string of the format: OPERATOR OPERAND1_PATTERN,OPERAND2
        """
        desired_operator, desired_operands_str = search_str.split()
        desired_operands = desired_operands_str.split(',')
        desired_first_operand_expression = desired_operands[0]

        if desired_first_operand_expression[1] == "*":
            # handle wildcard destination register
            # "**" for ra and all a,s,and t registers or the register group and a "*"- ex: "s*"
            pattern_argument = "a*,s*,t*,ra" if desired_operands[0][0] == "*" else desired_operands[0]
            desired_first_operand_registers = utils.build_register_list_from_pattern(pattern_argument)
        else:
            desired_first_operand_registers = [desired_operands[0]]

        return desired_operator, desired_first_operand_registers, desired_operands

    @staticmethod
    def get_search_criteria(pattern):
        """Returns a search criteria tuple

        pattern -- string in the 'search pattern' format or search criteria tuple
                   (see: InstructionSequence.extract_search_criteria())
        """
        if type(pattern) == str:
            pattern = InstructionSequence.extract_search_criteria(pattern)
        else:
            assert type(pattern) == tuple and len(pattern) == 3, "'pattern' must be a string or search criteria tuple"
        return pattern

    def instruction_matches(self, instruction_index, desired_operator, desired_first_operand_registers, desired_operands):
        """Returns True if the Instruction at self[instruction_index] matches the criteria of the 'desired' arguments"""

        instruction = self[instruction_index]
        return (
            instruction.operator == desired_operator and
            instruction.operands[0] in desired_first_operand_registers and
            instruction.check_other_operands_match(desired_operands) and
            self.register_changes.get(instruction.operands[0], -1) <= instruction_index
        )

    def search(self, pattern, disallowed_registers=None, desired_jump_register=None):
        """Searches for and, if found, returns a portion of this InstructionSequence that matches criteria

        Criteria: matches pattern,
                  none of registers in disallowed_registers changed after matching instruction,
                  instruction destination register not changed after instruction,
                  jump instruction must jump to desired_jump_register (if specified)

        pattern -- string in the 'search pattern' format or search criteria tuple
                   (see: InstructionSequence.extract_search_criteria())

        disallowed_registers -- optional list of registers that must not be changed in instructions after a match
        desired_jump_register -- optional string name of the register the jump instruction must jump to
        """
        (
            desired_operator,
            desired_first_operand_registers,
            desired_operands
        ) = InstructionSequence.get_search_criteria(pattern)

        matching_subsequence = None

        if disallowed_registers is None:
            disallowed_registers = []

        # if jump_register is specified, make sure self jumps to that register.
        # if it doesn't, return None
        if desired_jump_register and self.jump_register != desired_jump_register:
            return None

        # iterate over the instructions in order and return the first one that matches the criteria
        for index in xrange(len(self)):
            if self.instruction_matches(index, desired_operator, desired_first_operand_registers, desired_operands):
                match = self._include_copy_to_jump_register(self[index:], disallowed_registers)
                if match:
                    matching_subsequence = match
                    # since instructions were processed in order,
                    # the first matching subsequence contains all subsequences, so we're done
                    break

        if matching_subsequence and len(matching_subsequence) == 1:
            # the matching instruction was the branch delay slot, so include the jump as well
            matching_subsequence = self[-2:]
        return matching_subsequence