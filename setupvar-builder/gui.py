from typing import cast

from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, QRect, Qt,
                          pyqtSignal)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QHBoxLayout, QMainWindow, QMenuBar, QPushButton,
                             QSpinBox, QTableView, QVBoxLayout, QWidget)

from settings_types import CheckBoxDict, NumericDict, OneOfDict


class MyTableModel(QAbstractTableModel):
    def __init__(self, data: list[list[str]]):
        super().__init__()
        self.table_data: list[list[str]] = data
        self.headers: list[str] = ["Settings", "VarStore", "VarOffset", "Options"]
        self.options: dict[int, str | int] = (
            {}
        )  # dictionary to store options for each row

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.table_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.headers[section]
            return None

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | int | None:
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 3:  # fourth column for options
                return self.options.get(index.row(), "")  # return option for that row
            else:
                return self.dataValue(index)
        return None

    def setData(
        self,
        index: QModelIndex,
        value: str | int,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        if (
            role == Qt.ItemDataRole.EditRole and index.column() == 3
        ):  # check if editing the fourth column
            self.options[index.row()] = value  # update options for that row
            self.dataChanged.emit(index, index, [role])  # signal that data has changed
            return True
        return False

    def dataValue(self, index: QModelIndex) -> str | None:
        row = index.row()
        col = index.column()
        if 0 <= row < len(self.table_data) and 0 <= col < len(self.headers):
            return self.table_data[row][col]
        return None


class MainWindow(QMainWindow):
    new_file_selected = pyqtSignal(str)
    export: list[str] = []

    def __init__(self):
        super().__init__()

        # set window title
        self.setWindowTitle("setupvar-builder")

        # initialize primary screen geometry
        screen_geo = self.initialize_screen()

        # initialize table view and model
        self.initialize_table(screen_geo)

        # initialize menu bar
        self.initialize_menu_bar()

        # initialize central widget
        self.initialize_central_widget(screen_geo)

    def initialize_screen(self) -> QRect:
        # get the primary screen
        primary_screen = QApplication.primaryScreen()

        if primary_screen is not None:
            # get the screen geometry
            return primary_screen.geometry()
        else:
            # if no primary screen found, return default geometry
            return QRect(0, 0, 800, 600)

    def initialize_table(self, screen_geo: QRect):
        # initialize table data and settings dictionary
        self.table_data: list[list[str]] = []
        self.settings_dict = None

        # initialize table model and view
        self.table_model = MyTableModel(self.table_data)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)

        # adjust table view height
        table_height = screen_geo.height() - 135
        self.table_view.setFixedHeight(table_height)

        # set column widths
        self.set_column_widths(screen_geo)

    def set_column_widths(self, screen_geo: QRect):
        # calculate column width based on screen width and number of columns
        column_width = (screen_geo.width() - 45) // len(self.table_model.headers)

        # set width for each column
        for i in range(len(self.table_model.headers)):
            self.table_view.setColumnWidth(i, column_width)

    def initialize_menu_bar(self):
        # create menu bar
        menubar = QMenuBar()

        # create file menu and actions
        file_menu = menubar.addMenu("File")
        open_action = QAction("&Open", self)
        file_menu.addAction(open_action)  # type: ignore
        open_action.setShortcut(QKeySequence.StandardKey.Open)

        # connect file menu actions to slots
        open_action.triggered.connect(self.open_new_file)  # type: ignore

        # set menu bar
        self.setMenuBar(menubar)

    def initialize_central_widget(self, screen_geo: QRect):
        # create layout for central widget
        layout = QVBoxLayout()

        # add table view to layout
        layout.addWidget(self.table_view, alignment=Qt.AlignmentFlag.AlignTop)

        # add button to layout
        self.add_button_to_layout(layout)

        # create central widget and set layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # center the main window on the screen
        self.center_main_window(screen_geo)

    def add_button_to_layout(self, layout: QVBoxLayout):
        # create horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # create export button
        export_button = QPushButton("Export")
        export_button.setFixedSize(110, 25)
        export_button.clicked.connect(self.export_button)  # type: ignore

        # add button to horizontal layout
        button_layout.addWidget(export_button)

        # add horizontal layout to main layout
        layout.addLayout(button_layout)

    def center_main_window(self, screen_geo: QRect):
        # center the main window on the screen
        self.move(screen_geo.center() - self.rect().center())

    def open_new_file(self):
        file_path = self.open_file_dialog()
        if file_path:
            self.new_file_selected.emit(file_path)

    def open_file_dialog(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text Files (*.txt)"
        )
        return file_path

    def save_file_dialog(self) -> str:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "output.txt", "Text Files (*.txt)"
        )
        return file_path

    def clear_data(self):
        for row in range(self.table_model.rowCount()):
            index = self.table_model.index(row, 3)
            self.table_view.setIndexWidget(index, None)

        self.table_model.options = {}
        self.settings_dict = {}
        self.export.clear()
        self.table_data.clear()
        self.table_model.layoutChanged.emit()

    def get_dict(
        self, dict: dict[str, dict[str, OneOfDict | NumericDict | CheckBoxDict]]
    ):
        self.settings_dict = dict

    def add_one_of(self, name: str, varstore: str, varoffset: str):
        self.table_data.append([name, varstore, varoffset, ""])
        self.table_model.layoutChanged.emit()

    def add_one_of_option(self, oneofoption_name: str, oneofoption_default: str | None):
        row_position = len(self.table_data) - 1  # adjusting for 0-based indexing
        current_item = self.table_model.index(row_position, 3)

        if oneofoption_default:
            if not current_item.data():
                self.table_model.setData(
                    current_item, oneofoption_name, Qt.ItemDataRole.EditRole
                )  # set data in model
                combo = QComboBox()
                self.table_view.setIndexWidget(current_item, combo)

            else:
                combo = self.table_view.indexWidget(current_item)

            combo = cast(QComboBox, self.table_view.indexWidget(current_item))
            combo.addItem(oneofoption_name)
            combo.setCurrentText(oneofoption_default)

    def add_numeric(
        self,
        name: str,
        varstore: str,
        varoffset: str,
        min: int,
        max: int,
        default: int | None,
    ):
        self.table_data.append([name, varstore, varoffset, ""])
        self.table_model.layoutChanged.emit()

        row_position = len(self.table_data) - 1  # adjusting for 0-based indexing
        current_item = self.table_model.index(row_position, 3)

        if (
            -2147483648 < default < 2147483647 and default >= min
            if default is not None
            else default
        ):
            spinbox = QSpinBox(self)
            try:
                spinbox.setMinimum(min)
                spinbox.setMaximum(max)
                (
                    spinbox.setValue(default)
                    if default is not None
                    else spinbox.setValue(0)
                )
            except OverflowError:
                spinbox.setMinimum(-2147483648)
                spinbox.setMaximum(2147483647)
                (
                    spinbox.setValue(default)
                    if default is not None
                    else spinbox.setValue(0)
                )

            self.table_view.setIndexWidget(current_item, spinbox)

    def add_checkbox(
        self, name: str, varstore: str, varoffset: str, default: str | None
    ):
        self.table_data.append([name, varstore, varoffset, ""])
        self.table_model.layoutChanged.emit()

        row_position = len(self.table_data) - 1  # adjusting for 0-based indexing
        current_item = self.table_model.index(row_position, 3)
        checkbox = QCheckBox(self)
        if default == "Enabled":
            checkbox.setChecked(True)
        self.table_view.setIndexWidget(current_item, checkbox)

    def export_button(self):
        for row in range(len(self.table_data)):
            name_index = self.table_model.index(row, 0)
            varstore_index = self.table_model.index(row, 1)
            varoffset_index = self.table_model.index(row, 2)
            index = self.table_model.index(row, 3)

            name = str(self.table_model.data(name_index))
            varstore = str(self.table_model.data(varstore_index))
            varoffset = str(self.table_model.data(varoffset_index))

            widget = self.table_view.indexWidget(index)

            if isinstance(widget, QComboBox):
                self.export_oneof(name, varstore, varoffset, widget)

            elif isinstance(widget, QSpinBox):
                self.export_numeric(name, varstore, varoffset, widget)

            elif isinstance(widget, QCheckBox):
                self.export_checkbox(name, varstore, varoffset, widget)

        file_path = self.save_file_dialog()
        self.write_export(file_path)

    def export_oneof(self, name: str, varstore: str, varoffset: str, widget: QComboBox):
        text = widget.currentText()
        if self.settings_dict is not None:
            if (
                varstore in self.settings_dict
                and varoffset in self.settings_dict[varstore]
                and text != self.settings_dict[varstore][varoffset]["default"]
            ):
                one_of_dict = cast(OneOfDict, self.settings_dict[varstore][varoffset])
                option = one_of_dict["options"].get(text)
                size = one_of_dict["size"]
                self.export.append(
                    f"# {name}: {text}\nsetup_var.efi {varoffset} {option} -s {size} -n {varstore}\n\n"
                )

    def export_numeric(
        self, name: str, varstore: str, varoffset: str, widget: QSpinBox
    ):
        value = widget.value()
        if self.settings_dict is not None:
            numeric_dict = cast(NumericDict, self.settings_dict[varstore][varoffset])
            if (
                varstore in self.settings_dict
                and varoffset in self.settings_dict[varstore]
                and value != numeric_dict["default"]
            ):
                size = numeric_dict["size"]
                self.export.append(
                    f"# {name}: {value}\nsetup_var.efi {varoffset} 0x{hex(value)[2:].upper()} -s {size} -n {varstore}\n\n"
                )

    def export_checkbox(
        self, name: str, varstore: str, varoffset: str, widget: QCheckBox
    ):
        if self.settings_dict is not None:
            if (
                varstore in self.settings_dict
                and varoffset in self.settings_dict[varstore]
            ):
                checkbox_dict = cast(
                    CheckBoxDict, self.settings_dict[varstore][varoffset]
                )
                default_value = checkbox_dict["default"]
                if widget.isChecked():
                    if default_value == "Disabled":
                        self.export.append(
                            f"# {name}: Enabled\nsetup_var.efi {varoffset} 0x1 -s 0x1 -n {varstore}\n\n"
                        )
                else:
                    if default_value == "Enabled":
                        self.export.append(
                            f"# {name}: Disabled\nsetup_var.efi {varoffset} 0x0 -s 0x1 -n {varstore}\n\n"
                        )

    def write_export(self, file_path: str):
        if file_path:
            with open(file_path, "w", encoding="utf8") as output:
                output.writelines(self.export)
