from typing import TypedDict


class OneOfDict(TypedDict):
    type: str
    name: str
    size: str
    options: dict[str, str]
    default: str | None


class NumericDict(TypedDict):
    type: str
    name: str
    size: str
    min: int
    max: int
    default: int


class CheckBoxDict(TypedDict):
    type: str
    name: str
    default: str
