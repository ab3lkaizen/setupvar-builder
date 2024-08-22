import re
import sys
from typing import cast

from PyQt6.QtWidgets import QApplication

from dict_types import CheckBoxDict, NumericDict, OneOfDict
from gui import MainWindow


def handle_file_selected(file_path: str) -> None:
    window.clear_data()
    parsed_input_file = parse_input_file(file_path)
    if parsed_input_file:
        settings_dict = dict_population(parsed_input_file)
        table_population(settings_dict)
        window.get_dict(settings_dict)


def is_hex_line(start_line: str) -> bool:
    """Matches a hexadecimal number prefixed with 0x at the beginning of a line"""
    return bool(re.match(r"^0x[0-9a-fA-F]+:", start_line))


def parse_input_file(input_file: str) -> list[str]:
    extraction_mode = "Extraction mode: UEFI"
    pattern = re.compile(r"\{.*\}")
    pattern_found = False
    parsed_input_file: list[str] = []
    accumulator: list[str] = []

    with open(input_file, "r", encoding="utf8") as in_file:
        first_line = in_file.readline()

        # validate input file
        if extraction_mode not in first_line:
            window.show_message("Warning", "Invalid file")
            return []  # return empty list if invalid

        for line in in_file:
            line = line.strip()

            if not pattern_found:
                if pattern.search(line):
                    pattern_found = True

            if is_hex_line(line):
                if accumulator:  # if accumulator is not empty
                    parsed_input_file.append("\n".join(accumulator))
                    accumulator = []  # reset accumulator

                accumulator.append(line)
            else:
                if accumulator:
                    accumulator[-1] += " " + line

        if accumulator:
            parsed_input_file.append("\n".join(accumulator))

        # validate input file
        if not pattern_found:
            window.show_message(
                "Information", 'Use the "verbose" option of IFRExtractor'
            )
            return []  # return empty list if invalid

        return parsed_input_file


