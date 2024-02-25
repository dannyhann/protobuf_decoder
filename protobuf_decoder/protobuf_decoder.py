from __future__ import annotations
import re
import struct
import ctypes
from typing import List, Tuple, Union
from enum import Enum
import binascii
from dataclasses import dataclass

HEX_PATTERN = "^[\\0-9a-fA-F\\s]+$"
ParsedDataType = Union[str, int, "FixedBitsValue", "ParsedResults"]


class FixedBitsValue:
    _is_unsigned: bool
    _unsigned_int_value: int
    _signed_int_value: int
    _bits: int

    _value_type: str

    def __init__(self, bit_value: int, bits: int):
        self._bit_value = bit_value
        self._bits = bits
        self._parse()

    def _parse(self):
        if self._bits == 64:
            self._pack_fmt = "<q"
            self._unpack_fmt = "d"
            self._value_type = "double"
            self._signed_int_value = ctypes.c_int64(self._bit_value).value
            self._unsigned_int_value = ctypes.c_uint64(self._bit_value).value

        elif self._bits == 32:
            self._pack_fmt = "<l"
            self._unpack_fmt = "f"
            self._value_type = "float"
            self._signed_int_value = ctypes.c_int32(self._bit_value).value
            self._unsigned_int_value = ctypes.c_uint32(self._bit_value).value

        else:
            raise ValueError(f"Not Supported: {self._bits}bits")

        if self._bit_value > 0 and self._signed_int_value == 0 and self._unsigned_int_value == 0:
            raise ValueError(f"Invalid {self._bits} bits range: {self._bit_value}")

        self._is_unsigned = not self._signed_int_value == self._unsigned_int_value

    @property
    def int(self):
        return self._signed_int_value

    @property
    def unsigned_int(self):
        return self._unsigned_int_value

    @property
    def signed_int(self):
        return self._signed_int_value

    @property
    def value(self):
        return struct.unpack(self._unpack_fmt, struct.pack(self._pack_fmt, self._signed_int_value))[0]

    def __str__(self):
        _name = f"Fixed{self._bits}Value"
        _value = f"{self._value_type}:{self.value}"
        if self._is_unsigned:
            return f"{_name}(unsigned_int:{self._unsigned_int_value}, signed_int: {self._signed_int_value}, {_value})"
        return f"{_name}(int:{self._unsigned_int_value}, {_value})"

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        dict_result = dict(
            value=self.value,
            signed_int=self.signed_int,
            unsigned_int=self.unsigned_int,
            value_type=self._value_type,
        )

        if not self._is_unsigned:
            dict_result.pop("unsigned_int")

        return dict_result


@dataclass(init=False)
class ParsedResult:
    field: int
    wire_type: str
    data: ParsedDataType

    def __init__(self, field: int, wire_type: str, data: ParsedDataType):
        self.field = field
        self.wire_type = wire_type
        self.data = data

    def to_dict(self):
        if isinstance(self.data, ParsedResults):
            data = self.data.to_dict()
        elif isinstance(self.data, FixedBitsValue):
            data = self.data.to_dict()
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
    remain_data: str = None

    @property
    def has_results(self):
        return len(self.results) > 0

    @property
    def has_remain_data(self):
        return self.remain_data is not None

    def __getitem__(self, item):
        return self.results[item]

    def to_dict(self):
        results = [result.to_dict() for result in self.results]
        dict_results = dict(
            results=results,
        )
        if self.has_remain_data:
            dict_results["remain_data"] = self.remain_data

        return dict_results


class State(Enum):
    FIND_FIELD = 1
    PARSE_VARINT = 2
    PARSE_LENGTH_DELIMITED = 3
    GET_DELIMITED_DATA = 4
    TERMINATED = 5

    PARSE_BIT64 = 6
    PARSE_BIT32 = 7

    PARSE_START_GROUP = 8
    PARSE_END_GROUP = 9


class WireType(Enum):
    VARINT = 0
    LEN = 2

    I64 = 1
    I32 = 5

    SGROUP = 3  # deprecated
    EGROUP = 4  # deprecated


