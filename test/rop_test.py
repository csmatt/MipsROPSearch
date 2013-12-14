import unittest
from src import rop, gadget_types, objdump_handler
import utils


class BuilderTests(unittest.TestCase):

    def test_empty_pipe_raises_exception(self):
        class FakeGadgetType(rop.GadgetType):
            def search(self):
                self.rop_gadgets = []
        
        builder = rop.Builder([FakeGadgetType()])
        self.assertRaises(Exception, builder.run)