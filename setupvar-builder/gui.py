import re
from typing import cast

from dict_types import CheckBoxDict, NumericDict, OneOfDict
from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, QRect, Qt,
                          pyqtSignal)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMainWindow, QMenuBar, QMessageBox, QPushButton,
                             QSizePolicy, QSpacerItem, QSpinBox, QTableView,
                             QVBoxLayout, QWidget)


class MyTableModel(QAbstractTableModel):
    def __init__(self, data: list[list[str]]):
        super().__init__()
        self.table_data: list[list[str]] = data
        self.filtered_data: list[list[str]] = self.table_data.copy()
        self.headers: list[str] = ["Settings", "VarStore", "VarOffset", "Options"]
        self.options: dict[int, str] = {}  # dictionary to store options for each row

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
        value: str,
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

    def setFilter(
        self,
        query: str,
        match_case: bool,
        match_whole_word: bool,
        exact_match: bool,
        regex_search: bool,
    ):
        """Filter rows based on a query in column 1"""

        # build the regex pattern based on the options
        flags = 0 if match_case else re.IGNORECASE
        word_boundary = r"\b" if match_whole_word else ""
        search_string = query if regex_search else re.escape(query)
        pattern = rf"{word_boundary}{search_string}{word_boundary}"
        search_type = re.fullmatch if exact_match else re.search

        try:
            # filter rows
            self.filtered_data = [
                row for row in self.table_data if search_type(pattern, row[0], flags)
            ]
        except re.error:
            self.filtered_data = []

        self.layoutChanged.emit()


