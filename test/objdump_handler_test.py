import unittest
import utils
from src import objdump_handler


class FunctionTests(unittest.TestCase):

    def tearDown(self):
        objdump_handler.ALL_JUMP_BLOCKS = []

    def test_branch_and_its_delay_slot_instructions_excluded_from_jump_blocks(self):
        fxn = utils.create_function_from_string_list([
            "beqz t9,16f08 <h_errno+0x16ed4>",
            "move a0,s0",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        self.assertEqual(len(fxn.jump_blocks[0]), 2)
        self.assertEqual(fxn.jump_blocks[0][0].operator, "jalr")

    def test_multiple_jump_blocks_extracted(self):
        fxn = utils.create_function_from_string_list([
            "jalr t9",
            "move a0,s0",
            "jr t9",
            "addiu a1,s3,10396"
        ])
        self.assertEqual(len(fxn.jump_blocks), 2)


class InstructionSequenceSearchTests(unittest.TestCase):

    def test_match_on_delay_slot_includes_jump(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "move a0,s0",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        matching_subsequence = instruction_sequence.search("addiu a1,s3,10396")
        self.assertEqual(matching_subsequence[0].operator, "jalr")

    def test_no_match_when_jump_register_does_not_match(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "move a0,s0",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        matching_subsequence = instruction_sequence.search("addiu a1,s3,10396", None, "t8")
        self.assertIsNone(matching_subsequence)

    def test_no_match_when_disallowed_register_changed_in_delay_slot(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "move a0,s0",
            "jalr t9",
            "addiu a1,s3,10396"

        ])
        matching_subsequence = instruction_sequence.search("addiu a1,s3,10396", ["a1"], "t8")
        self.assertIsNone(matching_subsequence)

    def test_disallowed_register_change_is_excluded(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "move a0,s0",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        matching_subsequence = instruction_sequence.search("addiu a1,s3,10396", ["a0"])
        self.assertTrue(matching_subsequence[0].operator.startswith("jalr"))

    def test_match_on_non_change_instruction(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "sw ra,28(sp)",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        matching_subsequence = instruction_sequence.search("sw ra,sp")
        self.assertTrue(matching_subsequence[0].operator.startswith("sw"))

    def test_no_match_when_second_operand_not_matched(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "sw ra,28(sp)",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        matching_subsequence = instruction_sequence.search("sw ra,24(sp)")
        self.assertIsNone(matching_subsequence)

    def test_match_on_wildcarded_first_operand(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "move a0,s0",
            "jalr t9",
            "addiu a1,s3,10396"
        ])
        matching_subsequence = instruction_sequence.search("move a*,s0")
        self.assertEqual(matching_subsequence[0].operator, "move", "single wildcard failed.")
        matching_subsequence = instruction_sequence.search("move **,s0")
        self.assertEqual(matching_subsequence[0].operator, "move", "double wildcard failed.")

    def test_move_to_jump_register_included(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "sw ra,28(sp)",
            "move t9,s0",
            "sw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        matching_subsequence = instruction_sequence.search("sw s1", None, "t9")
        self.assertEqual(matching_subsequence[0].operator, "move")
        self.assertEqual(matching_subsequence[0].operands[0], "t9")

    def test_move_to_jump_register_included_when_search_for_reg_change(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "sw ra,28(sp)",
            "move t9,s0",
            "lw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        matching_subsequence = instruction_sequence.search("lw s1", None, "t9")
        self.assertEqual(matching_subsequence[0].operator, "move")
        self.assertEqual(matching_subsequence[0].operands[0], "t9")

    def test_no_match_when_disallowed_register_changed_after_move_to_jump_register(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "sw ra,28(sp)",
            "move t9,s0",
            "lw s2,36(sp)",
            "lw s1,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        matching_subsequence = instruction_sequence.search("lw s1", ["s2"], "t9")
        self.assertEqual(matching_subsequence[0].operator, "lw")
        self.assertEqual(matching_subsequence[0].operands[0], "s1")

    def test_no_match_if_change_to_destination_register_after_matched_instruction(self):
        instruction_sequence = utils.create_instruction_sequence_from_string_list([
            "lw s2,36(sp)",
            "lw s2,32(sp)",
            "jalr t9",
            "move at,at"
        ])
        matching_subsequence = instruction_sequence.search("lw s2")
        self.assertEqual(matching_subsequence[0].operands[1], "32(sp)")