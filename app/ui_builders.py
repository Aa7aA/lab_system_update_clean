from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QFormLayout,
    QPushButton,
)

# ----------------------------
# Internal helpers
# ----------------------------
def _make_flag_label() -> QLabel:
    lbl = QLabel("")
    lbl.setFixedWidth(22)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("font-weight: 900; font-size: 14px;")
    return lbl


def _make_range_label() -> QLabel:
    lbl = QLabel("")
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl.setStyleSheet("color: #555;")
    return lbl

def _make_test_name_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight: 800; font-size: 14px;")
    return lbl

def _add_combo_items(cb: QComboBox, options: list[str], ensure_empty: bool = True) -> None:
    # Normalize so empty choice appears once at the top
    opts = [o for o in (options or []) if o is not None]
    opts = [str(o) for o in opts]

    # remove empties then add one empty at top if requested
    cleaned = [o for o in opts if o.strip() != ""]
    if ensure_empty:
        cb.addItem("")
    for o in cleaned:
        cb.addItem(o)



class PositiveNegativeButtons(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._value = ""

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.btn_positive = QPushButton("Positive(+ve)")
        self.btn_negative = QPushButton("Negative(-ve)")
        self.btn_positive.setCheckable(True)
        self.btn_negative.setCheckable(True)


        self.btn_positive.setMinimumHeight(30)
        self.btn_negative.setMinimumHeight(30)

        self.btn_positive.setCursor(Qt.PointingHandCursor)
        self.btn_negative.setCursor(Qt.PointingHandCursor)

        self.btn_positive.clicked.connect(lambda: self.set_value("Positive(+ve)"))
        self.btn_negative.clicked.connect(lambda: self.set_value("Negative(-ve)"))

        row.addWidget(self.btn_positive)
        row.addWidget(self.btn_negative)

        self._refresh_style()

    def value(self) -> str:
        return self._value

    def set_value(self, value: str) -> None:
        value = (value or "").strip()

        if value in {"Positive", "Positive(+ve)", "Positive (+)", "+", "+ve"}:
            self._value = "Positive(+ve)"
        elif value in {"Negative", "Negative(-ve)", "Negative (-)", "-", "-ve"}:
            self._value = "Negative(-ve)"
        else:
            self._value = ""

        self.btn_positive.setChecked(self._value == "Positive(+ve)")
        self.btn_negative.setChecked(self._value == "Negative(-ve)")

        self._refresh_style()

    def _refresh_style(self) -> None:
        base = """
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #c6d3e1;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #f5f9ff;
                border: 1px solid #8fc7ff;
            }
        """

        positive_selected = """
            QPushButton {
                background-color: #ffd6df;
                color: #8a1f35;
                border: 2px solid #ff4d6d;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 900;
            }
        """

        negative_selected = """
            QPushButton {
                background-color: #dff5e7;
                color: #146c37;
                border: 2px solid #2fa866;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 900;
            }
        """

        self.btn_positive.setStyleSheet(
            positive_selected if self._value == "Positive(+ve)" else base
        )
        self.btn_negative.setStyleSheet(
            negative_selected if self._value == "Negative(-ve)" else base
        )


def make_positive_negative_buttons() -> PositiveNegativeButtons:
    return PositiveNegativeButtons()












def _build_flagged_rows_grid(
    grid: QGridLayout,
    test_names: list[str],
) -> tuple[dict[str, QLineEdit], dict[str, QLabel], dict[str, QLabel]]:
    """
    Build rows into an existing grid:
    label | input | flag
    Range labels are still created and returned for logic/printing,
    but they are hidden and not added to the visible UI.
    Returns maps: inputs, flags, ranges
    """
    inputs: dict[str, QLineEdit] = {}
    flags: dict[str, QLabel] = {}
    ranges: dict[str, QLabel] = {}

    for r, test_name in enumerate(test_names):
        lbl = _make_test_name_label(f"{test_name} :")
        lbl.setMinimumWidth(78)

        edit = QLineEdit()
        edit.setPlaceholderText("Result")
        edit.setMinimumHeight(26)
        edit.setMinimumWidth(96)

        flag_lbl = _make_flag_label()
        range_lbl = _make_range_label()
        range_lbl.hide()  # keep for logic, but do not show in UI

        grid.addWidget(lbl, r, 0)
        grid.addWidget(edit, r, 1)
        grid.addWidget(flag_lbl, r, 2)
         

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 0)




        inputs[test_name] = edit
        flags[test_name] = flag_lbl
        ranges[test_name] = range_lbl

    grid.setRowStretch(len(test_names), 1)
    return inputs, flags, ranges





