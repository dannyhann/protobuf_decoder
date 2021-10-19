from __future__ import annotations
import re
from typing import List, Tuple, Union
from enum import Enum
import binascii
from dataclasses import dataclass

HEX_PATTERN = "^[\\0-9a-fA-F\\s]+$"


@dataclass
class ParsedResult:
    field: int
    wire_type: str
    data: Union[str, int, List[ParsedResult]]

    def to_dict(self):
        if isinstance(self.data, list):
            data = [sub_result.to_dict() for sub_result in self.data]
        else:
            data = self.data

        return dict(
            field=self.field,
            wire_type=self.wire_type,
            data=data
        )


class State(Enum):
    FIND_FIELD = 1
    PARSE_VARINT = 2
    PARSE_LENGTH_DELIMITED = 3
    GET_DELIMITED_DATA = 4
    TERMINATED = 5


class WireType(Enum):
    VARINT = 0
    LENGTH_DELIMITED = 2

    BIT64 = 1  # not supported
    BIT32 = 5  # not supported

    START_GROUP = 3  # deprecated
    END_GROUP = 4  # deprecated


class Utils:
    @classmethod
    def validate(cls, string: str) -> Tuple[bool, str]:
        regex_validator = re.compile(HEX_PATTERN)
        validate_result = regex_validator.match(string)
        if validate_result is None:
            return False, string

        hex_string = validate_result.string
        hex_string = hex_string.replace(" ", "")

        if len(hex_string) % 2 != 0:
            return False, hex_string

        return True, hex_string

    @classmethod
    def get_chunked_list(cls, string) -> List[str]:
        while string:
            yield string[:2]
            string = string[2:]

    @classmethod
    def hex_string_to_binary(cls, string) -> str:
        return bin(int(string, 16))[2:].zfill(4)

    @classmethod
    def hex_string_to_decimal(cls, string) -> int:
        return int(string, 16)

    @classmethod
    def hex_string_to_utf8(cls, string) -> str:
        string = string.replace(" ", "")
        return binascii.unhexlify(string).decode("utf-8")


class BytesBuffer:
    def __init__(self):
        self._buffer = []

    def append(self, byte_string):
        self._buffer.append(byte_string)

    def flush(self):
        self._buffer = []

    def __iter__(self):
        return iter(self._buffer)


class Fetcher:
    def __init__(self):
        self.data_length = 0
        self.fetch_index = 0

    def set_data_length(self, data_length):
        self.valid(data_length)
        self.data_length = data_length

    @staticmethod
    def valid(data_length):
        if not isinstance(data_length, int):
            raise TypeError(f"a int object is required, not {repr(type(data_length))}")

        if data_length < 0:
            raise ValueError(f"data_length should be positive")

    def fetch(self):
        self.fetch_index += 1

    @property
    def has_next(self):
        return self.fetch_index < self.data_length - 1

    def seek(self, index=0):
        self.fetch_index = index


class Parser:
    def __init__(self):
        self.buffer = BytesBuffer()
        self.fetcher = Fetcher()
        self.target_field = None
        self.parsed_data: List[ParsedResult] = []
        self.state = State.FIND_FIELD

    @staticmethod
    def has_next(chunk_bytes) -> bool:
        return bool(chunk_bytes & 0x80)

    @staticmethod
    def get_value(chunk_bytes) -> int:
        return chunk_bytes & 0x7F

    @staticmethod
    def parse_wire_type(chunk_bytes) -> Tuple[int, int]:
        wire_type = chunk_bytes & 0x7
        field = chunk_bytes >> 3
        return wire_type, field

    def get_buffered_value(self) -> int:
        bit_value = 0
        for idx, byte_string in enumerate(self.buffer):
            bit_value += byte_string << (7 * idx)
        return bit_value

    def handler_find_field(self, chunk):
        value = self.get_value(chunk)
        if self.has_next(chunk):
            self.buffer.append(value)
        else:
            self.buffer.append(value)
            bit_value = self.get_buffered_value()
            wire_type, field = self.parse_wire_type(bit_value)
            self.target_field = field

            if wire_type == WireType.VARINT.value:
                self.state = State.PARSE_VARINT
            elif wire_type == WireType.LENGTH_DELIMITED.value:
                self.state = State.PARSE_LENGTH_DELIMITED
            elif wire_type == WireType.END_GROUP.value:
                self.state = State.TERMINATED
            elif wire_type in (WireType.BIT32.value, WireType.BIT64.value, WireType.START_GROUP.value):
                raise ValueError(f"Unsupported wire type {wire_type}")
            else:
                self.state = State.TERMINATED
            self.buffer.flush()

    def parse_varint_handler(self, chunk):
        value = self.get_value(chunk)
        if self.has_next(chunk):
            self.buffer.append(value)
        else:
            self.buffer.append(value)
            bit_value = self.get_buffered_value()
            self.parsed_data.append(
                ParsedResult(
                    field=self.target_field,
                    wire_type="varint",
                    data=bit_value
                )
            )

            self.state = State.FIND_FIELD
            self.buffer.flush()

    def parse_length_delimited_handler(self, chunk):
        value = self.get_value(chunk)
        if self.has_next(chunk):
            self.buffer.append(value)
        else:
            self.buffer.append(value)
            data_length = self.get_buffered_value()
            self.fetcher.set_data_length(data_length)

            self.state = State.GET_DELIMITED_DATA

            self.buffer.flush()

    def get_delimited_data_handler(self, chunk):
        value = chunk
        if self.fetcher.has_next:
            self.fetcher.fetch()
            self.buffer.append(value)

        else:
            self.buffer.append(value)
            data = list(map(lambda x: hex(x)[2:].zfill(2), self.buffer))
            sub_parsed_date = Parser().parse(" ".join(data))
            if sub_parsed_date:
                data = sub_parsed_date
                wire_type = "length_delimited"
            else:
                data = Utils.hex_string_to_utf8("".join(data))
                wire_type = "string"

            self.parsed_data.append(
                ParsedResult(
                    field=self.target_field,
                    wire_type=wire_type,
                    data=data
                )
            )
            self.buffer.flush()
            self.fetcher.seek()
            self.state = State.FIND_FIELD

    def parse(self, test_target):
        is_valid, validate_string = Utils.validate(test_target)
        if not is_valid:
            raise ValueError("Invalid hex format")

        for chunk in Utils.get_chunked_list(validate_string):
            chunk = Utils.hex_string_to_decimal(chunk)

            if self.state == State.FIND_FIELD:
                self.handler_find_field(chunk)

            elif self.state == State.PARSE_VARINT:
                self.parse_varint_handler(chunk)

            elif self.state == State.PARSE_LENGTH_DELIMITED:
                self.parse_length_delimited_handler(chunk)

            elif self.state == State.GET_DELIMITED_DATA:
                self.get_delimited_data_handler(chunk)

            elif self.state == State.TERMINATED:
                return self.parsed_data
            else:
                raise ValueError(f"Unsupported State {self.state}")

        return self.parsed_data