def dict_population(
    parsed_file: list[str],
) -> dict[str, dict[str, OneOfDict | NumericDict | CheckBoxDict]]:
    varstore_pattern = re.compile(
        r'VarStoreId: 0x([0-9A-Fa-f]+), Size: 0x([0-9A-Fa-f]+), Name: "(.*?)"'
    )
    oneof_pattern = re.compile(
        r'OneOf Prompt:.*?"(.+?)", Help: "(.*?)", QuestionFlags: 0x([0-9A-Fa-f]+), QuestionId: 0x([0-9A-Fa-f]+), VarStoreId: 0x([0-9A-Fa-f]+), VarOffset: 0x([0-9A-Fa-f]+), Flags: 0x([0-9A-Fa-f]+), Size: ([0-9A-Fa-f]+)'
    )
    oneofoption_pattern = re.compile(
        r'OneOfOption Option: "(.*?)" Value: ([\d]+)(, Default)?'
    )
    numeric_pattern = re.compile(
        r'Numeric Prompt: "(.+?)", Help: "(.*?)", QuestionFlags: 0x([0-9A-Fa-f]+), QuestionId: 0x([0-9A-Fa-f]+), VarStoreId: 0x([0-9A-Fa-f]+), VarOffset: 0x([0-9A-Fa-f]+), Flags: 0x([0-9A-Fa-f]+), Size: ([0-9A-Fa-f]+), Min: 0x([0-9A-Fa-f]+), Max: 0x([0-9A-Fa-f]+), Step: 0x([0-9A-Fa-f]+)'
    )
    checkbox_pattern = re.compile(
        r'CheckBox Prompt: "(.+?)", Help: "(.*?)", QuestionFlags: 0x([0-9A-Fa-f]+), QuestionId: 0x([0-9A-Fa-f]+), VarStoreId: 0x([0-9A-Fa-f]+), VarOffset: 0x([0-9A-Fa-f]+), Flags: 0x([0-9A-Fa-f]+), Default: (Enabled|Disabled)'
    )
    default_pattern = re.compile(r"Default DefaultId: 0x0 Value: ([\d]+)")

    varstores: dict[str, str] = {}
    settings_dict: dict[str, dict[str, OneOfDict | NumericDict | CheckBoxDict]] = {}

    oneof_name = oneof_varstore = oneof_varoffset = numeric_name = numeric_varstore = (
        numeric_varoffset
    ) = last_oneof_name = default = last_match = child_match = None

    for match in parsed_file:
        # check for matches in each line
        varstore_match = re.search(varstore_pattern, match)
        oneof_match = re.search(oneof_pattern, match)
        oneofoption_match = re.search(oneofoption_pattern, match)
        numeric_match = re.search(numeric_pattern, match)
        checkbox_match = re.search(checkbox_pattern, match)
        default_match = re.search(default_pattern, match)

        if varstore_match:
            varstore_id = varstore_match.group(1)
            varstore_name = varstore_match.group(3)
            varstores[varstore_id] = varstore_name

        elif oneof_match:
            child_match = None  # reset

            oneof_name = oneof_match.group(1).strip()
            oneof_varstoreid = oneof_match.group(5)
            oneof_varstore = str(varstores.get(oneof_varstoreid))
            oneof_varoffset = str("0x" + oneof_match.group(6))
            oneof_size = hex(int(oneof_match.group(8)) // 8)

            # check if the varstore already exists in the dictionary
            if oneof_varstore not in settings_dict:
                settings_dict[oneof_varstore] = {}

            settings_dict[oneof_varstore][oneof_varoffset] = cast(
                OneOfDict,
                {
                    "type": "oneof",
                    "name": oneof_name,
                    "size": oneof_size,
                },
            )

            last_match = "oneof"

        elif oneofoption_match and last_match == "oneof":
            oneofoption_name = oneofoption_match.group(1).strip()
            oneofoption_value = hex(int(oneofoption_match.group(2)))
            oneofoption_value = (
                f"0x{oneofoption_value[2:].upper()}"  # formatting purposes
            )
            oneofoption_default = oneofoption_match.group(3)

            if (
                oneof_varstore in settings_dict
                and oneof_varoffset in settings_dict[oneof_varstore]
            ):
                oneof_dict = cast(
                    OneOfDict, settings_dict[oneof_varstore][oneof_varoffset]
                )

                if (
                    last_oneof_name == oneof_name
                    and default == oneofoption_value
                    or oneofoption_default
                ):
                    if "default" not in settings_dict[oneof_varstore][oneof_varoffset]:
                        oneof_dict["default"] = oneofoption_name

                if "options" not in settings_dict[oneof_varstore][oneof_varoffset]:
                    oneof_dict["options"] = {}

                oneof_dict["options"][oneofoption_name] = oneofoption_value

            child_match = "oneof_option"

        elif numeric_match:
            numeric_name = numeric_match.group(1).strip()
            numeric_varstoreid = numeric_match.group(5)
            numeric_varstore = str(varstores.get(numeric_varstoreid))
            numeric_varoffset = str("0x" + numeric_match.group(6))
            numeric_size = hex(int(numeric_match.group(8)) // 8)
            numeric_min = int(numeric_match.group(9), 16)
            numeric_max = int(numeric_match.group(10), 16)

            if numeric_varstore not in settings_dict:
                settings_dict[numeric_varstore] = {}

            settings_dict[numeric_varstore][numeric_varoffset] = cast(
                NumericDict,
                {
                    "type": "numeric",
                    "name": numeric_name,
                    "size": numeric_size,
                    "min": numeric_min,
                    "max": numeric_max,
                },
            )

            last_match = "numeric"

        elif checkbox_match:
            checkbox_name = checkbox_match.group(1).strip()
            checkbox_varstoreid = checkbox_match.group(5)
            checkbox_varstore = str(varstores.get(checkbox_varstoreid))
            checkbox_varoffset = "0x" + checkbox_match.group(6)
            checkbox_default = checkbox_match.group(8)

            if checkbox_varstore not in settings_dict:
                settings_dict[checkbox_varstore] = {}

            settings_dict[checkbox_varstore][checkbox_varoffset] = cast(
                CheckBoxDict,
                {
                    "type": "checkbox",
                    "name": checkbox_name,
                    "default": checkbox_default,
                },
            )

            last_match = "checkbox"

        elif default_match:
            default_value = default_match.group(1)
            if last_match == "oneof":
                if child_match:
                    default = hex(int(default_value))
                    default = f"0x{default[2:].upper()}"  # format to match `oneofoption_value`
                    if (
                        oneof_varstore in settings_dict
                        and oneof_varoffset in settings_dict[oneof_varstore]
                    ):
                        oneof_dict = cast(
                            OneOfDict, settings_dict[oneof_varstore][oneof_varoffset]
                        )
                        for option, value in oneof_dict["options"].items():
                            if value == default:
                                oneof_dict["default"] = option
                                break
                else:
                    default = hex(int(default_value))
                    default = f"0x{default[2:].upper()}"  # format to match `oneofoption_value`
                    last_oneof_name = oneof_name
            elif last_match == "numeric":
                default = int(default_value)
                if (
                    numeric_varstore in settings_dict
                    and numeric_varoffset in settings_dict[numeric_varstore]
                ):
                    numeric_dict = cast(
                        NumericDict, settings_dict[numeric_varstore][numeric_varoffset]
                    )
                    numeric_dict["default"] = default

    return settings_dict


def table_population(
    settings_dict: dict[str, dict[str, OneOfDict | NumericDict | CheckBoxDict]]
) -> None:
    for varstore, data_1 in settings_dict.items():
        for varoffset, data_2 in data_1.items():

            name = data_2["name"]
            default = None  # reset
            try:
                default = data_2["default"]
            except KeyError:
                pass

            if data_2["type"] == "oneof":
                data_2 = cast(OneOfDict, data_2)
                window.add_oneof(name, varstore, varoffset)

                options = data_2["options"]
                for key in options.keys():
                    window.add_oneof_option(
                        key, str(default) if default is not None else default
                    )

            elif data_2["type"] == "numeric":
                data_2 = cast(NumericDict, data_2)
                min = data_2["min"]
                max = data_2["max"]
                window.add_numeric(
                    name,
                    varstore,
                    varoffset,
                    min,
                    max,
                    int(default) if default is not None else default,
                )

            elif data_2["type"] == "checkbox":
                data_2 = cast(CheckBoxDict, data_2)
                window.add_checkbox(
                    name,
                    varstore,
                    varoffset,
                    str(default) if default is not None else default,
                )


def main() -> None:
    window.open_file.connect(handle_file_selected)  # type: ignore
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    main()