def _build_mixed_rows_grid(
    grid: QGridLayout,
    test_defs: list[tuple[str, str, list[str]]],
) -> tuple[dict[str, QWidget], dict[str, QLabel], dict[str, QLabel]]:
    """
    Build rows into an existing grid using input_type per test.

    test_defs format:
        [(test_name, input_type, options), ...]

    Returns:
        inputs, flags, ranges
    """
    inputs: dict[str, QWidget] = {}
    flags: dict[str, QLabel] = {}
    ranges: dict[str, QLabel] = {}

    for r, (test_name, input_type, options) in enumerate(test_defs):
        lbl = _make_test_name_label(f"{test_name} :")
        lbl.setMinimumWidth(78)

        itype = (input_type or "").strip().lower()

        if itype == "dropdown":
            w = QComboBox()
            w.setEditable(True)
            w.setInsertPolicy(QComboBox.NoInsert)
            _add_combo_items(w, options or [], ensure_empty=True)
            w.setMinimumHeight(26)
            w.setMinimumWidth(96)
        elif itype == "titer":
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            cb = QComboBox()
            cb.setEditable(True)
            _add_combo_items(cb, options or [], ensure_empty=True)
            cb.setMinimumHeight(26)

            titer_edit = QLineEdit()
            titer_edit.setPlaceholderText("Titer")
            titer_edit.setFixedWidth(80)

            row_layout.addWidget(cb, 1)
            row_layout.addWidget(titer_edit, 0)

            # store as combined widget
            w = row_widget

            # VERY IMPORTANT: attach children for later access
            w._result_cb = cb
            w._titer_edit = titer_edit




        elif itype == "buttons":
            w = make_positive_negative_buttons()
            w.setMinimumHeight(30)
            w.setMinimumWidth(160)

        else:
            w = QLineEdit()
            w.setPlaceholderText("Result")
            w.setMinimumHeight(26)
            w.setMinimumWidth(96)

        flag_lbl = _make_flag_label()
        range_lbl = _make_range_label()
        range_lbl.hide()

        grid.addWidget(lbl, r, 0)
        grid.addWidget(w, r, 1)
        grid.addWidget(flag_lbl, r, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 0)

        inputs[test_name] = w
        flags[test_name] = flag_lbl
        ranges[test_name] = range_lbl

    grid.setRowStretch(len(test_defs), 1)
    return inputs, flags, ranges