class Utils:

    @classmethod
    def sanitize_input(cls, string: str) -> str:
        return string.replace("\n", " ")

    @classmethod
    def validate(cls, string: str) -> Tuple[bool, str]:
        regex_validator = re.compile(HEX_PATTERN)
        string = cls.sanitize_input(string)
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

    @classmethod
    def chunk_to_hex_string(cls, chunk) -> str:
        return hex(chunk)[2:].zfill(2)

    @classmethod
    def change_endian(cls, string) -> str:
        is_valid, valid_string = cls.validate(string)
        if not is_valid:
            raise ValueError("Invalid hex format")

        _output = []

        _chunk_buffer = []
        for chunk in cls.get_chunked_list(valid_string):
            _chunk_buffer.append(chunk)
            if len(_chunk_buffer) == 2:
                _chunk_buffer.reverse()
                for _chunk in _chunk_buffer:
                    _output.append(_chunk)
                _chunk_buffer = []

        for _chunk in _chunk_buffer:
            _output.append(_chunk)

        return " ".join(_output)

    @classmethod
    def show_parsed_results(cls, parsed_results: ParsedResults, depth=0, print_func=print):
        if parsed_results.has_results:
            for result in parsed_results.results:
                if isinstance(result.data, ParsedResults):
                    print_func("\t" * depth, f"[{result.field}: {result.wire_type}] =>")
                    cls.show_parsed_results(result.data, depth + 1)
                else:
                    print_func("\t" * depth, f"[{result.field}: {result.wire_type}] => {result.data}")
        if parsed_results.has_remain_data:
            print_func("\t" * depth, f"left over bytes: {parsed_results.remain_data}")


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

    @property
    def fetching_count(self):
        return self._fetch_index

    @property
    def fetching_bits(self):
        return self.fetching_count * 8

    def fetch_64bits(self):
        self.set_data_length(8 + 1)

    def fetch_32bits(self):
        self.set_data_length(4 + 1)


class RemainChunkTransaction:
    def __init__(self):
        self._is_done = True
        self._remain_hex_string_list = []

    def consume_chunk(self, chunk):
        self._remain_hex_string_list.append(
            Utils.chunk_to_hex_string(chunk)
        )

    def flush_chunk(self):
        self._remain_hex_string_list = []

    def start(self):
        self._is_done = False

    def done(self):
        self._is_done = True
        self.flush_chunk()

    @property
    def is_done(self):
        return self._is_done

    @property
    def remain_hex_string_list(self):
        return self._remain_hex_string_list

    @property
    def remain_hex_string(self):
        return " ".join(self._remain_hex_string_list)

    @property
    def has_remain_data(self):
        return len(self._remain_hex_string_list) > 0


