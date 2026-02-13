from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import FOUND_OUTSIDE_NUM_BLOCK, LookupRow, NOT_FOUND_IN_BLOCK, NOT_FOUND_IN_FILE, NumBlock

logger = logging.getLogger(__name__)

DELIMITER = "Numeral Display & Input[NUM"
OBJECT_NUMBER_RE = re.compile(r"^(\d{4})")
FIELD_LABELS = {
    "Address": ("address_line", ("Address",)),
    "UnitScale": ("unitscale_line", ("UnitScale", "Set UnitScale")),
    "Storage Type": ("storage_type_line", ("Storage Type",)),
    "Minimum Input Limit": ("min_input_limit_line", ("Minimum Input Limit",)),
    "Maximum Input Limit": ("max_input_limit_line", ("Maximum Input Limit",)),
    "Timing of max/min range check": ("timing_range_check_line", ("Timing of max/min range check",)),
}


@dataclass(frozen=True)
class ParseDiagnostics:
    num_block_count: int
    sorted_object_numbers: list[str]
    missing_numbers: list[str]
    duplicate_addresses: dict[str, list[str]]


def decode_file(path: str | Path) -> tuple[str, str]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        encoding = "latin-1 (fallback)"
    logger.info("decoded %s with %s", path, encoding)
    return text, encoding


def _line_matches_label(line: str, label: str) -> bool:
    normalized_line = line.lstrip()
    if normalized_line == label:
        return True
    return normalized_line.startswith(f"{label} ") or normalized_line.startswith(f"{label}:")


def _extract_fields(block_text: str) -> dict[str, str]:
    values: dict[str, str] = {meta[0]: NOT_FOUND_IN_BLOCK for meta in FIELD_LABELS.values()}
    lines = [line.rstrip("\r") for line in block_text.split("\n")]

    for index, line in enumerate(lines):
        for _canonical_label, (attr_name, accepted_labels) in FIELD_LABELS.items():
            if values[attr_name] != NOT_FOUND_IN_BLOCK:
                continue

            matched_label = next((label for label in accepted_labels if _line_matches_label(line, label)), None)
            if matched_label is None:
                continue

            normalized_line = line.lstrip()
            # Preserve full original line where possible; support layout where value is on next line.
            if normalized_line == matched_label and index + 1 < len(lines) and lines[index + 1].strip():
                values[attr_name] = f"{matched_label} {lines[index + 1].strip()}"
            else:
                values[attr_name] = normalized_line

    return values


def parse_num_blocks(text: str) -> list[NumBlock]:
    parts = text.split(DELIMITER)
    blocks: list[NumBlock] = []
    for part in parts[1:]:
        object_match = OBJECT_NUMBER_RE.match(part)
        object_number = f"NUM{object_match.group(1)}" if object_match else NOT_FOUND_IN_BLOCK
        reconstructed_block = DELIMITER + part

        values = _extract_fields(reconstructed_block)

        blocks.append(
            NumBlock(
                object_number=object_number,
                raw_block_text=reconstructed_block,
                address_line=values["address_line"],
                unitscale_line=values["unitscale_line"],
                storage_type_line=values["storage_type_line"],
                min_input_limit_line=values["min_input_limit_line"],
                max_input_limit_line=values["max_input_limit_line"],
                timing_range_check_line=values["timing_range_check_line"],
            )
        )

    logger.info("parsed num blocks: %s", len(blocks))
    return blocks


def _object_int(object_number: str) -> int:
    return int(object_number[3:])


