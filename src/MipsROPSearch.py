#!/usr/bin/python

import sys
from ObjdumpFunction import ObjdumpFunction
from Instruction import Instruction
import Utils


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
                functions.append(function)
                function = None
        elif line.startswith("Disassembly of section"):
            # we hit a section that isn't .text, we're done here
            break
    return functions


def print_help_message(additional_lines=None):
    print "\n_usage: MipsROPSearch FILE INSTRUCTION [JUMP_REGISTER] [DISALLOWED_REGISTERS]\n"
    if additional_lines:
        for line in additional_lines:
            print "\t%s" % line
        print ""


def main():
    if len(sys.argv) < 3 or (len(sys.argv) > 1 and sys.argv[1] == "--help"):
        print_help_message()
        exit()

    file_name = sys.argv[1]
    objdump_lines = []
    try:
        f = open(file_name, 'r')
        objdump_lines = f.readlines()
        f.close()
    except IOError as e:
        print_help_message([e])
        exit()

    functions = extract_functions_from_objdump_lines(objdump_lines)

    jump_register = sys.argv[3] if len(sys.argv) > 3 else None

    disallowed_registers = Utils.build_register_list_from_pattern(sys.argv[4]) if len(sys.argv) > 4 else []

    for function in functions:
        function.extract_jump_blocks()
        rop_gadgets = function.search(sys.argv[2], disallowed_registers, jump_register)
        Utils.print_list(rop_gadgets)

if __name__ == '__main__':
    main()