class MainWindow(QMainWindow):
    open_file = pyqtSignal(str)

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

        # initialize export list
        self.export: list[str] = []

        # initialize filtered rows set
        self.filtered_rows: set[int] = set()

        # initialize dynamic widget
        self.dynamic_widget = None

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

        # set the table view's size policy to expanding
        self.table_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # set column widths
        self.set_column_widths()

    def set_column_widths(self):
        # get the header for the table view
        header = self.table_view.horizontalHeader()

        # set the section resize mode for all columns to `Stretch``
        if header:
            for col in range(self.table_model.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

    def initialize_menu_bar(self):
        # create menu bar
        menubar = QMenuBar()

        # create file menu and actions
        file_menu = menubar.addMenu("File")

        # open action
        open_action = QAction("&Open", self)
        file_menu.addAction(open_action)  # type: ignore
        open_action.setShortcut(QKeySequence.StandardKey.Open)

        # save action
        save_action = QAction("&Save", self)
        file_menu.addAction(save_action)  # type: ignore
        save_action.setShortcut(QKeySequence.StandardKey.Save)

        # connect file menu actions to slot
        open_action.triggered.connect(self.open_new_file)  # type: ignore
        save_action.triggered.connect(self.write_script)  # type: ignore

        # set menu bar
        self.setMenuBar(menubar)

    def initialize_central_widget(self, screen_geo: QRect):
        # create layout for central widget
        layout = QVBoxLayout()

        # create layout for search bar
        self.search_layout = QHBoxLayout()

        # create search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search")
        self.search_layout.addWidget(self.search_bar)

        # connect the QLineEdit's textChanged signal
        self.search_bar.textChanged.connect(self.hide_dynamic_widget)  # type: ignore
        self.search_bar.textChanged.connect(self.perform_search)  # type: ignore

        # create 'Match case' checkbox
        self.match_case = QCheckBox()
        self.match_case.setText("Match case")
        self.search_layout.addWidget(self.match_case)

        # connect the stateChanged signal of the `Match case` checkbox
        self.match_case.stateChanged.connect(self.hide_dynamic_widget)  # type: ignore
        self.match_case.stateChanged.connect(self.perform_search)  # type: ignore

        # create 'Match whole word only' checkbox
        self.match_whole_word = QCheckBox()
        self.match_whole_word.setText("Match whole word only")
        self.search_layout.addWidget(self.match_whole_word)

        # connect the stateChanged signal of the `Match whole word only` checkbox
        self.match_whole_word.stateChanged.connect(self.hide_dynamic_widget)  # type: ignore
        self.match_whole_word.stateChanged.connect(self.perform_search)  # type: ignore

        # create 'Exact match only' checkbox
        self.exact_match = QCheckBox()
        self.exact_match.setText("Exact match only")
        self.search_layout.addWidget(self.exact_match)

        # connect the stateChanged signal of the `Exact match only` checkbox
        self.exact_match.stateChanged.connect(self.hide_dynamic_widget)  # type: ignore
        self.exact_match.stateChanged.connect(self.perform_search)  # type: ignore

        # create 'Regex search' checkbox
        self.regex_search = QCheckBox()
        self.regex_search.setText("Regex search")
        self.search_layout.addWidget(self.regex_search)

        # connect the stateChanged signal of the `Regex search` checkbox
        self.regex_search.stateChanged.connect(self.hide_dynamic_widget)  # type: ignore
        self.regex_search.stateChanged.connect(self.perform_search)  # type: ignore

        # create spacer to maintain consistent layout
        self.spacer = QSpacerItem(
            240, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.search_layout.addItem(self.spacer)

        # create label
        self.label = QLabel("Set all to:")
        self.label.setVisible(False)
        self.search_layout.addWidget(self.label)

        # create apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.setFixedSize(85, 25)
        self.apply_button.clicked.connect(lambda: self.check_widget_value(self.dynamic_widget))  # type: ignore

        # add search layot to layout
        layout.addLayout(self.search_layout)

        # add table view to layout
        layout.addWidget(self.table_view, 1)

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
        export_button.clicked.connect(self.write_script)  # type: ignore

        # add button to horizontal layout
        button_layout.addWidget(export_button)

        # add horizontal layout to main layout
        layout.addLayout(button_layout)

    def center_main_window(self, screen_geo: QRect):
        # center the main window on the screen
        self.move(screen_geo.center() - self.rect().center())

    def show_message(self, type: str, message: str):
        # define constants
        INFO_TYPE = "Information"
        WARNING_TYPE = "Warning"

        if type == INFO_TYPE:
            QMessageBox.information(self, type, message, QMessageBox.StandardButton.Ok)
        elif type == WARNING_TYPE:
            QMessageBox.warning(self, type, message, QMessageBox.StandardButton.Ok)

    def open_new_file(self):
        file_path = self.open_file_dialog()
        if file_path:
            self.open_file.emit(file_path)
        self.setDisabled(False)

    def open_file_dialog(self) -> str:
        self.setDisabled(True)  # temporarily disable the UI while loading
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text files (*.txt)"
        )
        return file_path

    def save_file_dialog(self) -> str:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "setupvar-script.nsh",
            "EFI Shell scripts (*.nsh);; All files (*.*)",
        )
        return file_path

    def get_dict(
        self, dict: dict[str, dict[str, OneOfDict | NumericDict | CheckBoxDict]]
    ):
        self.settings_dict = dict

    def add_oneof(self, name: str, varstore: str, varoffset: str):
        self.table_data.append([name, varstore, varoffset])
        self.table_model.layoutChanged.emit()

    def add_oneof_option(self, oneofoption_name: str, oneofoption_default: str | None):
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
        self.table_data.append([name, varstore, varoffset])
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
        self.table_data.append([name, varstore, varoffset])
        self.table_model.layoutChanged.emit()

        row_position = len(self.table_data) - 1  # adjusting for 0-based indexing
        current_item = self.table_model.index(row_position, 3)
        checkbox = QCheckBox(self)
        if default == "Enabled":
            checkbox.setChecked(True)
        self.table_view.setIndexWidget(current_item, checkbox)

    def perform_search(self):
        search_text = self.search_bar.text()
        match_case = self.match_case.isChecked()
        match_whole_word = self.match_whole_word.isChecked()
        exact_match = self.exact_match.isChecked()
        regex_search = self.regex_search.isChecked()

        if len(search_text) >= 2:
            self.table_model.setFilter(
                search_text, match_case, match_whole_word, exact_match, regex_search
            )
        else:
            self.table_model.setFilter(
                "", match_case, match_whole_word, exact_match=False, regex_search=False
            )

        # update visibility of rows
        self.update_rows_visibility()

    def update_rows_visibility(self):
        # track rows that should be visible
        self.filtered_rows = set(
            self.table_model.table_data.index(row)
            for row in self.table_model.filtered_data
        )

        for row in range(self.table_model.rowCount()):
            is_visible = row in self.filtered_rows
            self.table_view.setRowHidden(
                row, not is_visible
            )  # hide rows that are not in the filtered set

        # ensure that the table view is updated
        viewport = self.table_view.viewport()
        if viewport is not None:
            viewport.update()

        self.check_widgets(self.filtered_rows)

    def check_widgets(self, visible_rows: set[int]):
        if len(visible_rows) > 1:  # mass selection is not necessary otherwise
            # get the class of the first widget in the visible rows
            first_row = next(iter(visible_rows), None)
            if first_row is None:
                return

            first_widget_class = self.get_widget_class(first_row, column=3)

            # verify all widgets are of the same type
            if not all(
                self.get_widget_class(row, column=3) == first_widget_class
                for row in visible_rows
            ):
                return  # exit if widgets differ

            # create and configure the dynamic widget based on the widget type
            self.dynamic_widget = self.create_dynamic_widget(first_widget_class)
            if self.dynamic_widget is not None:
                if first_widget_class == "QComboBox":
                    data = self.collect_data_for_widget(visible_rows)

                    self.dynamic_widget = cast(QComboBox, self.dynamic_widget)
                    self.dynamic_widget.addItems(data.keys())
                elif first_widget_class == "QSpinBox":
                    self.dynamic_widget = cast(QSpinBox, self.dynamic_widget)
                    self.dynamic_widget.setMinimum(-2147483648)
                    self.dynamic_widget.setMaximum(2147483647)

                if self.has_spacer_item(self.search_layout):
                    self.show_dynamic_widget()

    def get_widget_class(self, row: int, column: int) -> str:
        """Helper to retrieve the class name of a widget at a specific row and column."""
        widget_index = self.table_model.index(row, column)
        widget = self.table_view.indexWidget(widget_index)
        return widget.__class__.__name__ if widget else ""

    def create_dynamic_widget(self, widget_class_name: str) -> QWidget | None:
        """Creates a dynamic widget based on widget class name."""
        widget_mapping = {
            "QComboBox": QComboBox,
            "QSpinBox": QSpinBox,
            "QCheckBox": QCheckBox,
        }
        widget_constructor = widget_mapping.get(widget_class_name)
        if widget_constructor:
            dynamic_widget = widget_constructor()
            dynamic_widget.setMinimumSize(85, 23)
            return dynamic_widget
        return None

    def collect_data_for_widget(self, visible_rows: set[int]) -> dict[str, str]:
        """Collects relevant data for populating the QComboBox used for bulk setting adjustments."""
        data: dict[str, str] = {}
        for index, row in enumerate(visible_rows):
            varstore_index = self.table_model.index(row, 1)
            varoffset_index = self.table_model.index(row, 2)

            varstore = str(self.table_model.data(varstore_index))
            varoffset = str(self.table_model.data(varoffset_index))

            if self.settings_dict:
                oneof_dict = cast(OneOfDict, self.settings_dict[varstore][varoffset])

                for option_name, option_value in oneof_dict["options"].items():
                    if data.get(option_name) == option_value:
                        keys_to_delete = [
                            key for key in data if key not in oneof_dict["options"]
                        ]
                        for key in keys_to_delete:
                            del data[key]
                    elif data.get(option_name) is None and index == 0:
                        data[option_name] = option_value
                    else:
                        keys_to_delete = [
                            key for key in data if key not in oneof_dict["options"]
                        ]
                        for key in keys_to_delete:
                            del data[key]
        return data

    def show_dynamic_widget(self):
        self.search_layout.removeItem(self.spacer)
        self.label.setVisible(True)
        self.search_layout.addWidget(self.label)
        self.search_layout.addWidget(self.dynamic_widget)
        self.search_layout.addWidget(self.apply_button)
        self.apply_button.setVisible(True)

    def hide_dynamic_widget(self):
        self.label.setVisible(False)
        self.search_layout.removeWidget(self.label)
        if self.dynamic_widget is not None:
            self.dynamic_widget.setVisible(False)
            self.search_layout.removeWidget(self.dynamic_widget)
        self.apply_button.setVisible(False)
        self.search_layout.removeWidget(self.apply_button)
        if not self.has_spacer_item(self.search_layout):
            self.search_layout.addItem(self.spacer)

    def has_spacer_item(self, layout: QHBoxLayout) -> bool:
        """Helper to determine whether the layout contains a QSpacerItem."""
        return any(
            isinstance(layout.itemAt(i), QSpacerItem) for i in range(layout.count())
        )

    def check_widget_value(self, widget: QWidget):
        """Set values for widgets in the filtered rows based on the initial widget's value."""
        value = None  # initialize value to ensure it is always bound

        if isinstance(widget, QComboBox):
            value = widget.currentText()
        elif isinstance(widget, QSpinBox):
            value = widget.value()
        elif isinstance(widget, QCheckBox):
            value = widget.isChecked()

        if value is not None:
            for row in self.filtered_rows:
                widget_index = self.table_model.index(row, 3)
                row_widget = self.table_view.indexWidget(widget_index)

                if isinstance(row_widget, QComboBox):
                    row_widget.setCurrentText(str(value))
                elif isinstance(row_widget, QSpinBox):
                    row_widget.setValue(int(value))
                elif isinstance(row_widget, QCheckBox):
                    row_widget.setChecked(bool(value))

    def write_script(self):
        self.export.append(
            "# The script was created with setupvar-builder (https://github.com/ab3lkaizen/setupvar-builder)\n\n"
        )  # attribution at the top of the script file

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
        self.export_script(file_path)

    def export_oneof(self, name: str, varstore: str, varoffset: str, widget: QComboBox):
        oneofoption_name = widget.currentText()
        if self.settings_dict is not None:
            if (
                varstore in self.settings_dict
                and varoffset in self.settings_dict[varstore]
                and oneofoption_name
                != self.settings_dict[varstore][varoffset]["default"]
            ):
                oneof_dict = cast(OneOfDict, self.settings_dict[varstore][varoffset])
                option = oneof_dict["options"].get(oneofoption_name)
                size = oneof_dict["size"]
                self.export.append(
                    f"# {name}: {oneofoption_name}\nsetup_var.efi {varoffset} {option} -s {size} -n {varstore}\n\n"
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

    def export_script(self, file_path: str):
        if file_path:
            name_index = self.table_model.index(0, 0)
            varstore_index = self.table_model.index(0, 1)
            varoffset_index = self.table_model.index(0, 2)

            name = self.table_model.data(name_index)
            varstore = self.table_model.data(varstore_index)
            varoffset = self.table_model.data(varoffset_index)

            self.export.append(
                f"# read {name} and reboot\nsetup_var.efi {varoffset} -n {varstore} -r"
            )

            with open(file_path, "w", encoding="utf8") as output:
                output.writelines(self.export)

        # clear data
        self.export.clear()

    def clear_data(self):
        for row in range(self.table_model.rowCount()):
            index = self.table_model.index(row, 3)
            self.table_view.setIndexWidget(index, None)

        self.table_model.options.clear()
        self.table_data.clear()
        if self.settings_dict:
            self.settings_dict.clear()
        self.table_model.layoutChanged.emit()
