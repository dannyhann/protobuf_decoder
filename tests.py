import pytest
from protobuf_decoder.protobuf_decoder import Utils, Parser, ParsedResult, ParsedResults


def test_binary_validate():
    is_valid, _ = Utils.validate("08 12")
    assert is_valid is True

    is_valid, _ = Utils.validate("0812")
    assert is_valid is True

    is_valid, _ = Utils.validate("08 12 2")
    assert is_valid is False

    is_valid, _ = Utils.validate("081H")
    assert is_valid is False


def test_get_chunked_list():
    _, validate_string = Utils.validate("08 12")
    chunked_list = Utils.get_chunked_list(validate_string)
    chunked_list = list(chunked_list)
    assert len(chunked_list) == 2
    assert chunked_list[0] == "08"
    assert chunked_list[1] == "12"


def test_hex_string_to_binary():
    binary = Utils.hex_string_to_binary("1")
    assert binary == "0001"

    binary = Utils.hex_string_to_binary("F")
    assert binary == "1111"

    with pytest.raises(ValueError):
        Utils.hex_string_to_binary("H")


def test_hex_string_to_decimal():
    assert Utils.hex_string_to_decimal("A") == 10
    assert Utils.hex_string_to_decimal("1") == 1
    assert Utils.hex_string_to_decimal("F") == 15
    with pytest.raises(ValueError):
        Utils.hex_string_to_decimal("G")


def test_hex_string_to_utf8():
    assert Utils.hex_string_to_utf8("74657374") == "test"
    assert Utils.hex_string_to_utf8("74 65 73 74 32") == "test2"
    assert Utils.hex_string_to_utf8("E2 9C 8A") == "✊"


def test_parse():
    """
    # proto
    message Test1 {
      required int32 a = 16;
    }

    # message
    {
      "a": 1
    }

    # binary
    80 01 01
    """

    test_target = "80 01 01"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([ParsedResult(field=16, wire_type="varint", data=1)])
    assert ParsedResult(field=16, wire_type="varint", data=1).to_dict() == dict(field=16, wire_type="varint", data=1)


def test_parse2():
    """
    # proto
    message Test1 {
      int32 a = 1;
      string b = 2;
    }

    # message
    {
      "a": 150,
      "b": "test"
    }

    # binary
    08 96 01 12 04 74 65 73 74
    """

    test_target = "08 96 01 12 04 74 65 73 74"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([ParsedResult(field=1, wire_type="varint", data=150),
                                         ParsedResult(field=2, wire_type="string", data='test')])


def test_parse3():
    """
    # proto
    message Test1 {
      string b = 2;
    }

    # message
    {
      "b": "testing"
    }

    # binary
    12 07 74 65 73 74 69 6e 67
    """
    test_target = "12 07 74 65 73 74 69 6e 67"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([ParsedResult(field=2, wire_type="string", data='testing')])


def test_parser4():
    """
    # proto
    message Test1 {
      int32 a = 1;
    }

    message Test2 {
      Test1 b = 3;
    }

    # message
    {
      "a": {
            "b": 150
            }
    }

    # binary
    1a 03 08 96 01
    """
    test_target = "1a 03 08 96 01"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(
        [ParsedResult(field=3, wire_type="length_delimited", data=ParsedResults(
            [ParsedResult(field=1, wire_type="varint", data=150)]))])


def test_parser5():
    """
    # proto
    message Test1 {
      string a = 1;
    }

    # message
    {
      "a": "테스트"
    }

    # binary
    0A 09 ED 85 8C EC 8A A4 ED 8A B8
    """
    test_target = "0A 09 ED 85 8C EC 8A A4 ED 8A B8"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([ParsedResult(field=1, wire_type="string", data='테스트')])


def test_parser6():
    """
    ['ed', '85', '8c', 'ec', '8a', 'a4', 'ed', '8a', 'b8'] is "테스트"
    """
    test_target = " ".join(['ed', '85', '8c', 'ec', '8a', 'a4', 'ed', '8a', 'b8'])
    parsed_data = Parser().parse(test_target)
    assert parsed_data.has_results is False


def test_parser7():
    """
    # proto
    message Test1 {
      required string a = 1;
    }

    # message
    {
      "a": "✊"
    }

    # binary
    0A 03 E2 9C 8A

    """
    test_target = "0A 03 E2 9C 8A"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([ParsedResult(field=1, wire_type="string", data='✊')])


def test_parser8():
    """
    # proto
    message Test1 {
      repeated string a = 1;
    }

    # message
    {
      "a": [
        "test",
        "test2"
      ]
    }

    # binary
    0A 04 74 65 73 74 0A 05 74 65 73 74 32

    """
    test_target = "0A 04 74 65 73 74 0A 05 74 65 73 74 32"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([
        ParsedResult(field=1, wire_type="string", data='test'),
        ParsedResult(field=1, wire_type="string", data='test2')
    ])


def test_zero_length_string():
    test_target = "0a 00 10 ff ff 03 18 17"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([
        ParsedResult(field=1, wire_type='string', data=''),
        ParsedResult(field=2, wire_type='varint', data=65535),
        ParsedResult(field=3, wire_type='varint', data=23)
    ])


def test_empty_string():
    test_target = ""
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([])
