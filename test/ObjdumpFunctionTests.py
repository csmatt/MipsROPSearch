import unittest
from src.ObjdumpFunction import ObjdumpFunction


class ObjdumpFunctionTests(unittest.TestCase):

    def createObjdumpFunctionFromStringList(self, stringList):
        offset = 0
        objdumpFunction = ObjdumpFunction("%04d <function_name>:" % offset)
        for instIndex in range(len(stringList)):
            offset = instIndex
            objdumpFunction.addInstruction("%04d: %08d %s" % (offset, 0, stringList[instIndex]))
        return objdumpFunction

    def test_branch_and_its_delay_slot_instructions_excluded_from_jump_blocks(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "beqz t9,16f08 <h_errno+0x16ed4>",
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        fxn.extractJumpBlocks()
        self.assertEqual(len(fxn.jumpBlocks[0]), 2)
        self.assertEqual(fxn.jumpBlocks[0][0].operator, "jalr")

    def test_multiple_jump_blocks_extracted(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "jalr t9",
                "move a0,s0",
                "jr t9",
                "addiu a1,s3,10396"
        ])
        fxn.extractJumpBlocks()
        self.assertEqual(len(fxn.jumpBlocks), 2)

    def test_match_on_delay_slot_includes_jump(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("addiu a1,s3,10396")
        self.assertEqual(gadget[0][0].operator, "jalr")

    def test_no_match_when_jump_register_does_not_match(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("addiu a1,s3,10396", None, "t8")
        self.assertEqual(len(gadget), 0)

    def test_no_match_when_disallowed_register_changed_in_delay_slot(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("addiu a1,s3,10396", ["a1"], "t8")
        self.assertEqual(len(gadget), 0)

    def test_disallowed_register_change_is_excluded(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("addiu a1,s3,10396", ["a0"])
        self.assertTrue(gadget[0][0].operator.startswith("jalr"))

    def test_match_on_non_change_instruction(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "sw ra,28(sp)",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("sw ra,sp")
        self.assertTrue(gadget[0][0].operator.startswith("sw"))

    def test_no_match_when_second_operand_not_matched(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "sw ra,28(sp)",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("sw ra,24(sp)")
        self.assertEqual(len(gadget), 0)

    def test_match_on_wildcarded_first_operand(self):
        fxn = self.createObjdumpFunctionFromStringList([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("move a*,s0")
        self.assertEqual(gadget[0][0].operator, "move", "Single wildcard failed.")
        gadget = fxn.search("move **,s0")
        self.assertEqual(gadget[0][0].operator, "move", "Double wildcard failed.")

    def test_move_to_jump_register_included(self):
        fxn = self.createObjdumpFunctionFromStringList([
            "sw ra,28(sp)",
            "move t9,s0",
            "lw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("lw s1", None, "t9")
        self.assertEqual(gadget[0][0].operator, "move")
        self.assertEqual(gadget[0][0].operands[0], "t9")

    def test_no_match_when_disallowed_register_changed_after_move_to_jump_register(self):
        fxn = self.createObjdumpFunctionFromStringList([
            "sw ra,28(sp)",
            "move t9,s0",
            "lw s2,36(sp)",
            "lw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        fxn.extractJumpBlocks()
        gadget = fxn.search("lw s1", ["s2"], "t9")
        self.assertEqual(gadget[0][0].operator, "lw")
        self.assertEqual(gadget[0][0].operands[0], "s1")