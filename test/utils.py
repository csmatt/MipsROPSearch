from src import objdump_handler


def create_instruction_sequence_from_string_list(string_list):
    instruction_list = []
    for inst_index in range(len(string_list)):
        offset = inst_index
        instruction_list.append(objdump_handler.Instruction("%04d: %08d %s" % (offset, 0, string_list[inst_index])))
    return objdump_handler.InstructionSequence(instruction_list)


def create_function_from_string_list(string_list):
    offset = 0
    objdump_function = objdump_handler.Function("%04d <function_name>:" % offset)
    objdump_function.instructions = create_instruction_sequence_from_string_list(string_list)
    objdump_function.extract_jump_blocks()
    return objdump_function