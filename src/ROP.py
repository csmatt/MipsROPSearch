from InstructionSequence import InstructionSequence
import ObjdumpHandler


class Builder:

    def __init__(self, pipeline):
        """
        pipeline -- list of GadgetType objects in the same order as the desire rop sequence
        """
        self.pipeline = pipeline

    def run(self):
        """
        Processes the pipeline and returns a valid rop sequence or None if not possible

        :raises Exception: if no gadgets are found for one of the gadget types in self.pipeline
        """
        for pipe in self.pipeline:
            if not pipe.rop_gadgets:
                # there's no sense attempting to build if we don't have all the materials
                # usefully notifies of a failure early (and the cause) especially since, if the last pipe is empty,
                # recursive calls to Builder.build will iterate over every gadget of every pipe only to return None
                raise Exception("No gadgets found for type: %s. Canceling build." % pipe.__class__.__name__)

        return Builder.build(self.pipeline, set(), [])

    @staticmethod
    def build(pipeline, fresh_registers, rop_sequence):
        """
        Returns the first valid sequence of gadgets encountered by recursively calling itself, advancing through the
        pipeline as gadgets are found that are valid for in the context of rop_sequence.
        If a gadget fitting into the sequence cannot be found, the method returns and picks up where it left off for the
        previous gadget type in the pipeline.
        """
        crnt_gadget_type = pipeline[0]
        for gadget in crnt_gadget_type.rop_gadgets:
            if len(rop_sequence) == 0 or crnt_gadget_type.is_compatible(gadget, rop_sequence[-1], fresh_registers):
                new_sequence = rop_sequence + [gadget]
                if len(pipeline) > 1:
                    next_fresh_registers = fresh_registers.copy()
                    next_fresh_registers.difference_update(gadget.dependent_registers)
                    next_fresh_registers.update(gadget.fresh_registers)
                    result = Builder.build(pipeline[1:], next_fresh_registers, new_sequence)
                    if result is not None:
                        return result
                else:
                    return new_sequence
        return None

    @staticmethod
    def intersect(a, b):
        """Returns the list of gadgets with common offsets for their last instructions

        The function works by iterating over a and b individually
        to make maps of each InstructionSequence's last Instruction's offset to the InstructionSequence
        and sets of those offsets. The sets are then intersected and the offsets are used to look up
        the InstructionSequences. The larger of the two InstructionSequences will contain the smaller one,
        so it is added to the list of common gadgets that will be returned.

        a -- list of InstructionSequence objects
        b -- list of InstructionSequence objects
        """
        a_map_last_offset_to_gadget = {}
        a_offset_set = set()
        for gadget in a.rop_gadgets:
            offset = gadget[-1].offset
            a_map_last_offset_to_gadget[offset] = gadget
            a_offset_set.add(offset)

        b_map_last_offset_to_gadget = {}
        b_offset_set = set()
        for gadget in b.rop_gadgets:
            offset = gadget[-1].offset
            b_map_last_offset_to_gadget[offset] = gadget
            b_offset_set.add(offset)

        common = a_offset_set.intersection(b_offset_set)

        common_gadgets = []
        for offset in common:
            a_gadget = a_map_last_offset_to_gadget[offset]
            b_gadget = b_map_last_offset_to_gadget[offset]
            common_gadgets.append(a_gadget if len(a_gadget) > len(b_gadget) else b_gadget)

        return common_gadgets


class Gadget(InstructionSequence):

    def __init__(self, gadget, gadget_type):
        """
        gadget -- InstructionSequence object to initialize with
        gadget_type -- the subclass of GadgetType that describes this gadget
        """
        InstructionSequence.__init__(self, gadget)
        self.type = gadget_type
        self.fresh_registers = set()
        self.dependent_registers = set()

        # use self._get_last_change_to_jump_register giving it len(self) as the default index
        # to return if no controllable jump is found (so that it being returned means no controllable jump was found)
        self.has_controllable_jump = self._get_last_change_to_jump_register(len(self)) != len(self)

        for instruction in self:
            if instruction.operator == 'lw':
                self.fresh_registers.add(instruction.operands[0])
            elif instruction.operator == 'move':
                # maintain fresh and dependent register sets for 'move' instructions
                # TODO: can't reliably use 'lw' until we start keeping track of changes to $sp
                if instruction.operands[1] in self.fresh_registers:
                    self.fresh_registers.remove(instruction.operands[1])
                else:
                    self.dependent_registers.add(instruction.operands[1])

    def find_matching_instruction(self, pattern=None):
        """
        Uses pattern to find the first matching instruction in this gadget.

        pattern -- None, search string, or search_criteria tuple.
                   If None, self.type.search_pattern will be used.
        """
        pattern = pattern if pattern is not None else self.type.search_pattern
        search_criteria = InstructionSequence.get_search_criteria(pattern)
        for i in xrange(len(self)):
            if self.instruction_matches(i, *search_criteria):
                return self[i]


class GadgetType:

    search_pattern = None  # must specify in subclass
    reverse_search_results = False

    def __init__(self, *args, **kwargs):
        self.rop_gadgets = []
        self.search()

    def search(self):
        """
        Finds all instruction sequences in ObjdumpHandler that match self.search_pattern and contain controllable jumps
        and stores them as Gadget objects in self.rop_gadgets in an order defined by self.prioritize()
        """
        results = ObjdumpHandler.search(self.search_pattern)
        for result in results:
            gadget = Gadget(result, self.__class__)
            if gadget.has_controllable_jump:
                self.rop_gadgets.append(gadget)

        self.rop_gadgets = sorted(self.rop_gadgets, key=self.prioritize, reverse=self.reverse_search_results)
        return self.rop_gadgets

    def is_compatible(self, gadget, previous_gadget, fresh_registers):
        """
        Returns True if gadget is compatible with previous_gadget and fresh_registers.
        For gadget to be compatible, its dependent_registers must all be contained in fresh_registers

        gadget -- the Gadget object being checked for compatibility
        previous_gadget -- the Gadget object coming prior to gadget
        fresh_registers -- list of register names that are available for use by gadget
        """
        return gadget.dependent_registers <= fresh_registers

    @classmethod
    def prioritize(cls, gadget):
        """
        By default, rop_gadgets is prioritized its length in descending order
        so that gadgets with the fewest side effects come first
        """
        return len(gadget)