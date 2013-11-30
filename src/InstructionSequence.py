from Instruction import Instruction
import Utils


class InstructionSequence(list):
    """
    Subclass of list specifically to store Instruction objects in order.
    """
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
        # go through the instructions in reverse order to find the last time a register is changed in self
        # put that register in self.register_changes and map it to the index of the instruction where it's last changed
        for inst_index in xrange(len(self)-1, -1, -1):
            if self[inst_index].operator_type in Instruction.CHANGE_OP_TYPES:
                if self[inst_index].operands[0] not in self.register_changes:
                    self.register_changes[self[inst_index].operands[0]] = inst_index

    @staticmethod
    def _makes_changes(instructions, reg_list):
        """Returns True if an instruction in instructions changes the value of any registers in reg_list

        instructions -- list of Instruction objects
        reg_list -- list of register name strings
        """
        for inst in instructions:
            if inst.operator_type in Instruction.CHANGE_OP_TYPES and inst.operands[0] in reg_list:
                return True
        return False

    @staticmethod
    def _is_copy_to_jump_register(instruction, jump_register):
        """Returns True if instruction is copying a value into jump_register in a way that allows for controlling jumps
           and False otherwise.

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

    def _include_copy_to_jump_register(self, potential_gadget, disallowed_registers):
        """Tries to include a instruction that controls where this sequence will jump to, if possible.

        If an instruction controlling the jump exists and including it along with the instructions between it and
        potential_gadget does not change any disallowed registers, that list of instructions is returned.
        Or, if none of the disallowed registers were changed, the original list of instructions is returned.
        If disallowed registers were changed, None is returned.

        potential_gadget -- list of Instructions
        disallowed_registers -- list of registers that must not be changed in the list of Instructions returned
        """
        start_index = len(self)-len(potential_gadget)
        new_start_index = self._include_copy_to_jump_register_helper(start_index)
        new_potential_gadget = self[new_start_index:]
        if (
            new_start_index != start_index and
            not InstructionSequence._makes_changes(new_potential_gadget, disallowed_registers)
        ):
            return new_potential_gadget
        # there were no qualifying moves into the jump register prior to the matching instruction
        # make sure the gadget starting with the matching instruction doesn't change disallowed registers
        elif not self._makes_changes(potential_gadget, disallowed_registers):
            # no disallowed registers changed values, add this gadget
            return potential_gadget

    def _include_copy_to_jump_register_helper(self, index):
        """Attempts to find and return the index of a controllable jump instruction

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

        Returns a tuple of:
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
            desired_first_operand_registers = Utils.build_register_list_from_pattern(pattern_argument)
        else:
            desired_first_operand_registers = [desired_operands[0]]

        return desired_operator, desired_first_operand_registers, desired_operands

    def search(self, pattern, disallowed_registers=None, desired_jump_register=None):
        """Searches for and returns portions of this InstructionSequence that match criteria

        Criteria: matches pattern,
                  none of registers in disallowed_registers changed after matching instruction,
                  instruction destination register not changed after instruction,
                  jump instruction must jump to desired_jump_register (if specified)

        pattern -- tuple containing the desired operator, a list of expanded first operands from the pattern, and a list of all operands
                   or a string to extract the tuple from

        disallowed_registers -- optional list of registers that must not be changed in instructions after a match
        desired_jump_register -- optional string name of the register the jump instruction must jump to
        """
        if type(pattern) == str:
            pattern = InstructionSequence.extract_search_criteria(pattern)
        desired_operator, desired_first_operand_registers, desired_operands = pattern

        rop_gadget = None

        if disallowed_registers is None:
            disallowed_registers = []

        # if jump_register is specified, make sure self jumps to that register.
        # if it doesn't, return None
        if desired_jump_register and self.jump_register != desired_jump_register:
            return None

        # iterate over the instructions in order and return the first one that matches the criteria
        for inst_index in xrange(len(self)):
            instruction = self[inst_index]
            if (
                instruction.operator == desired_operator and
                instruction.operands[0] in desired_first_operand_registers and
                instruction.check_other_operands_match(desired_operands) and
                self.register_changes.get(instruction.operands[0], -1) <= inst_index
            ):
                potential_gadget = self._include_copy_to_jump_register(self[inst_index:], disallowed_registers)
                if potential_gadget:
                    rop_gadget = potential_gadget
                    # since instructions were processed in order, the first matching gadget contains all sub gadgets,
                    # so we're done
                    break

        if rop_gadget and len(rop_gadget) == 1:
            # the matching instruction was the branch delay slot, so include the jump as well
            rop_gadget = self[-2:]
        return rop_gadget