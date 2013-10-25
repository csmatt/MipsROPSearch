MipsROPSearch
=============

Assists in finding ROP gadgets in output from objdump

MipsROPSearch.py LIBC_FILE INSTRUCTION JUMP_REGISTER [DISALLOWED_REGISTERS]

#### INSTRUCTION: must be surrounded with quotes
- should be of the form: "OPERATOR REGISTER"
- OPERATOR must be an operator that causes a change in REGISTER: example operators lw, addiu, move
- REGISTER is the destination register and can have wildcards: ** matches a-, s-, t-registers, and ra; _s*_ matches all s-registers

#### JUMP_REGISTER
- the register the jump instruction should jump to. for example: *t9*

#### DISALLOWED_REGISTERS
- registers that ROP gadgets aren't allowed to change
- can be a single register or pattern or both separated by commas: ex: a0,s*,t4-t8
