import unittest
from src import objdump_handler


class ObjdumpFunctionTests(unittest.TestCase):

    def setUp(self):
        objdump_handler.ALL_JUMP_BLOCKS = []
    
    @staticmethod
    def create_function_from_string_list(string_list):
        offset = 0
        objdump_function = objdump_handler.Function("%04d <function_name>:" % offset)
        for inst_index in range(len(string_list)):
            offset = inst_index
            objdump_function.add_instruction("%04d: %08d %s" % (offset, 0, string_list[inst_index]))
        objdump_function.extract_jump_blocks()
        return objdump_function

    def test_branch_and_its_delay_slot_instructions_excluded_from_jump_blocks(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "beqz t9,16f08 <h_errno+0x16ed4>",
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        self.assertEqual(len(fxn.jump_blocks[0]), 2)
        self.assertEqual(fxn.jump_blocks[0][0].operator, "jalr")

    def test_multiple_jump_blocks_extracted(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "jalr t9",
                "move a0,s0",
                "jr t9",
                "addiu a1,s3,10396"
        ])
        self.assertEqual(len(fxn.jump_blocks), 2)

    def test_match_on_delay_slot_includes_jump(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        gadget = objdump_handler.search("addiu a1,s3,10396")
        self.assertEqual(gadget[0][0].operator, "jalr")

    def test_no_match_when_jump_register_does_not_match(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        gadget = objdump_handler.search("addiu a1,s3,10396", None, "t8")
        self.assertEqual(len(gadget), 0)

    def test_no_match_when_disallowed_register_changed_in_delay_slot(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        gadget = objdump_handler.search("addiu a1,s3,10396", ["a1"], "t8")
        self.assertEqual(len(gadget), 0)

    def test_disallowed_register_change_is_excluded(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        gadget = objdump_handler.search("addiu a1,s3,10396", ["a0"])
        self.assertTrue(gadget[0][0].operator.startswith("jalr"))

    def test_match_on_non_change_instruction(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "sw ra,28(sp)",
                "jalr t9",
                "addiu a1,s3,10396"

        ])
        gadget = objdump_handler.search("sw ra,sp")
        self.assertTrue(gadget[0][0].operator.startswith("sw"))

    def test_no_match_when_second_operand_not_matched(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "sw ra,28(sp)",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        gadget = objdump_handler.search("sw ra,24(sp)")
        self.assertEqual(len(gadget), 0)

    def test_match_on_wildcarded_first_operand(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
                "move a0,s0",
                "jalr t9",
                "addiu a1,s3,10396"
        ])
        gadget = objdump_handler.search("move a*,s0")
        self.assertEqual(gadget[0][0].operator, "move", "single wildcard failed.")
        gadget = objdump_handler.search("move **,s0")
        self.assertEqual(gadget[0][0].operator, "move", "double wildcard failed.")

    def test_move_to_jump_register_included(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
            "sw ra,28(sp)",
            "move t9,s0",
            "sw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        gadget = objdump_handler.search("sw s1", None, "t9")
        self.assertEqual(gadget[0][0].operator, "move")
        self.assertEqual(gadget[0][0].operands[0], "t9")

    def test_move_to_jump_register_included_when_search_for_reg_change(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
            "sw ra,28(sp)",
            "move t9,s0",
            "lw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        gadget = objdump_handler.search("lw s1", None, "t9")
        self.assertEqual(gadget[0][0].operator, "move")
        self.assertEqual(gadget[0][0].operands[0], "t9")

    def test_no_match_when_disallowed_register_changed_after_move_to_jump_register(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
            "sw ra,28(sp)",
            "move t9,s0",
            "lw s2,36(sp)",
            "lw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        gadget = objdump_handler.search("lw s1", ["s2"], "t9")
        self.assertEqual(gadget[0][0].operator, "lw")
        self.assertEqual(gadget[0][0].operands[0], "s1")

    def test_no_match_if_change_to_destination_register_after_matched_instruction(self):
        fxn = ObjdumpFunctionTests.create_function_from_string_list([
            "lw s2,36(sp)",
            "lw s2,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        gadget = objdump_handler.search("lw s2")
        self.assertEqual(gadget[0][0].operands[1], "32(sp)")