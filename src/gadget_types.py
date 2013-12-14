from rop import GadgetType, Gadget
from objdump_handler import InstructionSequence


class SRegisterLoads(GadgetType):
    """
    Searches for gadgets with the greatest number of contiguous s-register load instructions
    and prioritizes those that have the fewest instructions not part of the contiguous s-register loading
    """
    search_pattern = "lw s*,sp"
    reverse_search_results = True

    @classmethod
    def prioritize(cls, gadget):
        """Prioritizes longer continuous sequence of loads into s-registers in a given gadget"""
        greatest_count = 0
        count = 0
        for inst in gadget:
            if inst.operator == 'lw' and inst.operands[0].startswith('s') and inst.operands[1].find('sp') != -1:
                count += 1
            else:
                if count > greatest_count:
                    greatest_count = count
                count = 0
        if count > greatest_count:
            greatest_count = count

        # negative of length to also prioritize the smallest/simplest gadgets that load many or all s-registers
        return greatest_count, -len(gadget)


class LoadArgForSleep(GadgetType):
    """
    Searches for gadgets that load an immediate value into a0
    and prioritizes ones that are small and have a low value source operand that is > 0
    """
    search_pattern = "li a0"

    @classmethod
    def prioritize(cls, gadget):
        """
        Prioritizes low number source operands so that sleep waits the least amount of time possible
        """
        search_criteria = InstructionSequence.get_search_criteria(cls.search_pattern)
        second_operand_str = gadget.find_matching_instruction(search_criteria).operands[1]
        second_operand = int(second_operand_str, 16 if 'x' in second_operand_str else 10)
        if second_operand < 0:
            second_operand = 100
        return second_operand, len(gadget)


class CallToSleep(GadgetType):
    """
    Searches for a gadget that contains 2 controllable jumps to different addresses
    The first will jump into sleep and the second will jump to the next gadget
    """

    def search(self):
        """
        This one is special since GadgetType.search searches each jump block individually and we need to find a gadget with two.
        This is accomplished by using the results from ControllableJump() and finding controllable jump gadgets whose
          last and first instructions' offsets are 4 bytes apart (meaning the second comes immediately after the first.)

        TODO: This isn't completely accurate since the second gadget could be from the next function
        """
        first_and_last_offsets = [(gadget[0].offset, gadget[-1].offset, gadget) for gadget in ControllableJump().rop_gadgets]
        for i in range(len(first_and_last_offsets)-1):
            crnt_first_offset, crnt_last_offset, crnt_gadget = first_and_last_offsets[i]
            next_first_offset, next_last_offset, next_gadget = first_and_last_offsets[i+1]
            if int(next_first_offset, 16) - int(crnt_last_offset, 16) == 4:
                # next_gadget starts immediately after crnt_gadget ends
                if crnt_gadget.find_matching_instruction("move t9").operands[1] != \
                        next_gadget.find_matching_instruction("move t9").operands[1]:
                    # the source operands were different (not useful since it will just jump into sleep twice)
                    # NOTE: this doesn't check for an instruction that changes t9 between the 2 jumps
                    #       (which would constitute a useful gadget)
                    combined_gadget = []
                    combined_gadget.extend(crnt_gadget)
                    combined_gadget.extend(next_gadget)
                    self.rop_gadgets.append(Gadget(combined_gadget, CallToSleep))

        self.rop_gadgets = sorted(self.rop_gadgets, key=self.prioritize, reverse=self.reverse_search_results)


class StackLocator(GadgetType):
    """Searches for gadgets that save a relative stack location to a register"""

    search_pattern = "addiu **,sp"


class ControllableJump(GadgetType):
    """Searches for controllable jump gadgets and prioritizes those with the fewest instructions"""

    search_pattern = "move **"
    reverse_search_results = True

    def __init__(self, custom_search_pattern=None, ensure_compatible=False):
        """
        Sets this instance's search_pattern to custom_search_pattern if provided and sets ensure_compatible

        custom_search_pattern -- optional pattern to use instead of ControllableJump.search_pattern for this instance
        ensure_compatible -- if True, requires the previous gadget's destination operand is the source operand in
                             the matching move instruction that controls the jump register
        """
        self.ensure_compatible = ensure_compatible
        if custom_search_pattern is not None:
            self.search_pattern = custom_search_pattern
        GadgetType.__init__(self)

    def is_compatible(self, gadget, previous_gadget, fresh_registers):
        """
        Returns True if this gadget is compatible with the previous gadget and current fresh_registers.

        First, the superclass version is run and, if that returns True and self.ensure_compatible is True, the logic
        mentioned in __init__'s docstring for ensure_compatible is tested
        """
        ret_val = GadgetType.is_compatible(self, gadget, previous_gadget, fresh_registers)
        if ret_val and self.ensure_compatible:
            previous_gadget_matching_instruction = previous_gadget.find_matching_instruction()
            required_pattern = "move %s,%s" % (gadget.jump_register, previous_gadget_matching_instruction.operands[0])
            ret_val = gadget.find_matching_instruction(required_pattern) is not None
        return ret_val