def build_diagnostics(num_blocks: list[NumBlock]) -> ParseDiagnostics:
    valid_numbers = sorted(
        [b.object_number for b in num_blocks if re.fullmatch(r"NUM\d{4}", b.object_number)],
        key=_object_int,
    )
    missing: list[str] = []
    if valid_numbers:
        number_values = [_object_int(number) for number in valid_numbers]
        present = set(number_values)
        for value in range(min(number_values), max(number_values) + 1):
            if value not in present:
                missing.append(f"NUM{value:04d}")

    duplicates: defaultdict[str, list[str]] = defaultdict(list)
    for block in num_blocks:
        if block.address_line != NOT_FOUND_IN_BLOCK:
            duplicates[block.address_line].append(block.object_number)

    duplicate_addresses = {
        address: object_numbers
        for address, object_numbers in duplicates.items()
        if len(object_numbers) > 1
    }

    return ParseDiagnostics(
        num_block_count=len(num_blocks),
        sorted_object_numbers=valid_numbers,
        missing_numbers=missing,
        duplicate_addresses=duplicate_addresses,
    )


def lookup_addresses(
    num_blocks: list[NumBlock],
    full_text: str,
    requested_addresses: Iterable[str],
) -> list[LookupRow]:
    rows: list[LookupRow] = []

    for requested in requested_addresses:
        search_variants = [f"Address ETHERNET:{requested}", f"Address {requested}"]
        match_in_block = next((block for block in num_blocks if block.address_line in search_variants), None)

        if match_in_block is not None:
            rows.append(
                LookupRow(
                    requested_address=requested,
                    object_number=match_in_block.object_number,
                    address_in_file=match_in_block.address_line,
                    unitscale=match_in_block.unitscale_line,
                    storage_type=match_in_block.storage_type_line,
                    min_input_limit=match_in_block.min_input_limit_line,
                    max_input_limit=match_in_block.max_input_limit_line,
                    timing_range_check=match_in_block.timing_range_check_line,
                )
            )
            continue

        outside_hit = next((variant for variant in search_variants if variant in full_text), None)
        if outside_hit is not None:
            rows.append(
                LookupRow(
                    requested_address=requested,
                    object_number=FOUND_OUTSIDE_NUM_BLOCK,
                    address_in_file=outside_hit,
                    unitscale=NOT_FOUND_IN_BLOCK,
                    storage_type=NOT_FOUND_IN_BLOCK,
                    min_input_limit=NOT_FOUND_IN_BLOCK,
                    max_input_limit=NOT_FOUND_IN_BLOCK,
                    timing_range_check=NOT_FOUND_IN_BLOCK,
                )
            )
        else:
            rows.append(
                LookupRow(
                    requested_address=requested,
                    object_number=NOT_FOUND_IN_FILE,
                    address_in_file=NOT_FOUND_IN_FILE,
                    unitscale=NOT_FOUND_IN_BLOCK,
                    storage_type=NOT_FOUND_IN_BLOCK,
                    min_input_limit=NOT_FOUND_IN_BLOCK,
                    max_input_limit=NOT_FOUND_IN_BLOCK,
                    timing_range_check=NOT_FOUND_IN_BLOCK,
                )
            )

    return rows



def num_blocks_debug_report(num_blocks: list[NumBlock]) -> str:
    lines: list[str] = []
    for index, block in enumerate(num_blocks, start=1):
        lines.append(f"### Block {index}: {block.object_number}")
        lines.append(f"Address: {block.address_line}")
        lines.append(f"UnitScale: {block.unitscale_line}")
        lines.append(f"Storage Type: {block.storage_type_line}")
        lines.append(f"Minimum Input Limit: {block.min_input_limit_line}")
        lines.append(f"Maximum Input Limit: {block.max_input_limit_line}")
        lines.append(f"Timing of max/min range check: {block.timing_range_check_line}")
        lines.append("Raw block:")
        lines.append(block.raw_block_text)
        lines.append("-" * 60)
    return "\n".join(lines)


def rows_to_markdown(rows: list[LookupRow]) -> str:
    headers = [
        "Gevraagd Address",
        "Objectnummer",
        "Address in file",
        "UnitScale",
        "Storage Type",
        "Minimum Input Limit",
        "Maximum Input Limit",
        "Timing of max/min range check",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.requested_address,
                    row.object_number,
                    row.address_in_file,
                    row.unitscale,
                    row.storage_type,
                    row.min_input_limit,
                    row.max_input_limit,
                    row.timing_range_check,
                ]
            )
            + " |"
        )
    return "\n".join(lines)
