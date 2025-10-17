from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QTextEdit,
    QInputDialog, QMessageBox, QDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QEvent, QPoint
from datetime import datetime
import sys

# ---------- Configurable keybind ----------
# Set the toggle key and modifiers here.
# Example for Ctrl + Tab:
TOGGLE_KEY = Qt.Key.Key_Tab
TOGGLE_MODIFIERS = (Qt.KeyboardModifier.ControlModifier,)

CREWMATE_COLORS = [
    "Red", "Blue", "Green", "Pink", "Orange", "Yellow",
    "Black", "White", "Purple", "Brown", "Cyan", "Lime",
    "Maroon", "Rose", "Banana", "Gray", "Tan", "Coral"
]

COLOR_HEX = {
    "Red": "#ff4d4d", "Blue": "#4d4dff", "Green": "#33cc33", "Pink": "#ff99cc",
    "Orange": "#ff9900", "Yellow": "#ffff66", "Black": "#333333", "White": "#e0e0e0",
    "Purple": "#9933cc", "Brown": "#996633", "Cyan": "#00cccc", "Lime": "#99ff33",
    "Maroon": "#800000", "Rose": "#ff66a3", "Banana": "#fff27f", "Gray": "#9e9e9e",
    "Tan": "#d2b48c", "Coral": "#ff7f50"
}

def text_contrast_for(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    luminance = (0.299*r + 0.587*g + 0.114*b) / 255
    return "#000000" if luminance > 0.6 else "#ffffff"

class MiniOverlay(QWidget):
    def __init__(self, parent_app):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.parent_app = parent_app
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowType.Tool)
        self.setStyleSheet("""
            QWidget { background-color: rgba(20,20,20,220); color: #fff; border-radius:8px; }
            QLabel { color: #fff; }
            QPushButton { padding:4px 8px; }
        """)
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.title = QLabel("AmogBook (mini)")
        self.title.setStyleSheet("font-weight:600;")
        self.vbox.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.info_victim = QLabel("Victim: None")
        self.info_location = QLabel("Location: -")
        self.info_suspects = QLabel("Suspects: -")
        self.info_time = QLabel("")
        self.vbox.addWidget(self.info_victim)
        self.vbox.addWidget(self.info_location)
        self.vbox.addWidget(self.info_suspects)
        self.vbox.addWidget(self.info_time)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open Full")
        open_btn.setFixedHeight(24)
        open_btn.clicked.connect(self.show_full)
        btn_row.addWidget(open_btn)
        self.vbox.addLayout(btn_row)
        self.adjustSize()
        self.move_to_corner()

    def move_to_corner(self):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.size().width(), self.size().height()
        margin = 12
        self.move(screen.right() - w - margin, screen.top() + margin)

    def show_full(self):
        self.parent_app.show_full_overlay()

    def refresh(self, case_id=None):
        if not case_id:
            self.info_victim.setText("Victim: None")
            self.info_location.setText("Location: -")
            self.info_suspects.setText("Suspects: -")
            self.info_time.setText("")
            return
        case = self.parent_app.cases.get(case_id)
        if not case:
            self.refresh(None)
            return
        self.info_victim.setText(f"Victim: {case['victim']}")
        self.info_location.setText(f"Location: {case['location']}")
        self.info_suspects.setText("Suspects: " + (", ".join(case["suspects"]) if case["suspects"] else "-"))
        self.info_time.setText(f"{case.get('timestamp','')}")
        self.adjustSize()
        self.move_to_corner()