def build_three_panel_mixed_form_with_flags(
    col1: list[tuple[str, str, list[str]]],
    col2: list[tuple[str, str, list[str]]],
    col3: list[tuple[str, str, list[str]]],
    col1_title: str = "",
    col2_title: str = "",
    col3_title: str = "",
) -> tuple[QWidget, dict[str, QWidget], dict[str, QLabel], dict[str, QLabel]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    def make_column(test_defs: list[tuple[str, str, list[str]]], title: str):
        box = QGroupBox(title)
        box.setObjectName("TestColumnCard")

        grid = QGridLayout(box)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        inputs, flags, ranges = _build_mixed_rows_grid(grid, test_defs)
        return box, inputs, flags, ranges

    b1, i1, f1, r1 = make_column(col1, col1_title)
    b2, i2, f2, r2 = make_column(col2, col2_title)
    b3, i3, f3, r3 = make_column(col3, col3_title)

    outer.addWidget(b1, 1)
    outer.addWidget(b2, 1)
    outer.addWidget(b3, 1)

    inputs = {**i1, **i2, **i3}
    flags = {**f1, **f2, **f3}
    ranges = {**r1, **r2, **r3}
    return tab, inputs, flags, ranges


def build_two_column_mixed_form_with_flags(
    col1: list[tuple[str, str, list[str]]],
    col2: list[tuple[str, str, list[str]]],
    title: str = "",
) -> tuple[QWidget, dict[str, QWidget], dict[str, QLabel], dict[str, QLabel]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    def make_column(test_defs: list[tuple[str, str, list[str]]]):
        box = QGroupBox(title)
        box.setObjectName("TestColumnCard")

        grid = QGridLayout(box)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        inputs, flags, ranges = _build_mixed_rows_grid(grid, test_defs)
        return box, inputs, flags, ranges

    b1, i1, f1, r1 = make_column(col1)
    b2, i2, f2, r2 = make_column(col2)

    outer.addWidget(b1, 1)
    outer.addWidget(b2, 1)

    inputs = {**i1, **i2}
    flags = {**f1, **f2}
    ranges = {**r1, **r2}
    return tab, inputs, flags, ranges


def build_single_column_mixed_form_with_flags(
    test_defs: list[tuple[str, str, list[str]]],
    title: str = "",
) -> tuple[QWidget, dict[str, QWidget], dict[str, QLabel], dict[str, QLabel]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QVBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)

    box = QGroupBox(title)
    box.setObjectName("TestColumnCard")

    grid = QGridLayout(box)
    grid.setContentsMargins(8, 6, 8, 6)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(4)

    inputs, flags, ranges = _build_mixed_rows_grid(grid, test_defs)

    outer.addWidget(box)
    return tab, inputs, flags, ranges









# ------------------------------------------------------------
# 3 COLUMNS: label | input | flag | range
# ------------------------------------------------------------
def build_three_panel_form_with_flags(
    col1: list[str],
    col2: list[str],
    col3: list[str],
    col1_title: str = "",
    col2_title: str = "",
    col3_title: str = "",
) -> tuple[QWidget, dict[str, QLineEdit], dict[str, QLabel], dict[str, QLabel]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    def make_column(test_names: list[str], title: str):
        box = QGroupBox(title)
        box.setObjectName("TestColumnCard")

        grid = QGridLayout(box)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        inputs, flags, ranges = _build_flagged_rows_grid(grid, test_names)
        return box, inputs, flags, ranges

    b1, i1, f1, r1 = make_column(col1, col1_title)
    b2, i2, f2, r2 = make_column(col2, col2_title)
    b3, i3, f3, r3 = make_column(col3, col3_title)

    outer.addWidget(b1, 1)
    outer.addWidget(b2, 1)
    outer.addWidget(b3, 1)

    inputs = {**i1, **i2, **i3}
    flags = {**f1, **f2, **f3}
    ranges = {**r1, **r2, **r3}

    return tab, inputs, flags, ranges


# ------------------------------------------------------------
# 1 COLUMN: label | input | flag | range
# ------------------------------------------------------------
def build_single_column_form_with_flags(
    test_names: list[str],
    title: str = "",
) -> tuple[QWidget, dict[str, QLineEdit], dict[str, QLabel], dict[str, QLabel]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QVBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)

    box = QGroupBox(title)
    box.setObjectName("TestColumnCard")

    grid = QGridLayout(box)
    grid.setContentsMargins(8, 6, 8, 6)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(4)

    inputs, flags, ranges = _build_flagged_rows_grid(grid, test_names)

    outer.addWidget(box)
    return tab, inputs, flags, ranges


# ------------------------------------------------------------
# 2 COLUMNS: label | input | flag | range
# ------------------------------------------------------------
def build_two_column_form_with_flags(
    col1: list[str],
    col2: list[str],
    title: str = "",
) -> tuple[QWidget, dict[str, QLineEdit], dict[str, QLabel], dict[str, QLabel]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    def make_column(test_names: list[str]):
        box = QGroupBox(title)
        box.setObjectName("TestColumnCard")


        grid = QGridLayout(box)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        inputs, flags, ranges = _build_flagged_rows_grid(grid, test_names)
        return box, inputs, flags, ranges

    b1, i1, f1, r1 = make_column(col1)
    b2, i2, f2, r2 = make_column(col2)

    outer.addWidget(b1, 1)
    outer.addWidget(b2, 1)

    inputs = {**i1, **i2}
    flags = {**f1, **f2}
    ranges = {**r1, **r2}

    return tab, inputs, flags, ranges


# ------------------------------------------------------------
# DROPDOWNS
# ------------------------------------------------------------
def build_dropdown_pairs(
    pairs: list[tuple[str, list[str]]],
    title: str = "",
    editable: bool = True,
) -> tuple[QWidget, dict[str, QComboBox]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QVBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)

    box = QGroupBox(title)
    form = QFormLayout(box)
    form.setLabelAlignment(Qt.AlignLeft)
    form.setFormAlignment(Qt.AlignTop)

    inputs: dict[str, QComboBox] = {}

    for name, options in pairs:
        cb = QComboBox()
        cb.setEditable(editable)
        _add_combo_items(cb, options, ensure_empty=True)
        inputs[name] = cb
        form.addRow(_make_test_name_label(name), cb)

    outer.addWidget(box)
    return tab, inputs


def build_two_panel_dropdowns(
    pairs: list[tuple[str, list[str]]],
    left_title: str = "",
    right_title: str = "",
    editable: bool = True,
) -> tuple[QWidget, dict[str, QComboBox]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    mid = (len(pairs) + 1) // 2
    left_pairs = pairs[:mid]
    right_pairs = pairs[mid:]

    def make_panel(items, title):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        inputs: dict[str, QComboBox] = {}
        for name, options in items:
            cb = QComboBox()
            cb.setEditable(editable)
            _add_combo_items(cb, options, ensure_empty=True)
            inputs[name] = cb
            form.addRow(_make_test_name_label(name), cb)
        return box, inputs

    b1, i1 = make_panel(left_pairs, left_title)
    b2, i2 = make_panel(right_pairs, right_title)

    outer.addWidget(b1, 1)
    outer.addWidget(b2, 1)

    inputs = {**i1, **i2}
    return tab, inputs


def build_two_panel_dropdowns_with_titer(
    left_items: list[tuple[str, list[str]]],
    right_items: list[tuple[str, list[str]]],
    left_title: str = "",
    right_title: str = "",
    editable: bool = True,
) -> tuple[QWidget, dict[str, QComboBox], dict[str, QLineEdit]]:
    """
    Two-panel layout like build_two_panel_dropdowns, but each row has:
      - Result dropdown (Positive/Negative/etc.)
      - Titer number input (small QLineEdit)

    Returns:
      tab, result_widgets_by_test, titer_widgets_by_test
    """
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    def make_panel(items, title):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        results: dict[str, QComboBox] = {}
        titers: dict[str, QLineEdit] = {}

        for test_name, options in items:
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(10)

            cb = QComboBox()
            cb.setEditable(editable)
            _add_combo_items(cb, options, ensure_empty=True)

            t = QLineEdit()
            t.setPlaceholderText("Titer")
            t.setFixedWidth(90)

            row_lay.addWidget(cb, 1)
            row_lay.addWidget(t, 0)

            form.addRow(_make_test_name_label(test_name), row)

            results[test_name] = cb
            titers[test_name] = t

        return box, results, titers

    left_box, left_results, left_titers = make_panel(left_items, left_title)
    right_box, right_results, right_titers = make_panel(right_items, right_title)

    outer.addWidget(left_box, 1)
    outer.addWidget(right_box, 1)

    # merge dicts
    all_results = {**left_results, **right_results}
    all_titers = {**left_titers, **right_titers}

    return tab, all_results, all_titers






def build_notes_tab(title: str = "Notes") -> tuple[QWidget, QTextEdit]:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(10, 10, 10, 10)

    box = QGroupBox(title)
    box_layout = QVBoxLayout(box)

    notes = QTextEdit()
    notes.setPlaceholderText("Notes / comment")

    box_layout.addWidget(notes)
    layout.addWidget(box)

    return tab, notes




def build_widal_test_table(
    rows: list[str],
    options: list[str],
    title: str = "Widal Test",
) -> tuple[QWidget, dict[str, QComboBox]]:
    """
    Neat Widal table (top-left), no stretching gaps.
    Keys: 'Sal.Typhi__O', 'Sal.Typhi__H', ...
    """
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QVBoxLayout(tab)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(8)

    # Keep the table on the left like the original UI
    row_wrap = QHBoxLayout()
    row_wrap.setContentsMargins(0, 0, 0, 0)
    row_wrap.setSpacing(0)
    outer.addLayout(row_wrap)

    box = QGroupBox(title)
    row_wrap.addWidget(box, 0)

    # Add stretch so the group stays left and doesn't expand across the whole tab
    row_wrap.addStretch(1)

    grid = QGridLayout(box)
    grid.setContentsMargins(14, 14, 14, 14)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(12)

    # Make columns behave nicely
    grid.setColumnStretch(0, 2)  # test name column
    grid.setColumnStretch(1, 1)  # O
    grid.setColumnStretch(2, 1)  # H

    # Headers (row 0)
    hdr_o = QLabel("O")
    hdr_h = QLabel("H")
    hdr_o.setAlignment(Qt.AlignCenter)
    hdr_h.setAlignment(Qt.AlignCenter)

    grid.addWidget(QLabel(""), 0, 0)
    grid.addWidget(hdr_o, 0, 1)
    grid.addWidget(hdr_h, 0, 2)

    widgets: dict[str, QComboBox] = {}

    def make_combo() -> QComboBox:
        cb = QComboBox()
        cb.setEditable(False)
        cb.setMinimumWidth(140)
        for opt in options:
            cb.addItem(opt)
        return cb

    # Data rows start from row=1
    for r, name in enumerate(rows, start=1):
        lab = _make_test_name_label(name)
        lab.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        cb_o = make_combo()
        cb_h = make_combo()

        grid.addWidget(lab, r, 0)
        grid.addWidget(cb_o, r, 1)
        grid.addWidget(cb_h, r, 2)

        widgets[f"{name}__O"] = cb_o
        widgets[f"{name}__H"] = cb_h

    # IMPORTANT: prevent vertical stretching pushing everything to bottom
    grid.setRowStretch(len(rows) + 1, 1)

    # Keep any extra space below, not above
    outer.addStretch(1)

    return tab, widgets



# ------------------------------------------------------------
# TWO PANEL key/label DROPDOWNS (GUE style)
# ------------------------------------------------------------
def build_two_panel_keylabel_dropdowns(
    left_items: list[tuple[str, str, list[str]]],
    right_items: list[tuple[str, str, list[str]]],
    left_title: str = "",
    right_title: str = "",
    editable: bool = True,
) -> tuple[QWidget, dict[str, QComboBox]]:
    w = QWidget()
    w.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(w)
    outer.setContentsMargins(10, 10, 10, 10)
    outer.setSpacing(18)

    def make_panel(items, title):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        inputs: dict[str, QComboBox] = {}
        for key, label, options in items:
            cb = QComboBox()
            cb.setEditable(editable)
            _add_combo_items(cb, options, ensure_empty=True)
            inputs[key] = cb
            form.addRow(_make_test_name_label(label), cb)
        return box, inputs

    b1, i1 = make_panel(left_items, left_title)
    b2, i2 = make_panel(right_items, right_title)

    outer.addWidget(b1, 1)
    outer.addWidget(b2, 1)

    inputs = {**i1, **i2}
    return w, inputs


# ------------------------------------------------------------
# ANTIBIOTICS TABLE
# ------------------------------------------------------------
def build_antibiotics_table(antibiotics: list[str]) -> tuple[QWidget, dict[str, QComboBox]]:
    w = QWidget()
    w.setLayoutDirection(Qt.LeftToRight)

    grid = QGridLayout(w)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(8)

    header1 = QLabel("Antibiotic")
    header2 = QLabel("Sensitivity")
    header1.setStyleSheet("font-weight: 800;")
    header2.setStyleSheet("font-weight: 800;")
    grid.addWidget(header1, 0, 0)
    grid.addWidget(header2, 0, 1)

    inputs: dict[str, QComboBox] = {}
    opts = ["", "S", "I", "R"]

    for i, ab in enumerate(antibiotics, start=1):
        lbl = _make_test_name_label(ab)
        combo = QComboBox()
        combo.addItems(opts)
        combo.setMinimumWidth(120)
        grid.addWidget(lbl, i, 0)
        grid.addWidget(combo, i, 1)
        inputs[ab] = combo

    grid.setRowStretch(len(antibiotics) + 1, 1)
    return w, inputs


def build_antibiotics_table_from_db(
    pairs: list[tuple[str, list[str]]],
    editable: bool = True,
) -> tuple[QWidget, dict[str, QComboBox]]:
    w = QWidget()
    w.setLayoutDirection(Qt.LeftToRight)

    grid = QGridLayout(w)
    grid.setHorizontalSpacing(10)
    grid.setVerticalSpacing(8)

    inputs: dict[str, QComboBox] = {}

    grid.addWidget(QLabel("Antibiotic"), 0, 0)
    grid.addWidget(QLabel("S / I / R"), 0, 1)

    for r, (name, opts) in enumerate(pairs, start=1):
        lab = _make_test_name_label(name)
        lab.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        combo = QComboBox()
        combo.setEditable(editable)
        _add_combo_items(combo, opts, ensure_empty=True)

        inputs[name] = combo
        grid.addWidget(lab, r, 0)
        grid.addWidget(combo, r, 1)

    grid.setRowStretch(len(pairs) + 1, 1)
    return w, inputs



def build_antibiotics_table_three_columns(
    antibiotics: list[str],
    options: list[str] | None = None,
    splits: tuple[int, int] = (10, 20),
) -> tuple[QWidget, dict[str, QComboBox]]:
    """
    Culture antibiotics table in 3 columns like the original UI.
    Returns:
      widget, inputs_dict[antibiotic] = QComboBox
    """
    if options is None:
        options = ["", "S", "I", "R"]

    # Split list into 3 columns: [0:s1], [s1:s2], [s2:]
    s1, s2 = splits
    col1 = antibiotics[:s1]
    col2 = antibiotics[s1:s2]
    col3 = antibiotics[s2:]

    host = QWidget()
    host.setLayoutDirection(Qt.LeftToRight)

    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(30)

    inputs: dict[str, QComboBox] = {}

    def make_block(items: list[str]) -> QWidget:
        w = QWidget()
        w.setLayoutDirection(Qt.LeftToRight)
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        h1 = QLabel("Antibiotic")
        h2 = QLabel("Result")
        h1.setStyleSheet("font-weight: 800; text-decoration: underline;")
        h2.setStyleSheet("font-weight: 800; text-decoration: underline;")
        grid.addWidget(h1, 0, 0)
        grid.addWidget(h2, 0, 1)

        for r, name in enumerate(items, start=1):
            lab = _make_test_name_label(name)
            cb = QComboBox()
            cb.setEditable(False)
            cb.addItems(options)
            cb.setMinimumWidth(140)

            grid.addWidget(lab, r, 0)
            grid.addWidget(cb, r, 1)
            inputs[name] = cb

        grid.setRowStretch(len(items) + 1, 1)
        return w

    row.addWidget(make_block(col1), 1)
    row.addWidget(make_block(col2), 1)
    row.addWidget(make_block(col3), 1)

    return host, inputs



def build_torch_two_panel_dropdowns(
    left_tests: list[str],
    right_tests: list[str],
    options: list[str],
    left_title: str = "",
    right_title: str = "",
) -> tuple[QWidget, dict[str, QComboBox], dict[str, QLineEdit]]:
    tab = QWidget()
    tab.setLayoutDirection(Qt.LeftToRight)

    outer = QHBoxLayout(tab)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(28)

    result_widgets: dict[str, QComboBox] = {}
    titer_widgets: dict[str, QLineEdit] = {}

    def make_panel(items: list[str], title: str) -> QGroupBox:
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        h_param = QLabel("Parameter")
        h_res = QLabel("Result")
        h_titer = QLabel("")

        h_param.setStyleSheet("font-weight: 800; text-decoration: underline;")
        h_res.setStyleSheet("font-weight: 800; text-decoration: underline;")

        grid.addWidget(h_param, 0, 0)
        grid.addWidget(h_res, 0, 1)
        grid.addWidget(h_titer, 0, 2)

        row = 1
        for name in items:
            if name.strip() == ".":
                grid.addWidget(QLabel(""), row, 0)
                grid.addWidget(QLabel(""), row, 1)
                grid.addWidget(QLabel(""), row, 2)
                row += 1
                continue

            lab = _make_test_name_label(name)

            cb = QComboBox()
            cb.setEditable(True)
            cb.setInsertPolicy(QComboBox.NoInsert)
            cb.addItems(options)
            cb.setMinimumWidth(170)

            titer = QLineEdit()
            titer.setPlaceholderText("Titer")
            titer.setFixedWidth(90)

            grid.addWidget(lab, row, 0)
            grid.addWidget(cb, row, 1)
            grid.addWidget(titer, row, 2)

            result_widgets[name] = cb
            titer_widgets[name] = titer
            row += 1

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setRowStretch(row + 1, 1)
        return box

    left_box = make_panel(left_tests, left_title)
    right_box = make_panel(right_tests, right_title)

    outer.addWidget(left_box, 1)
    outer.addWidget(right_box, 1)

    return tab, result_widgets, titer_widgets




