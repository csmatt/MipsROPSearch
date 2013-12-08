MipsROPSearch
=============

Assists in finding ROP gadgets in output from objdump

MipsROPSearch.py FILE 'SEARCH_PATTERN' JUMP_REGISTER [DISALLOWED_REGISTERS]

#### FILE: 
- path to a file created by running *objdump -d* on a MIPS binary and outputting it to a file

#### SEARCH_PATTERN: must be surrounded with quotes
- should be of the form: "OPERATOR REGISTER[,OPERAND1,OPERAND2]"
- OPERATOR must be an operator that causes a change in REGISTER: example operators lw, addiu, move
- REGISTER is the destination register and can have wildcards: ** matches a-, s-, t-registers, and ra; _s*_ matches all s-registers
- OPERANDn is optional but provides finer grain search by matching only instructions that contain each OPERANDn string specified

#### JUMP_REGISTER
- the register the jump instruction should jump to. for example: *t9*

#### DISALLOWED_REGISTERS
- registers that ROP gadgets aren't allowed to change
- can be a single register or pattern or both separated by commas: ex: a0,s*,t4-t8

#### EXAMPLES
- MipsROPSearch.py libc.objdump "lw s*" t9 t2-t4 # finds gadgets that jump to $t9, don't change values of t2,t3,t4 and contain instructions loading a word into any s-register
- MipsROPSearch.py libc.objdump "sw s1,sp" # finds gadgets regardless of jump register that store the value in s1 to somewhere on the stack