class AmogBook(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AmogBook v1.2 — Overlay Edition")
        self.setGeometry(120, 120, 520, 680)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.cases = {}
        self.sus_levels = {}
        self.selected_case_id = None
        self.selected_victim = None
        self.selected_suspects = []

        self.tabs = QTabWidget()
        self.init_case_tab()
        self.init_sus_tab()
        self.init_log_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)

        version_label = QLabel("AmogBook v1.2 — Overlay Edition")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(version_label)

        self.setLayout(layout)

        # Mini overlay
        self.mini = MiniOverlay(self)
        self.mini.show()

        # Start hidden (full overlay hidden by default)
        self.hide()

        # Install event filter for global key handling
        QApplication.instance().installEventFilter(self)

    def _modifiers_match(self, required_mods):
        if not required_mods:
            return True
        current = QApplication.keyboardModifiers()
        for m in required_mods:
            if not (current & m):
                return False
        return True

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == TOGGLE_KEY and self._modifiers_match(TOGGLE_MODIFIERS):
                self.toggle_overlay()
                return True
        return super().eventFilter(obj, event)

    # ---------- Case Tab / UI ----------
    def init_case_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.victim_label = QLabel("Victim: None")
        layout.addWidget(self.victim_label)
        layout.addWidget(self.build_selector("Select Victim", self.set_victim))

        self.location_input = QLineEdit()
        layout.addWidget(QLabel("Location"))
        layout.addWidget(self.location_input)

        layout.addWidget(QLabel("Suspects"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.suspect_layout = QVBoxLayout()
        container.setLayout(self.suspect_layout)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.selected_suspects = []
        self.add_suspect_slot()

        layout.addWidget(self.build_selector("Select Suspect (assigns to next slot)", self.assign_to_last_slot))

        self.notes_input = QLineEdit()
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_input)

        self.case_list = QListWidget()
        self.case_list.itemClicked.connect(self.on_case_selected)
        self.case_list.itemDoubleClicked.connect(self.view_case)
        layout.addWidget(self.case_list)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Case")
        save_btn.clicked.connect(self.save_case)
        remove_btn = QPushButton("Remove Case")
        remove_btn.clicked.connect(self.remove_case)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(remove_btn)
        layout.addLayout(btn_row)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Case")

    def build_selector(self, label: str, callback):
        box = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label))

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        cols = 6

        for i, color in enumerate(CREWMATE_COLORS):
            hexc = COLOR_HEX.get(color, "#888888")
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setToolTip(color)
            btn.setStyleSheet(f"background-color: {hexc}; border-radius: 15px; border: 1px solid #222;")
            btn.clicked.connect(lambda _, c=color: callback(c))

            name_lbl = QLabel(color)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            name_lbl.setStyleSheet(f"font-size: 9px; color: {text_contrast_for(hexc)};")

            cell_layout = QVBoxLayout()
            cell_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            cell_layout.addWidget(name_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)
            cell_widget = QWidget()
            cell_widget.setLayout(cell_layout)

            row = i // cols
            col = i % cols
            grid.addWidget(cell_widget, row, col)

        layout.addLayout(grid)
        box.setLayout(layout)
        return box

    def set_victim(self, color: str):
        self.selected_victim = color
        self.victim_label.setText(f"Victim: {color}")

    # Dynamic suspect slots
    def add_suspect_slot(self):
        lbl = QLabel("Suspect: [Unassigned]")
        lbl.setStyleSheet("padding: 6px; border: 1px solid #666; border-radius: 6px;")
        lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lbl.customContextMenuRequested.connect(lambda _: self.confirm_remove_suspect(lbl))
        lbl.mousePressEvent = lambda e, l=lbl: self.assign_or_change_suspect(e, l)
        self.suspect_layout.addWidget(lbl)
        self.selected_suspects.append(None)

    def assign_to_last_slot(self, color: str):
        for i, suspect in enumerate(self.selected_suspects):
            if suspect is None:
                self.selected_suspects[i] = color
                lbl = self.suspect_layout.itemAt(i).widget()
                if lbl:
                    lbl.setText(f"Suspect: {color}")
                self.add_suspect_slot()
                return

    def assign_or_change_suspect(self, event, label):
        if event.button() == Qt.MouseButton.LeftButton:
            color, ok = QInputDialog.getItem(self, "Assign Suspect", "Crewmate color:", CREWMATE_COLORS, 0, False)
            if ok:
                idx = self.suspect_layout.indexOf(label)
                if idx < 0:
                    return
                self.selected_suspects[idx] = color
                label.setText(f"Suspect: {color}")
                if idx == len(self.selected_suspects) - 1:
                    self.add_suspect_slot()

    def confirm_remove_suspect(self, label):
        idx = self.suspect_layout.indexOf(label)
        if idx < 0:
            return
        reply = QMessageBox.question(self, "Remove Suspect", "Delete this suspect slot?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_suspect(label)

    def remove_suspect(self, label):
        idx = self.suspect_layout.indexOf(label)
        if idx < 0:
            return
        self.selected_suspects.pop(idx)
        w = self.suspect_layout.takeAt(idx).widget()
        if w:
            w.deleteLater()
        for i in range(self.suspect_layout.count()):
            lbl = self.suspect_layout.itemAt(i).widget()
            val = self.selected_suspects[i]
            lbl.setText(f"Suspect: {val}" if val else "Suspect: [Unassigned]")
        if len(self.selected_suspects) == 0:
            self.add_suspect_slot()

    # ---------- Sus tab ----------
    def init_sus_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.sus_list = QListWidget()
        self.sus_list.itemDoubleClicked.connect(self.edit_sus)
        layout.addWidget(self.sus_list)

        btn_row = QHBoxLayout()
        set_btn = QPushButton("Set Sus")
        set_btn.clicked.connect(self.set_sus)
        remove_btn = QPushButton("Remove Sus")
        remove_btn.clicked.connect(self.remove_sus)
        btn_row.addWidget(set_btn)
        btn_row.addWidget(remove_btn)
        layout.addLayout(btn_row)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Sus")

    def set_sus(self):
        color, ok = QInputDialog.getItem(self, "Set Sus", "Crewmate color:", CREWMATE_COLORS, 0, False)
        if not ok:
            return
        level, ok = QInputDialog.getDouble(self, "Sus Level", f"{color} sus %:", 50.0, 0.0, 100.0, 1)
        if ok:
            self.sus_levels[color] = level
            self.refresh_sus_list()

    def edit_sus(self, item):
        color = item.text().split(":")[0]
        current = self.sus_levels.get(color, 50.0)
        level, ok = QInputDialog.getDouble(self, "Edit Sus", f"{color} sus %:", current, 0.0, 100.0, 1)
        if ok:
            self.sus_levels[color] = level
            self.refresh_sus_list()

    def remove_sus(self):
        item = self.sus_list.currentItem()
        if not item:
            return
        color = item.text().split(":")[0]
        if color in self.sus_levels:
            del self.sus_levels[color]
        self.refresh_sus_list()

    def refresh_sus_list(self):
        self.sus_list.clear()
        for color, level in sorted(self.sus_levels.items(), key=lambda x: -x[1]):
            self.sus_list.addItem(f"{color}: {level:.1f}%")

    # ---------- Log tab ----------
    def init_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.log_area = QTextEdit()
        layout.addWidget(self.log_area)
        log_btn = QPushButton("Add Log Entry")
        log_btn.clicked.connect(self.add_log)
        layout.addWidget(log_btn)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Log")

    def add_log(self):
        entry, ok = QInputDialog.getText(self, "Log Entry", "Note:")
        if ok and entry:
            timestamp = datetime.now().isoformat(timespec='seconds')
            self.log_area.append(f"[{timestamp}] {entry}")

    # ---------- Case persistence / editor ----------
    def save_case(self):
        if not self.selected_victim or not self.location_input.text():
            QMessageBox.warning(self, "Missing Info", "Victim and location are required.")
            return
        suspects = [s for s in self.selected_suspects if s]
        case_id = f"{self.selected_victim} @ {self.location_input.text()} ({datetime.now().strftime('%H:%M:%S')})"
        if case_id in self.cases:
            suffix = 1
            while f"{case_id}#{suffix}" in self.cases:
                suffix += 1
            case_id = f"{case_id}#{suffix}"
        self.cases[case_id] = {
            "victim": self.selected_victim,
            "location": self.location_input.text(),
            "suspects": suspects,
            "notes": self.notes_input.text(),
            "timestamp": datetime.now().isoformat(timespec='seconds')
        }
        self.case_list.addItem(case_id)
        self.selected_case_id = case_id
        self.mini.refresh(case_id)
        # reset suspect slots
        self.selected_suspects.clear()
        while self.suspect_layout.count():
            w = self.suspect_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.add_suspect_slot()
        self.location_input.clear()
        self.notes_input.clear()

    def remove_case(self):
        item = self.case_list.currentItem()
        if not item:
            return
        cid = item.text()
        if cid in self.cases:
            del self.cases[cid]
        row = self.case_list.row(item)
        self.case_list.takeItem(row)
        if self.selected_case_id == cid:
            self.selected_case_id = None
            self.mini.refresh(None)

    def on_case_selected(self, item):
        cid = item.text()
        self.selected_case_id = cid
        self.mini.refresh(cid)

    def view_case(self, item):
        cid = item.text()
        case = self.cases.get(cid)
        if not case:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Case")
        dlg_layout = QVBoxLayout()
        dlg_layout.addWidget(QLabel(f"Victim: {case['victim']}"))
        dlg_layout.addWidget(QLabel("Location"))
        location = QLineEdit(case["location"])
        dlg_layout.addWidget(location)
        dlg_layout.addWidget(QLabel("Suspects"))
        editor_suspect_layout = QVBoxLayout()
        editor_labels = []
        def make_editor_label(color_text):
            lbl = QLabel(f"Suspect: {color_text}" if color_text else "Suspect: [Unassigned]")
            lbl.setStyleSheet("padding: 6px; border: 1px solid #666; border-radius: 6px;")
            lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lbl.customContextMenuRequested.connect(lambda _: remove_editor_label(lbl))
            lbl.mousePressEvent = lambda e, l=lbl: editor_assign_or_change(e, l)
            return lbl
        def remove_editor_label(lbl):
            idx = editor_suspect_layout.indexOf(lbl)
            if idx < 0:
                return
            w = editor_suspect_layout.takeAt(idx).widget()
            if w:
                w.deleteLater()
            editor_labels.pop(idx)
        def editor_assign_or_change(event, lbl):
            if event.button() == Qt.MouseButton.LeftButton:
                color, ok = QInputDialog.getItem(dialog, "Assign Suspect", "Crewmate color:", CREWMATE_COLORS, 0, False)
                if ok:
                    idx = editor_suspect_layout.indexOf(lbl)
                    if idx < 0:
                        return
                    lbl.setText(f"Suspect: {color}")
                    if idx == len(editor_labels) - 1:
                        new_lbl = make_editor_label(None)
                        editor_labels.append(new_lbl)
                        editor_suspect_layout.addWidget(new_lbl)
        for s in case["suspects"]:
            lbl = make_editor_label(s)
            editor_labels.append(lbl)
            editor_suspect_layout.addWidget(lbl)
        empty_lbl = make_editor_label(None)
        editor_labels.append(empty_lbl)
        editor_suspect_layout.addWidget(empty_lbl)
        dlg_layout.addLayout(editor_suspect_layout)
        dlg_layout.addWidget(QLabel("Notes"))
        notes = QLineEdit(case.get("notes", ""))
        dlg_layout.addWidget(notes)
        save_btn = QPushButton("Save")
        def on_save():
            new_loc = location.text()
            new_notes = notes.text()
            new_sus = []
            for lbl in editor_labels:
                txt = lbl.text()
                if ": " in txt:
                    val = txt.split(": ", 1)[1]
                    if val and val != "[Unassigned]":
                        new_sus.append(val)
            self.update_case(cid, new_loc, new_notes, new_sus, dialog)
        save_btn.clicked.connect(on_save)
        dlg_layout.addWidget(save_btn)
        dialog.setLayout(dlg_layout)
        dialog.exec()

    def update_case(self, cid, location, notes, suspects, dialog):
        if cid not in self.cases:
            return
        self.cases[cid]["location"] = location
        self.cases[cid]["notes"] = notes
        self.cases[cid]["suspects"] = suspects
        self.mini.refresh(cid)
        dialog.accept()

    # ---------- Overlay control ----------
    def toggle_overlay(self):
        if self.isVisible():
            self.hide()
            self.mini.show()
        else:
            self.show()
            self.mini.hide()
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(screen.center() - QPoint(self.width()//2, self.height()//2))

    def show_full_overlay(self):
        self.show()
        self.mini.hide()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center() - QPoint(self.width()//2, self.height()//2))

# ---------- main ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AmogBook()
    sys.exit(app.exec())
