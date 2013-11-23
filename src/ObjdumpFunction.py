import re
import Utils
from Instruction import Instruction


class ObjdumpFunction:
    FIRST_LINE_PATTERN = re.compile(r'^([0-9a-f]+) <(.+)>:')
    # looks for operator and operands expression in string from command line arg
    INSTRUCTION_EXPRESSION_PATTERN = re.compile(r'(?P<operator>[a-z]+)\s(?P<operandExpression>[a-z0-9\*]{2}).*')

    def __init__(self, first_line):
        """Initializes a new ObjdumpFunction object

        first_line -- string from the first line of a function from objdump output that contains its name and start offset
        """
        self.start, self.name = ObjdumpFunction.FIRST_LINE_PATTERN.findall(first_line)[0]
        self.instructions = []
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

    def _check_changed(self, inst_list, reg_list):
        """Returns true if an instruction in inst_list changes the value of any registers in reg_list

        inst_list -- list of instruction objects
        reg_list -- list of register name strings
        """
        for inst in inst_list:
            if inst.operator_type in Instruction.CHANGE_OPS and inst.operands[0] in reg_list:
                return True
        return False

    def _check_other_operands_match(self, instruction_operands, desired_operands):
        """Returns true if instruction_operands[1:] match all operands specified in desired_operands[1:] in order

        For a match, strings in desired_operands do not have to match exactly, they only have to be a substring

        instruction_operands -- an instruction object's .operands
        desired_operands -- list of strings to match in order against instruction_operands
        """
        instruction_operands_length = len(instruction_operands)
        desired_operands_length = len(desired_operands)

        if desired_operands_length > instruction_operands_length:
            # there's no way there's a match if the instruction doesn't have enough operands, return False
            return False

        for operand_index in xrange(1, desired_operands_length):
            if not desired_operands[operand_index] in instruction_operands[operand_index]:
                return False
        return True

    def _search_for_register_change_in_jump_block(self, block, operator, desired_register, reg_last_change):
        """Adds jump block to rop_gadgets if criteria is met

        Criteria: operator and desired_register match an instruction,
                  no register in disallowed_registers has its value changed after matching instruction

        block -- jump block (list of instruction objects)
        operator -- string that a qualifying instruction's operator will match
        desired_register -- string that a qualifying instruction's destination register operand will match
        reg_last_change -- dict mapping register names to the index in block where that register's value was updated (closest to the jump)
        """
        # There's a chance that the last time our register is changed is the instruction after the jump.
        # If that's the case, we also need to include the jump in the rop_block,
        # so set start_from to the jump instruction, otherwise, start from where the register is last changed
        rop_gadget_start = len(block)-2 if reg_last_change[desired_register] == len(block)-1 else reg_last_change[desired_register]

        if block[reg_last_change[desired_register]].operator == operator:
            # cool, the register we wanted changed was changed and by the operator we wanted, return the block starting from there
            return block[rop_gadget_start:]

    def _include_move_to_jump_register(self, block, index, reg_last_change):
        """Looks prior to index in block for a move instruction copying a register's value into the jump_register

        If a move instruction exists prior to index and no disallowed_registers are changed after the move, the move
        instruction's index is returned. otherwise, index is returned.

        block -- a jump block
        index -- the index to return if a qualifying move instruction is not found
        reg_last_change -- a map of register names to the index in block closest to the jump at which they were changed
        """
        last_change_of_jump_register = reg_last_change.get(block[-2].operands[0])
        if (
            last_change_of_jump_register is not None and
            block[last_change_of_jump_register].operator == "move" and
            index > last_change_of_jump_register
        ):
            return last_change_of_jump_register
        return index

    def search(self, pattern_str, disallowed_registers=None, jump_register=None):
        """Searches for and returns portions of jump blocks that match criteria

        Criteria: match instruction pattern in pattern_str,
                  none of disallowed_registers changed after instruction,
                  jump instruction must jump to jump_register (if not none)

        pattern_str -- user input string containing the operator and an expression to match the first operand against
        disallowed_registers -- optional list of registers that must not be changed in instructions after a pattern_str match
        jump_register -- optional string name of the register the jump instruction must jump to
        """
        if not disallowed_registers: disallowed_registers = []

        desired_operator, desired_operands_str = pattern_str.split()
        desired_operands = desired_operands_str.split(',')
        desired_first_operand_expression = desired_operands[0]
        rop_gadgets = []

        if desired_first_operand_expression[1] == "*":
            # handle wildcard destination register
            # "**" for all a,s,and t registers or the register group and a "*"- ex: "s*"
            pattern_argument = "a*,s*,t*,ra" if desired_operands[0][0] == "*" else desired_operands[0]
            desired_first_operand_registers = Utils.build_register_list_from_pattern(pattern_argument)
        else:
            desired_first_operand_registers = [desired_operands[0]]

        for block in self.jump_blocks:
            # if jump_register is specified, make sure this block jumps to that register.
            # if it doesn't, move on to the next block
            if jump_register and block[-2].operands[0] != jump_register:
                continue

            reg_last_change = {}
            # go through the instructions in reverse order to find the last time a register is changed in a jump block
            # put that register in reg_last_change and map it to the index of the instruction where it's last changed
            for inst_index in xrange(len(block)-1, -1, -1):
                if block[inst_index].operator_type in Instruction.CHANGE_OPS:
                    if block[inst_index].operands[0] not in reg_last_change:
                        reg_last_change[block[inst_index].operands[0]] = inst_index

            for desired_register in desired_first_operand_registers:
                if Instruction.OPERATOR_TO_TYPE.get(desired_operator) in Instruction.CHANGE_OPS:
                    # if the destination register we're looking for isn't in this jump block, this block is useless, so continue

                    if desired_register in reg_last_change and block[reg_last_change[desired_register]].operator == desired_operator:
                        potential_rop_block = self._search_for_register_change_in_jump_block(block, desired_operator, desired_register, reg_last_change)
                        # if potential_rop_block starts with a jump instruction,
                        # the instruction we want to check for matching operands of is the one at index 1
                        desired_instruction_index = 1 if potential_rop_block[0].operator in Instruction.OP_TYPES["JUMP"] else 0
                        if self._check_other_operands_match(potential_rop_block[desired_instruction_index].operands, desired_operands):
                            # all operands match

                            # try to include moves into the jump register if possible
                            start_index = len(block)-len(potential_rop_block)
                            new_start_index = self._include_move_to_jump_register(block, start_index, reg_last_change)
                            new_potential_rop_block = block[new_start_index:]
                            if new_start_index != start_index and not self._check_changed(new_potential_rop_block, disallowed_registers):
                                rop_gadgets.append(new_potential_rop_block)
                            # there were no qualifying moves into the jump register prior to the matching instruction
                            # make sure the block starting with the matching instruction doesn't change disallowed registers
                            elif not self._check_changed(potential_rop_block, disallowed_registers):
                                # no disallowed registers changed values, add this gadget
                                rop_gadgets.append(potential_rop_block)
                else:
                    rop_gadget_start = 0
                    for reg in reg_last_change:
                        if reg in disallowed_registers:
                            if reg_last_change.get(reg) > rop_gadget_start:
                                rop_gadget_start = reg_last_change.get(reg)

                    if rop_gadget_start > 0:
                        # add 1 to start at the instruction after the disallowed register's value change occurred
                        rop_gadget_start += 1

                    # loop through the instructions and add instructions from block
                    # starting from an instruction containing a matching operator and operand
                    for inst_index in xrange(rop_gadget_start, len(block)):
                        if desired_operator == block[inst_index].operator and desired_register == block[inst_index].operands[0]:
                            if self._check_other_operands_match(block[inst_index].operands, desired_operands):
                                # if we're on the last instruction, we need to start the block from 1 prior to include the jump
                                block_start_index = inst_index - 1 if inst_index == len(block) - 1 else inst_index
                                rop_gadgets.append(block[block_start_index:])
                                break

        return rop_gadgets