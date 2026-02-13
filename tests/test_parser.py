import tempfile
import unittest
from pathlib import Path

from txt_parser.models import FOUND_OUTSIDE_NUM_BLOCK, NOT_FOUND_IN_BLOCK, NOT_FOUND_IN_FILE
from txt_parser.parser import build_diagnostics, decode_file, lookup_addresses, num_blocks_debug_report, parse_num_blocks, rows_to_markdown


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


    def test_extracts_next_line_value_layout(self):
        text = """Numeral Display & Input[NUM0007
Address
300
UnitScale
X
Storage Type
Y
Minimum Input Limit
0
Maximum Input Limit
9
Timing of max/min range check
Z
"""
        block = parse_num_blocks(text)[0]
        self.assertEqual("Address 300", block.address_line)
        self.assertEqual("UnitScale X", block.unitscale_line)
        self.assertEqual("Storage Type Y", block.storage_type_line)

    def test_extracts_realistic_num_block_layout(self):
        text = """Numeral Display & Input[NUM0010]
Storage Type
REAL(Real Number 2 words)
Set UnitScale
1000
Timing of max/min range check
Check Value after Scale Conversion
Address
ETHERNET:VUA.IJ.Buffer_afstand
Input Max/Min
Specify Maximum Input Limit
ON
   Maximum Input Limit
10
Specify Minimum Input Limit
ON
   Minimum Input Limit
0
"""
        block = parse_num_blocks(text)[0]
        self.assertEqual("NUM0010", block.object_number)
        self.assertEqual("Address ETHERNET:VUA.IJ.Buffer_afstand", block.address_line)
        self.assertEqual("Set UnitScale 1000", block.unitscale_line)
        self.assertEqual("Storage Type REAL(Real Number 2 words)", block.storage_type_line)
        self.assertEqual("Maximum Input Limit 10", block.max_input_limit_line)
        self.assertEqual("Minimum Input Limit 0", block.min_input_limit_line)


    def test_debug_report_contains_extracted_values(self):
        blocks = parse_num_blocks(SAMPLE_TEXT)
        report = num_blocks_debug_report(blocks)
        self.assertIn("### Block 1: NUM0001", report)
        self.assertIn("Address: Address 100", report)
        self.assertIn("UnitScale: UnitScale A", report)


    def test_decode_file_normalizes_escaped_newlines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("Numeral Display & Input[NUM0001\\nAddress\\n100", encoding="utf-8")
            text, source = decode_file(path)
            self.assertIn("escaped-newline-normalization", source)
            block = parse_num_blocks(text)[0]
            self.assertEqual("Address 100", block.address_line)

    def test_decode_file_rtf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.rtf"
            path.write_text(r"{\rtf1\ansi Numeral Display & Input[NUM0002\par Address\par ETHERNET:ABC}", encoding="utf-8")
            text, source = decode_file(path)
            self.assertTrue(source.startswith("rtf("))
            block = parse_num_blocks(text)[0]
            self.assertEqual("NUM0002", block.object_number)
            self.assertEqual("Address ETHERNET:ABC", block.address_line)


    def test_prefers_general_address_over_other_sections(self):
        text = """Numeral Display & Input[NUM0011]
General
Address
ETHERNET:MAIN.VALUE
Flicker
   Address

Input Max/Min
   Minimum Input Limit
1
   Maximum Input Limit
9
"""
        block = parse_num_blocks(text)[0]
        self.assertEqual("Address ETHERNET:MAIN.VALUE", block.address_line)



if __name__ == "__main__":
    unittest.main()
