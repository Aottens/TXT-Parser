from __future__ import annotations

from dataclasses import dataclass


NOT_FOUND_IN_BLOCK = "not found in block"
NOT_FOUND_IN_FILE = "niet gevonden in bestand"
FOUND_OUTSIDE_NUM_BLOCK = "gevonden buiten NUM-blok"


@dataclass(frozen=True)
class NumBlock:
    object_number: str
    raw_block_text: str
    address_line: str
    unitscale_line: str
    storage_type_line: str
    min_input_limit_line: str
    max_input_limit_line: str
    timing_range_check_line: str


@dataclass(frozen=True)
class LookupRow:
    requested_address: str
    object_number: str
    address_in_file: str
    unitscale: str
    storage_type: str
    min_input_limit: str
    max_input_limit: str
    timing_range_check: str
