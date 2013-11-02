#!/usr/bin/python

import sys
from ObjdumpFunction import ObjdumpFunction
from Instruction import Instruction
import Utils


def extractFunctionsFromObjdumpLines(objdumpLines):
    """Returns a list of ObjdumpFunctions created by parsing lines from objump output's .text section"""
    # we only care about the .text section, so we'll find where it is so we know where to start from
    startOfTextSection = 0
    for i in xrange(len(objdumpLines)):
        if objdumpLines[i] == "Disassembly of section .text:\n":
            startOfTextSection = i+2
            break

    functions = []
    function = None
    for line in objdumpLines[startOfTextSection:]:
        if Instruction.FIRST_LINE_PATTERN.match(line):
            function = ObjdumpFunction(line)
        elif Instruction.INSTRUCTION_LINE_PATTERN.match(line):
            function.addInstruction(line)
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


def printHelpMessage(additionalLines=None):
    print "\nUsage: MipsROPSearch FILE INSTRUCTION [JUMP_REGISTER] [DISALLOWED_REGISTERS]\n"
    if additionalLines:
        for line in additionalLines:
            print "\t%s" % line
        print ""


def main():
    if len(sys.argv) < 3 or (len(sys.argv) > 1 and sys.argv[1] == "--help"):
        printHelpMessage()
        exit()

    fileName = sys.argv[1]
    objdumpLines = []
    try:
        f = open(fileName, 'r')
        objdumpLines = f.readlines()
        f.close()
    except IOError as e:
        printHelpMessage([e])
        exit()

    functions = extractFunctionsFromObjdumpLines(objdumpLines)

    jumpRegister = sys.argv[3] if len(sys.argv)>3 else None

    disallowedRegisters = Utils.buildRegisterListFromPattern(sys.argv[4]) if len(sys.argv) > 4 else []

    for function in functions:
        function.extractJumpBlocks()
        function.search(sys.argv[2], disallowedRegisters, jumpRegister)

if __name__ == '__main__':
    main()