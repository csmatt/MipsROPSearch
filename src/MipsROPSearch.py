#!/usr/bin/python

import sys
import ObjdumpHandler
import Utils


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

    functions = ObjdumpHandler.extract_functions_from_objdump_lines(objdump_lines)

    jump_register = sys.argv[3] if len(sys.argv) > 3 else None

    disallowed_registers = Utils.build_register_list_from_pattern(sys.argv[4]) if len(sys.argv) > 4 else []

    for function in functions:
        rop_gadgets = function.search(sys.argv[2], disallowed_registers, jump_register)
        Utils.print_list(rop_gadgets)

if __name__ == '__main__':
    main()