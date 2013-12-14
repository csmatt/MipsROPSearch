#!/usr/bin/python

import sys
import objdump_handler
import utils


def print_help_message(additional_lines=None):
    print "\nUsage: MipsROPSearch.py FILE_PATH 'SEARCH_PATTERN' [JUMP_REGISTER] [DISALLOWED_REGISTERS]\n"
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

    jump_register = sys.argv[3] if len(sys.argv) > 3 else None

    disallowed_registers = utils.build_register_list_from_pattern(sys.argv[4]) if len(sys.argv) > 4 else []

    objdump_handler.extract_functions_from_objdump_lines(objdump_lines)
    rop_gadgets = objdump_handler.search(sys.argv[2], disallowed_registers, jump_register)
    utils.print_list(rop_gadgets)

if __name__ == '__main__':
    main()