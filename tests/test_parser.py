import unittest

from txt_parser.models import FOUND_OUTSIDE_NUM_BLOCK, NOT_FOUND_IN_BLOCK, NOT_FOUND_IN_FILE
from txt_parser.parser import build_diagnostics, lookup_addresses, parse_num_blocks, rows_to_markdown


SAMPLE_TEXT = """Header
Address 777
Numeral Display & Input[NUM0001
Address 100
UnitScale A
Storage Type B
Minimum Input Limit 1
Maximum Input Limit 9
Timing of max/min range check C
Numeral Display & Input[NUM0003
Address ETHERNET:200
UnitScale D
Storage Type E
Minimum Input Limit 2
Maximum Input Limit 8
Timing of max/min range check F
"""


class ParserTests(unittest.TestCase):
    def test_parse_num_blocks_and_exact_labels(self):
        blocks = parse_num_blocks(SAMPLE_TEXT)
        self.assertEqual(2, len(blocks))
        self.assertEqual("NUM0001", blocks[0].object_number)
        self.assertEqual("Address 100", blocks[0].address_line)
        self.assertEqual("UnitScale D", blocks[1].unitscale_line)

    def test_diagnostics(self):
        diagnostics = build_diagnostics(parse_num_blocks(SAMPLE_TEXT))
        self.assertEqual(2, diagnostics.num_block_count)
        self.assertEqual(["NUM0001", "NUM0003"], diagnostics.sorted_object_numbers)
        self.assertEqual(["NUM0002"], diagnostics.missing_numbers)

    def test_lookup_classification(self):
        blocks = parse_num_blocks(SAMPLE_TEXT)
        rows = lookup_addresses(blocks, SAMPLE_TEXT, ["100", "777", "404"])

        self.assertEqual("NUM0001", rows[0].object_number)
        self.assertEqual("Address 100", rows[0].address_in_file)

        self.assertEqual(FOUND_OUTSIDE_NUM_BLOCK, rows[1].object_number)
        self.assertEqual("Address 777", rows[1].address_in_file)
        self.assertEqual(NOT_FOUND_IN_BLOCK, rows[1].unitscale)

        self.assertEqual(NOT_FOUND_IN_FILE, rows[2].object_number)
        self.assertEqual(NOT_FOUND_IN_FILE, rows[2].address_in_file)

    def test_markdown_shape(self):
        blocks = parse_num_blocks(SAMPLE_TEXT)
        rows = lookup_addresses(blocks, SAMPLE_TEXT, ["100"])
        markdown = rows_to_markdown(rows)
        self.assertTrue(markdown.startswith("| Gevraagd Address | Objectnummer |"))
        self.assertIn("| 100 | NUM0001 | Address 100 |", markdown)


if __name__ == "__main__":
    unittest.main()
