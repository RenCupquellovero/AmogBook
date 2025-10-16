from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QListWidget,
    QTextEdit, QInputDialog, QMessageBox, QDialog, QFormLayout
)
from PyQt6.QtCore import Qt
from datetime import datetime
import sys

CREWMATE_COLORS = [
    "Red", "Blue", "Green", "Pink", "Orange", "Yellow",
    "Black", "White", "Purple", "Brown", "Cyan", "Lime"
]

class DetectiveNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Detective Notebook v1.0")
        self.setGeometry(100, 100, 500, 600)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.cases = {}  # case_id: {victim, location, suspects, notes}
        self.sus_levels = {}

        self.tabs = QTabWidget()
        self.init_case_tab()
        self.init_sus_tab()
        self.init_log_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)

        version_label = QLabel("Version 1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(version_label)

        self.setLayout(layout)

    def init_case_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.victim_box = QComboBox()
        self.victim_box.addItems(CREWMATE_COLORS)
        layout.addWidget(QLabel("Victim"))
        layout.addWidget(self.victim_box)

        self.location_input = QLineEdit()
        layout.addWidget(QLabel("Location"))
        layout.addWidget(self.location_input)

        self.suspect_boxes = []
        for i in range(4):
            box = QComboBox()
            box.addItems([""] + CREWMATE_COLORS)
            layout.addWidget(QLabel(f"Suspect {i+1}"))
            layout.addWidget(box)
            self.suspect_boxes.append(box)

        self.notes_input = QLineEdit()
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_input)

        self.case_list = QListWidget()
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

    def save_case(self):
        victim = self.victim_box.currentText()
        location = self.location_input.text()
        suspects = [box.currentText() for box in self.suspect_boxes if box.currentText()]
        notes = self.notes_input.text()
        if not location:
            QMessageBox.warning(self, "Missing Info", "Location is required.")
            return
        case_id = f"{victim} @ {location} ({datetime.now().strftime('%H:%M:%S')})"
        self.cases[case_id] = {
            "victim": victim,
            "location": location,
            "suspects": suspects,
            "notes": notes
        }
        self.case_list.addItem(case_id)

    def remove_case(self):
        selected = self.case_list.currentItem()
        if selected:
            cid = selected.text()
            del self.cases[cid]
            self.case_list.takeItem(self.case_list.row(selected))

    def view_case(self, item):
        cid = item.text()
        case = self.cases[cid]

        dialog = QDialog(self)
        dialog.setWindowTitle("View/Edit Case")
        layout = QFormLayout()

        victim = QComboBox()
        victim.addItems(CREWMATE_COLORS)
        victim.setCurrentText(case["victim"])
        layout.addRow("Victim", victim)

        location = QLineEdit(case["location"])
        layout.addRow("Location", location)

        suspects = []
        for i in range(4):
            box = QComboBox()
            box.addItems([""] + CREWMATE_COLORS)
            if i < len(case["suspects"]):
                box.setCurrentText(case["suspects"][i])
            layout.addRow(f"Suspect {i+1}", box)
            suspects.append(box)

        notes = QLineEdit(case.get("notes", ""))
        layout.addRow("Notes", notes)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.update_case(cid, victim, location, suspects, notes, dialog))
        layout.addRow(save_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def update_case(self, cid, victim, location, suspects, notes, dialog):
        self.cases[cid] = {
            "victim": victim.currentText(),
            "location": location.text(),
            "suspects": [s.currentText() for s in suspects if s.currentText()],
            "notes": notes.text()
        }
        dialog.accept()

    def set_sus(self):
        color, ok = QInputDialog.getItem(self, "Set Sus", "Crewmate color:", CREWMATE_COLORS, 0, False)
        if not ok:
            return
        level, ok = QInputDialog.getDouble(self, "Sus Level", f"{color} sus %:", 50, 0, 100, 1)
        if ok:
            self.sus_levels[color] = level
            self.refresh_sus_list()

    def edit_sus(self, item):
        color = item.text().split(":")[0]
        level, ok = QInputDialog.getDouble(self, "Edit Sus", f"{color} sus %:", self.sus_levels[color], 0, 100, 1)
        if ok:
            self.sus_levels[color] = level
            self.refresh_sus_list()

    def remove_sus(self):
        selected = self.sus_list.currentItem()
        if selected:
            color = selected.text().split(":")[0]
            del self.sus_levels[color]
            self.refresh_sus_list()

    def refresh_sus_list(self):
        self.sus_list.clear()
        for color, level in sorted(self.sus_levels.items(), key=lambda x: -x[1]):
            self.sus_list.addItem(f"{color}: {level:.1f}%")

    def add_log(self):
        entry, ok = QInputDialog.getText(self, "Log Entry", "Note:")
        if ok and entry:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_area.append(f"[{timestamp}] {entry}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DetectiveNotebook()
    window.show()
    sys.exit(app.exec())
