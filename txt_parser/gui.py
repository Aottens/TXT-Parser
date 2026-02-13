from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .parser import ParseDiagnostics, build_diagnostics, decode_file, lookup_addresses, parse_num_blocks, rows_to_markdown

logger = logging.getLogger(__name__)


class NumParserWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NUM Block Parser")
        self.resize(1200, 800)

        self.file_path: str | None = None
        self.file_text = ""
        self.num_blocks = []
        self.lookup_rows = []

        root = QWidget()
        root_layout = QVBoxLayout(root)

        top_bar = QHBoxLayout()
        self.open_button = QPushButton("Open file")
        self.open_button.clicked.connect(self.open_file)
        self.file_label = QLabel("No file selected")
        self.parse_button = QPushButton("Parse")
        self.parse_button.clicked.connect(self.parse_file)
        top_bar.addWidget(self.open_button)
        top_bar.addWidget(self.file_label, stretch=1)
        top_bar.addWidget(self.parse_button)
        root_layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        self._build_num_blocks_tab()
        self._build_lookup_tab()
        self._build_diagnostics_tab()

        self.setCentralWidget(root)
        self._build_menu()

    def _build_menu(self) -> None:
        save_action = QAction("Save Markdown", self)
        save_action.triggered.connect(self.save_markdown)
        self.menuBar().addAction(save_action)

    def _build_num_blocks_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.filter_field = QLineEdit()
        self.filter_field.setPlaceholderText("Filter NUM blocks table")
        self.filter_field.textChanged.connect(self.refresh_num_blocks_table)
        self.num_table = QTableWidget(0, 8)
        self.num_table.setHorizontalHeaderLabels(
            [
                "Objectnummer",
                "Address",
                "UnitScale",
                "Storage Type",
                "Minimum Input Limit",
                "Maximum Input Limit",
                "Timing of max/min range check",
                "Raw block preview",
            ]
        )
        layout.addWidget(self.filter_field)
        layout.addWidget(self.num_table)
        self.tabs.addTab(tab, "NUM Blocks")

    def _build_lookup_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.address_input = QPlainTextEdit()
        self.address_input.setPlaceholderText("One address per line")
        run_button = QPushButton("Run lookup")
        run_button.clicked.connect(self.run_lookup)

        self.lookup_table = QTableWidget(0, 8)
        self.lookup_table.setHorizontalHeaderLabels(
            [
                "Gevraagd Address",
                "Objectnummer",
                "Address in file",
                "UnitScale",
                "Storage Type",
                "Minimum Input Limit",
                "Maximum Input Limit",
                "Timing of max/min range check",
            ]
        )

        actions = QHBoxLayout()
        copy_button = QPushButton("Copy Markdown")
        copy_button.clicked.connect(self.copy_markdown)
        save_button = QPushButton("Save .md")
        save_button.clicked.connect(self.save_markdown)
        actions.addWidget(copy_button)
        actions.addWidget(save_button)

        layout.addWidget(self.address_input)
        layout.addWidget(run_button)
        layout.addWidget(self.lookup_table)
        layout.addLayout(actions)
        self.tabs.addTab(tab, "Address Lookup")

    def _build_diagnostics_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.diagnostics_text = QPlainTextEdit()
        self.diagnostics_text.setReadOnly(True)
        layout.addWidget(self.diagnostics_text)
        self.tabs.addTab(tab, "Diagnostics")

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open TXT file", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        self.file_path = path
        self.file_label.setText(Path(path).name)
        self.file_text, encoding = decode_file(path)
        self.statusBar().showMessage(f"Loaded {Path(path).name} ({encoding})")

    def parse_file(self) -> None:
        if not self.file_text:
            QMessageBox.warning(self, "No file", "Open a file first.")
            return
        self.num_blocks = parse_num_blocks(self.file_text)
        self.refresh_num_blocks_table()
        diagnostics = build_diagnostics(self.num_blocks)
        self.render_diagnostics(diagnostics)
        self.statusBar().showMessage(f"Parsed {len(self.num_blocks)} blocks")

    def refresh_num_blocks_table(self) -> None:
        filter_text = self.filter_field.text()
        blocks = [
            b
            for b in self.num_blocks
            if not filter_text
            or filter_text in b.object_number
            or filter_text in b.address_line
            or filter_text in b.raw_block_text
        ]
        self.num_table.setRowCount(len(blocks))
        for row, block in enumerate(blocks):
            preview = block.raw_block_text[:150].replace("\n", " ")
            values = [
                block.object_number,
                block.address_line,
                block.unitscale_line,
                block.storage_type_line,
                block.min_input_limit_line,
                block.max_input_limit_line,
                block.timing_range_check_line,
                preview,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.num_table.setItem(row, col, item)

    def run_lookup(self) -> None:
        if not self.file_text:
            QMessageBox.warning(self, "No file", "Open and parse a file first.")
            return
        requested = [line.strip() for line in self.address_input.toPlainText().splitlines() if line.strip()]
        self.lookup_rows = lookup_addresses(self.num_blocks, self.file_text, requested)
        self.lookup_table.setRowCount(len(self.lookup_rows))
        for row, item in enumerate(self.lookup_rows):
            values = [
                item.requested_address,
                item.object_number,
                item.address_in_file,
                item.unitscale,
                item.storage_type,
                item.min_input_limit,
                item.max_input_limit,
                item.timing_range_check,
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setFlags(table_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.lookup_table.setItem(row, col, table_item)

    def copy_markdown(self) -> None:
        markdown = rows_to_markdown(self.lookup_rows)
        QApplication.clipboard().setText(markdown)
        self.statusBar().showMessage("Markdown copied to clipboard")

    def save_markdown(self) -> None:
        markdown = rows_to_markdown(self.lookup_rows)
        path, _ = QFileDialog.getSaveFileName(self, "Save Markdown", "lookup.md", "Markdown (*.md)")
        if not path:
            return
        Path(path).write_text(markdown, encoding="utf-8")
        self.statusBar().showMessage(f"Saved {Path(path).name}")

    def render_diagnostics(self, diagnostics: ParseDiagnostics) -> None:
        lines = [f"num_block_count: {diagnostics.num_block_count}"]
        lines.append("sorted_object_numbers: " + ", ".join(diagnostics.sorted_object_numbers))
        lines.append("missing_numbers: " + ", ".join(diagnostics.missing_numbers))
        if diagnostics.duplicate_addresses:
            lines.append("duplicate_addresses:")
            for address, objects in diagnostics.duplicate_addresses.items():
                lines.append(f"  - {address} -> {', '.join(objects)}")
        else:
            lines.append("duplicate_addresses: none")
        self.diagnostics_text.setPlainText("\n".join(lines))


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication([])
    window = NumParserWindow()
    window.show()
    app.exec()
