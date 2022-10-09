from __future__ import annotations
import re
from typing import List, Tuple, Union
from enum import Enum
import binascii
from dataclasses import dataclass

HEX_PATTERN = "^[\\0-9a-fA-F\\s]+$"


@dataclass(init=False)
class ParsedResult:
    field: int
    wire_type: str
    data: Union[str, int, List[ParsedResult]]

    def __init__(self, field: int, wire_type: str, data: Union[str, int, ParsedResults]):
        self.field = field
        self.wire_type = wire_type
        if isinstance(data, ParsedResults):
            self.data = data.results
        else:
            self.data = data

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


@dataclass
class ParsedResults:
    results: List[ParsedResult]

    @property
    def has_results(self):
        return len(self.results) > 0


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
        self._data_length = 0
        self._fetch_index = 0

    def set_data_length(self, data_length):
        self._valid(data_length)
        self._data_length = data_length

    @staticmethod
    def _valid(data_length):
        if not isinstance(data_length, int):
            raise TypeError(f"a int object is required, not {repr(type(data_length))}")

        if data_length <= 0:
            raise ValueError(f"data_length should be positive")

    def fetch(self):
        self._fetch_index += 1

    @property
    def has_next(self):
        return self._fetch_index < self._data_length - 1

    def seek(self, index=0):
        self._fetch_index = index


class Parser:
    def __init__(self):
        self._buffer = BytesBuffer()
        self._fetcher = Fetcher()
        self._target_field = None
        self._parsed_data: List[ParsedResult] = []
        self._state = State.FIND_FIELD

    @staticmethod
    def _has_next(chunk_bytes) -> bool:
        return bool(chunk_bytes & 0x80)

    @staticmethod
    def _get_value(chunk_bytes) -> int:
        return chunk_bytes & 0x7F

    @staticmethod
    def _parse_wire_type(chunk_bytes) -> Tuple[int, int]:
        wire_type = chunk_bytes & 0x7
        field = chunk_bytes >> 3
        return wire_type, field

    def _get_buffered_value(self) -> int:
        bit_value = 0
        for idx, byte_string in enumerate(self._buffer):
            bit_value += byte_string << (7 * idx)
        return bit_value

    def _next_buffer_handler(self, value):
        self._buffer.append(value)

    def _handler_find_field(self, chunk):
        value = self._get_value(chunk)
        if self._has_next(chunk):
            return self._next_buffer_handler(value)

        self._buffer.append(value)
        bit_value = self._get_buffered_value()
        wire_type, field = self._parse_wire_type(bit_value)
        self._target_field = field

        if wire_type == WireType.VARINT.value:
            self._state = State.PARSE_VARINT
        elif wire_type == WireType.LENGTH_DELIMITED.value:
            self._state = State.PARSE_LENGTH_DELIMITED
        elif wire_type == WireType.END_GROUP.value:
            self._state = State.TERMINATED
        elif wire_type in (WireType.BIT32.value, WireType.BIT64.value, WireType.START_GROUP.value):
            raise ValueError(f"Unsupported wire type {wire_type}")
        else:
            self._state = State.TERMINATED
        self._buffer.flush()

    def _parse_varint_handler(self, chunk):
        value = self._get_value(chunk)
        if self._has_next(chunk):
            return self._next_buffer_handler(value)

        self._buffer.append(value)
        bit_value = self._get_buffered_value()
        self._parsed_data.append(
            ParsedResult(
                field=self._target_field,
                wire_type="varint",
                data=bit_value
            )
        )

        self._state = State.FIND_FIELD
        self._buffer.flush()

    def _zero_length_delimited_handler(self):
        self._parsed_data.append(
            ParsedResult(
                field=self._target_field,
                wire_type="string",
                data=""
            )
        )
        self._state = State.FIND_FIELD
        self._buffer.flush()

    def _parse_length_delimited_handler(self, chunk):
        value = self._get_value(chunk)
        if self._has_next(chunk):
            return self._next_buffer_handler(value)

        self._buffer.append(value)
        data_length = self._get_buffered_value()
        if data_length == 0:
            return self._zero_length_delimited_handler()

        self._fetcher.set_data_length(data_length)
        self._state = State.GET_DELIMITED_DATA
        self._buffer.flush()

    def _next_get_delimited_data_handler(self, value):
        self._fetcher.fetch()
        self._buffer.append(value)

    def _get_delimited_data_handler(self, chunk):
        value = chunk
        if self._fetcher.has_next:
            return self._next_get_delimited_data_handler(value)

        self._buffer.append(value)
        data = list(map(lambda x: hex(x)[2:].zfill(2), self._buffer))
        sub_parsed_data = Parser().parse(" ".join(data))
        if sub_parsed_data.has_results:
            data = sub_parsed_data
            wire_type = "length_delimited"
        else:
            data = Utils.hex_string_to_utf8("".join(data))
            wire_type = "string"

        self._parsed_data.append(
            ParsedResult(
                field=self._target_field,
                wire_type=wire_type,
                data=data
            )
        )
        self._buffer.flush()
        self._fetcher.seek()
        self._state = State.FIND_FIELD

    def _create_parsed_results(self) -> ParsedResults:
        return ParsedResults(results=self._parsed_data)

    def parse(self, test_target) -> ParsedResults:
        if test_target == "":
            return self._create_parsed_results()

        is_valid, validate_string = Utils.validate(test_target)
        if not is_valid:
            raise ValueError("Invalid hex format")

        for chunk in Utils.get_chunked_list(validate_string):
            chunk = Utils.hex_string_to_decimal(chunk)

            if self._state == State.FIND_FIELD:
                self._handler_find_field(chunk)

            elif self._state == State.PARSE_VARINT:
                self._parse_varint_handler(chunk)

            elif self._state == State.PARSE_LENGTH_DELIMITED:
                self._parse_length_delimited_handler(chunk)

            elif self._state == State.GET_DELIMITED_DATA:
                self._get_delimited_data_handler(chunk)

            elif self._state == State.TERMINATED:
                return self._create_parsed_results()
            else:
                raise ValueError(f"Unsupported State {self._state}")

        return self._create_parsed_results()