class Parser:
    def __init__(self, nexted_depth: int = 0, strict: bool = False):
        self._nested_depth = nexted_depth
        self._buffer = BytesBuffer()
        self._fetcher = Fetcher()
        self._target_field = None
        self._parsed_data: List[ParsedResult] = []
        self._state = State.FIND_FIELD
        self._is_strict = strict

        self._t = RemainChunkTransaction()

    def _create_nested_parser(self) -> Parser:
        return Parser(nexted_depth=self._nested_depth + 1, strict=self._is_strict)

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

    def _get_buffered_value(self, mask=7) -> int:
        bit_value = 0
        for idx, byte_string in enumerate(self._buffer):
            bit_value += byte_string << (mask * idx)
        return bit_value

    def _next_buffer_handler(self, value):
        self._buffer.append(value)

    def _handler_find_field(self, chunk):
        value = self._get_value(chunk)
        if self._has_next(chunk):
            return self._next_buffer_handler(value)

        self._t.start()

        self._buffer.append(value)
        bit_value = self._get_buffered_value()
        wire_type, field = self._parse_wire_type(bit_value)
        self._target_field = field

        if wire_type == WireType.VARINT.value:
            self._state = State.PARSE_VARINT
        elif wire_type == WireType.LEN.value:
            self._state = State.PARSE_LENGTH_DELIMITED
        elif wire_type == WireType.I64.value:
            self._state = State.PARSE_BIT64
        elif wire_type == WireType.I32.value:
            self._state = State.PARSE_BIT32
        elif wire_type == WireType.SGROUP.value:
            self._state = State.PARSE_START_GROUP
        elif wire_type == WireType.EGROUP.value:
            self._state = State.PARSE_END_GROUP
        elif wire_type == WireType.EGROUP.value:
            self._state = State.TERMINATED
        else:
            if self._is_strict:
                raise AssertionError(f"Invalid wire_type: {wire_type}")
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
        self._t.done()

    def _parse_fixed_handler(self, chunk):
        self._next_buffer_handler(chunk)
        self._fetcher.fetch()

        if not self._fetcher.has_next:
            bits = self._fetcher.fetching_bits
            int_value = self._get_buffered_value(mask=8)

            self._parsed_data.append(
                ParsedResult(
                    field=self._target_field,
                    wire_type=f"fixed{bits}",
                    data=FixedBitsValue(bit_value=int_value, bits=bits)
                )
            )

            self._state = State.FIND_FIELD
            self._buffer.flush()
            self._fetcher.seek()
            self._t.done()

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
        self._t.done()

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
        self._t.done()

    def _next_get_delimited_data_handler(self, value):
        self._fetcher.fetch()
        self._buffer.append(value)

    @staticmethod
    def is_maybe_nested_protobuf(string_or_not) -> bool:
        """
        Determine if the given input might be a nested protobuf.

        Args:
            string_or_not (str): Input string or data to be checked.

        Returns:
            bool: True if the input is likely a nested protobuf, otherwise False.
        """

        # Try to convert the input hex string to UTF-8
        try:
            _data = Utils.hex_string_to_utf8(string_or_not)
        except UnicodeDecodeError:
            # If a UnicodeDecodeError occurs, it's possibly a nested protobuf
            return True

        # Check the first 4 characters of the decoded data
        for c in _data[0:4]:
            # If any character has an ordinal value less than 0x20,
            # it's possibly a nested protobuf
            if ord(c) < 0x20:
                return True

        # If none of the above conditions were met, it's likely not a nested protobuf
        return False

    def _get_delimited_data_handler(self, chunk):
        value = chunk
        if self._fetcher.has_next:
            return self._next_get_delimited_data_handler(value)

        self._buffer.append(value)
        data = list(map(lambda x: hex(x)[2:].zfill(2), self._buffer))

        string_or_not = "".join(data)
        if self.is_maybe_nested_protobuf(string_or_not):
            data = self._create_nested_parser().parse(string_or_not)
            wire_type = "length_delimited"
        else:
            data = Utils.hex_string_to_utf8(string_or_not)
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
        self._t.done()

    def _create_parsed_results(self) -> ParsedResults:
        if not self._t.has_remain_data:
            return ParsedResults(results=self._parsed_data)

        return ParsedResults(
            results=self._parsed_data,
            remain_data=self._t.remain_hex_string
        )

    def parse(self, test_target) -> ParsedResults:
        if test_target == "":
            return self._create_parsed_results()

        is_valid, validate_string = Utils.validate(test_target)
        if not is_valid:
            raise ValueError("Invalid hex format")

        for hex_chunk in Utils.get_chunked_list(validate_string):
            chunk = Utils.hex_string_to_decimal(hex_chunk)

            self._t.consume_chunk(chunk)

            if self._state == State.FIND_FIELD:
                self._handler_find_field(chunk)

            elif self._state == State.PARSE_VARINT:
                self._parse_varint_handler(chunk)

            elif self._state == State.PARSE_LENGTH_DELIMITED:
                self._parse_length_delimited_handler(chunk)

            elif self._state == State.GET_DELIMITED_DATA:
                self._get_delimited_data_handler(chunk)

            elif self._state == State.PARSE_BIT64:
                self._fetcher.fetch_64bits()
                self._parse_fixed_handler(chunk)

            elif self._state == State.PARSE_BIT32:
                self._fetcher.fetch_32bits()
                self._parse_fixed_handler(chunk)

            elif self._state in (State.PARSE_START_GROUP, State.PARSE_END_GROUP):
                continue

            elif self._state == State.TERMINATED:
                pass

            else:
                raise ValueError(f"Unsupported State {self._state}")

        if self._is_strict:
            assert self._t.is_done, "parsing process is not done, Maybe invalid protobuf"

        return self._create_parsed_results()
