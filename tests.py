import pytest
import math
from protobuf_decoder.protobuf_decoder import Utils, Parser, ParsedResult, ParsedResults, FixedBitsValue


def show_parsed_results(parsed_results: ParsedResults, depth=0):
    if parsed_results.has_results:
        for result in parsed_results.results:
            if isinstance(result.data, ParsedResults):
                print("\t" * depth, f"[{result.field}: {result.wire_type}] =>")
                show_parsed_results(result.data, depth + 1)
            else:
                print("\t" * depth, f"[{result.field}: {result.wire_type}] => {result.data}")


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
    assert parsed_data.to_dict() == {'results': [{'field': 16, 'wire_type': 'varint', 'data': 1}]}


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
    assert parsed_data.to_dict() == {'results': [{'field': 1, 'wire_type': 'varint', 'data': 150},
                                                 {'field': 2, 'wire_type': 'string', 'data': 'test'}]}


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
    assert parsed_data.to_dict() == {'results': [{'field': 2, 'wire_type': 'string', 'data': 'testing'}]}


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
        [
            ParsedResult(field=3, wire_type="length_delimited", data=ParsedResults([
                ParsedResult(field=1, wire_type="varint", data=150)
            ]))
        ])
    assert parsed_data.to_dict() == {'results': [{'field': 3, 'wire_type': 'length_delimited', 'data': {
        'results': [{'field': 1, 'wire_type': 'varint', 'data': 150}]}}]}


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
    assert parsed_data.to_dict() == {'results': [{'field': 1, 'wire_type': 'string', 'data': '테스트'}]}


def test_parser6():
    """
    ['ed', '85', '8c', 'ec', '8a', 'a4', 'ed', '8a', 'b8'] is "테스트"
    """
    test_target = " ".join(['ed', '85', '8c', 'ec', '8a', 'a4', 'ed', '8a', 'b8'])
    parsed_data = Parser().parse(test_target)
    assert parsed_data.has_results is False
    assert parsed_data.to_dict() == {'results': []}


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
    assert parsed_data.to_dict() == {'results': [{'field': 1, 'wire_type': 'string', 'data': '✊'}]}


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
    assert parsed_data.to_dict() == {'results': [{'field': 1, 'wire_type': 'string', 'data': 'test'},
                                                 {'field': 1, 'wire_type': 'string', 'data': 'test2'}]}


def test_zero_length_string():
    test_target = "0a 00 10 ff ff 03 18 17"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([
        ParsedResult(field=1, wire_type='string', data=''),
        ParsedResult(field=2, wire_type='varint', data=65535),
        ParsedResult(field=3, wire_type='varint', data=23)
    ])
    assert parsed_data.to_dict() == {
        'results': [{'field': 1, 'wire_type': 'string', 'data': ''}, {'field': 2, 'wire_type': 'varint', 'data': 65535},
                    {'field': 3, 'wire_type': 'varint', 'data': 23}]}


def test_empty_string():
    test_target = ""
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults([])
    assert parsed_data.to_dict() == {'results': []}


def test_FixedBitsValue():
    value = FixedBitsValue(bit_value=10, bits=32)
    assert value.int == 10
    assert repr(value) == "Fixed32Value(int:10, float:1.401298464324817e-44)"

    value = FixedBitsValue(bit_value=4294967146, bits=32)
    assert value.int == -150
    assert value.signed_int == -150
    assert value.unsigned_int == 4294967146
    assert repr(value) == "Fixed32Value(unsigned_int:4294967146, signed_int: -150, float:nan)"

    value = FixedBitsValue(bit_value=4671105825815658496, bits=64)
    assert type(value.value) == float
    assert value.value == 19560.0
    assert repr(value) == "Fixed64Value(int:4671105825815658496, double:19560.0)"


def test_fixed32_value():
    """
        # proto
        message Test1 {
          repeated fixed32 a = 1;
        }

        # message
        {
          "a": 150
        }

        # binary
        0D 96 00 00 00

        """
    test_target = "0D 96 00 00 00"
    parsed_data = Parser().parse(test_target)
    assert isinstance(parsed_data[0].data, FixedBitsValue)
    assert parsed_data[0].wire_type == "fixed32"
    assert parsed_data[0].data.signed_int == 150

    assert isinstance(parsed_data[0].data.value, float)
    assert parsed_data[0].data.value == 2.1019476964872256e-43
    assert parsed_data.to_dict() == {'results': [{'field': 1, 'wire_type': 'fixed32',
                                                  'data': {'value': 2.1019476964872256e-43, 'signed_int': 150,
                                                           'value_type': 'float'}}]}


def test_fixed32_minus_value():
    """
        # proto
        message Test1 {
          repeated fixed32 a = 1;
        }

        # message
        {
          "a": -150
        }

        # binary
        0D 6A FF FF FF

        """
    test_target = "0D 6A FF FF FF"
    parsed_data = Parser().parse(test_target)
    assert isinstance(parsed_data[0].data, FixedBitsValue)
    assert parsed_data[0].wire_type == "fixed32"
    assert parsed_data[0].data.signed_int == -150

    assert isinstance(parsed_data[0].data.value, float)
    assert math.isnan(parsed_data[0].data.value)
    # 'nan' is not comparable, convert it to a string.
    assert str(parsed_data.to_dict()) == str({'results': [{'field': 1, 'wire_type': 'fixed32',
                                                           'data': {'value': float('nan'), 'signed_int': -150,
                                                                    'unsigned_int': 4294967146,
                                                                    'value_type': 'float'}}]})


def test_fixed64_value():
    """
        # proto
        message Test1 {
          repeated fixed64 a = 4;
        }

        # message
        {
          "a": 224301697723724
        }

        # binary
        21 4C ED 03 4F 00 CC 00 00

        """
    test_target = "21 4C ED 03 4F 00 CC 00 00"
    parsed_data = Parser().parse(test_target)
    assert isinstance(parsed_data[0].data, FixedBitsValue)
    assert parsed_data[0].wire_type == "fixed64"
    assert parsed_data[0].data.signed_int == 224301697723724
    assert parsed_data[0].data.value == 1.1081976314916e-309
    assert parsed_data.to_dict() == {'results': [{'field': 4, 'wire_type': 'fixed64',
                                                  'data': {'value': 1.1081976314916e-309, 'signed_int': 224301697723724,
                                                           'value_type': 'double'}}]}


def test_inner_protobuf_1():
    test_target = "08 C2 10 12 02 10 01"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=2114),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=2, wire_type='varint', data=1)]))])


def test_inner_protobuf_2():
    test_target = "0a892908be181283290801181238033809380d380f3813428f090804122208f1acb70210f80e1a0439493242220c325f335f35395f355f305f31280030c6c101122308e0b8bd02109d0f1a0432393439220d31305f335f35365f355f305f33280030b4b902122408eea2ba0210890f1a0432394858220e31365f31365f31345f355f305f3128003088ea01122308899fc20210ba0f1a04526f573e220e31365f31365f36325f355f305f31280030c639122408b7cad1021095101a0436393a46220e31345f31365f31325f345f305f3028003094fe011222089ca5b60210f20e1a0430367e41220c375f355f31335f355f305f30280030aef504122308b0a0c60210d10f1a0430314854220e31365f31365f31335f355f305f31280030e612122308c896c00210ae0f1a0439363641220e31365f31365f31395f365f305f302800308c2c122308fdfcbc02109a0f1a0452343644220d375f31365f31385f355f305f3228003096fe02122208cbcdbc0210980f1a0444663434220d345f31355f33345f325f305f30280030ec7c122108e2a3be0210a20f1a0459574e7e220c335f345f33385f355f305f30280030b20e122008bc87c20210b90f1a03384d43220c335f375f31365f345f305f31280030c62b122108d9c0d202109b101a0437354d4b220c345f395f31345f365f305f31280030a4761224089a8eb60210f10e1a04446e5434220e31335f31345f33375f355f305f32280030d4a52b122108b7f1bf0210ac0f1a0448454c4c220c31305f315f355f355f305f30280030966b122108d5f3c50210cf0f1a0439394659220c325f315f31365f355f305f30280030ce34122308cbdec60210d40f1a044f344242220d335f31305f35365f355f305f33280030beb101122208b9fab90210870f1a0421454421220c325f395f35375f355f305f30280030bcab01122208f5ebd0021091101a0436354143220c315f355f31345f345f305f31280030aae401122308d9dcb70210fa0e1a043134494e220d31315f365f34395f355f305f31280030d2e202122408ba97bb02108e0f1a0440573334220d31315f31365f315f315f305f33280030c2bd9704122108d4cfbd02109e0f1a0435304557220c365f31365f325f355f305f30280030c238122208b4fcc30210c40f1a044c38384d220d345f31365f35345f355f305f32280030ac36122308c6fec00210b30f1a0437314747220e31345f31325f36315f355f305f30280030c012122208a78cc30210bf0f1a0438334747220d31305f385f31345f355f305f31280030fe26122208f4fabd0210a00f1a0435324e4d220d31315f31365f355f375f305f30280030e80c1222089fa2bd02109c0f1a0423513438220d325f31305f35395f315f305f30280030840e122308a2aac10210b50f1a04417e4242220d375f31345f36305f335f305f32280030a0bd01122008b98ebd02109b0f1a043a343752220b345f335f345f365f305f30280030c038122308e3cfc00210b10f1a04477e4e4d220e31345f31305f35335f365f305f31280030dc12122408d7b7bc0210970f1a04524c3433220e31305f31305f36315f315f305f30280030a6af0112240893d8c10210b70f1a0437354443220e31305f31365f31325f355f305f32280030b2a60e42d308080112210896ff5c1087051a04572d5341220d31325f345f33385f355f305f3428003096131221089c853c10be031a044c583436220d31315f345f32345f355f305f33280030ce0212210888c31510af011a044d494d49220c375f315f33315f355f305f34280030cad4071220088ac25710e7041a0441363135220c345f31325f375f315f305f352800309e04121d08ebe15510de041a04694e534c2209355f31365f31325f342800309a0c122008e58f5d1088051a0456363438220c345f385f31335f375f305f332800309a15121f08b6b66610c5051a043d41583d220b375f375f375f355f305f34280030de06122108ecc41d10eb011a0365567e220e31305f31365f31335f355f305f33280030f028122008f4990b105d1a03393350220d31305f375f32375f355f305f35280030b0fa011220089ed3331089031a044c4e3933220c375f315f32335f325f305f362800308c1012210887846d10f1051a044e453533220d31345f375f31335f325f305f322800308406122208dec74110e4031a0438344f46220e31355f31325f35355f355f305f34280030984a1221088ec72f10ed021a04424c4e21220d335f31365f33375f355f305f34280030b80c122108b1806810ce051a0431373138220d335f31345f32355f365f305f37280030de2e122108b9cf13109e011a0431313538220d31315f345f31325f355f305f38280030ca24121e08b0e209104f1a03533739220c335f385f32375f355f305f32280030e439122008dbe61f10fe011a047e54522d220c345f395f32375f355f305f33280030d228122208f3f13710a3031a0434313945220e31365f31365f31335f365f305f35280030d40912210896812610ad021a0445334f31220d31345f335f31355f355f305f35280030b608121f0896d52f10ed021a037e4f47220c345f335f31345f355f305f34280030f811122208a9b70410221a04504c413e220e31365f31365f31395f355f305f36280030f4ea05122008a0c92f10ed021a034a5354220c375f315f33385f355f315f34280030e0c626122008b5e947108d041a03454c4b220d31305f315f34305f355f305f33280030e205122008aff30c105d1a03393354220d31365f31345f315f375f305f352800309cd610122008dbe560109f051a03373144220d335f31305f32335f355f305f352800308815122108eac42610b2021a045065404b220d31315f315f31345f315f305f33280030920a122208ab812810bc021a0431364f54220e31365f31355f31335f355f305f37280030c03b122208a3b60410221a044f6e6556220d31345f365f36375f365f325f36280030f2d1f50312210889fd73109d061a0453373937220d335f31365f35345f345f305f32280030da041220088fa10b105d1a0339334c220e31305f31325f31385f365f305f35280030a051122208ee841710bc011a0431313838220d325f31365f36305f355f305f3428003094a00112210897934010d9031a03525946220e31315f31325f36345f365f305f35280030f60242f8080802122208b3dcc60110f4091a0453563638220d375f31355f36305f355f305f34280030c444122008aea37910be061a03543330220c355f395f34395f355f305f342800309a9f2c122208febdb30110fd081a0457413439220d31355f335f35345f375f305f35280030ca1a122208bad5a101109a081a043530434e220d375f31365f33385f355f305f32280030fc0b1223088da1900110b5071a043e434841220e31305f31365f33345f355f305f312800308453122108adde9a0110f2071a04565f3130220c355f315f32385f315f305f33280030f20c122108fbea810110eb061a04572f3735220c345f335f31385f355f305f33280030a27d122408f89c8b011099071a04434e3231220e31365f31365f31335f365f305f3528003092a603122108f9fb7e10de061a043632444a220c31335f345f375f345f305f3328003092b70112210884da950110d5071a044c423831220c345f395f33375f365f305f35280030d20c122208839a7c10ce061a0457494221220d31365f315f31325f355f305f34280030a2d11f122208cd9dd10110b40a1a04534a3332220d375f31365f31365f315f305f31280030d20c122208e7d59d011082081a04504b3236220d335f31365f31345f365f305f33280030e410122108a4ebd90110e10a1a04416f3737220c335f385f33385f355f305f32280030925a122208b0ef980110e8071a045244324b220d345f31355f32365f365f305f32280030da1f122308f4f4a30110a5081a0436314247220e31315f31355f31335f365f305f34280030e206122108d7bea50110b0081a0427444d27220c315f31365f355f345f305f33280030ac04122208e6e8b10110f3081a0444513339220d31365f315f31385f355f305f33280030a24a1222089acdaa0110ca081a0431656538220c325f31345f365f355f305f342800309ea602122108d586d90110dd0a1a037e3547220d345f31365f35345f355f305f332800308005122008c2b7a0011092081a0478424f54220b325f315f355f355f305f32280030f20c122208f2c28d0110a9071a04537e3337220d325f31365f31325f375f305f34280030d22e122408abebd90110e10a1a0447563737220e31365f31325f32375f355f315f33280030d8d507122308c5a0950110d3071a0453214e37220e31365f31355f31325f355f305f32280030ea3512220887d3db0110ea0a1a0443504c57220d31365f315f36335f345f305f342800308212121c08a88c8f0110b1071a034e4a522208345f31365f315f35280030e62d122208d4fec20110dc091a044b323434220c375f31365f395f355f305f33280030ec8702122208bbd9c00110ce091a04506e582d220d315f31365f31325f355f305f32280030e803122108d3e2830110f5061a043838354e220c345f31305f355f355f305f35280030f431122408e5c7910110c0071a0436304754220d315f31365f31345f365f335f3828003090dba304122208c5b7910110c0071a0436304d78220c31355f355f325f355f305f38280030b88901122108afec810110eb061a04492f3735220c345f395f32395f355f305f32280030ba5542fe080803122208b1afb20210dc0e1a0446383444220c345f31365f355f375f305f30280030f8a909122108f1a2a90210a30e1a0453463a47220c325f385f31325f355f305f31280030f209122208bebcfd0110a50c1a0437334347220d315f31325f34395f355f305f32280030c009122108d3a2a30210810e1a044e654f31220c345f315f32375f365f305f31280030d80c122208c6df8d02108f0d1a0437394c42220d31325f31365f335f335f305f31280030ce041222088b90e40110950b1a0453325321220c355f365f31385f355f305f31280030deb202122108c4bcfd0110a60c1a0437347e46220c355f375f35335f355f305f3228003098111221089cb7950210b50d1a0445373137220c375f31355f355f365f305f31280030ba06122108d9f3ed0110cc0b1a0438344e4c220c345f315f35345f365f305f32280030a24a122208fed4ee0110d10b1a03343839220d31365f325f33365f315f305f3028003098d412122308b8deee0110d10b1a0438395643220d31305f315f36315f365f305f32280030c4e90a122108f5c8880210f20c1a0453503530220c31365f365f375f355f305f30280030d40b122208bee0850210e20c1a044e363334220d315f31325f31325f365f305f33280030960d122308d391f90110890c1a04494d3435220e31305f31365f32365f315f305f33280030a4161221088eb4990210c90d1a0433374849220c335f355f31325f345f305f31280030cc03122008f586830210ce0c1a0344564c220c345f31365f355f355f305f32280030aa5d122408cacfb30210e30e1a0444393152220e31365f31365f31345f355f305f31280030c89a01122108e2ccfe0110ad0c1a0446614d65220c345f335f31385f365f305f32280030cc15122308e9d0ee0110d10b1a0438394e52220e31365f31325f31395f355f305f31280030b664122208ed87840210d80c1a04565f3234220d345f31325f35345f355f305f31280030e003122208db81f10110de0b1a0430325641220d345f31325f31315f325f305f302800309839122108cafcec0110c70b1a0437392d41220c345f395f33335f345f305f30280030c855122208b0a5b00210d00e1a0457383732220d325f31325f32345f335f305f342800308428122308d6cdee0110d10b1a0438394347220c365f385f31325f365f315f342800309a8fb002122208cff1810210c50c1a03537e57220d31365f365f32345f355f305f312800309cea09122308caab930210ab0d1a04416e654c220e31305f31365f31345f365f305f35280030c21a12220888b8860210e60c1a044f575226220d31345f355f32375f365f305f33280030d80b122208f3e5f70110810c1a0423484c44220d325f31355f33345f315f305f302800308805122108bb86830210ce0c1a0444564c32220c325f375f36315f355f305f31280030ba041223088ec9ee0110d00b1a0438385648220d31305f365f33385f355f305f34280030a0b204122108e2fd9c0210db0d1a0443353554220c375f355f33385f355f305f33280030b81b122308b6ade30110910b1a0446433a4b220d31315f355f33345f365f305f33280030c6d80b4880f0b7a686315a54080110e5c791011a0436304754220ce9bb91e4babae68aace6a3ba281e301e38c00740d6b2bfa513620d315f31365f31345f365f335f386a0de1b4b3e1b58020e4bbbbe591bd700f781e8001bad9bbb7158801025a5b080110fed4ee011a0334383922133839234e203839434720383956432038394e52281e301e38d10b40ffbfc0ec09620d31365f325f33365f315f305f306a0e536b696c6c656420776f726b6572700e781e80018aebd28d148801035a5a08011093d8c1021a0437354443221244796e617374696320436f6e717565726f72281e301e38b70f408aa5fdcf0b620e31305f31365f31325f355f305f326a0c4c69616d2047696148c3a26e700f781e8001d48ab0fc1488010468018001048801019201ef010a44080110a0c92f1a034a535422074a555354494345281e301e38ed0240cc9da2820f620c375f315f33385f355f315f346a0553d0905645700f781e8001ca86c095158801010a50080010aff30c1a03393354220e5363756666656420546967657273281e301e385d40f7f7d4e50b620d31365f31345f315f375f305f356a0a53696c656e74666c6f77700f781e80018acaf6f51488010120002880f1e799aa313080cec39baa3140124821523d1000180020012a350a2468747470733a2f2f796f75747562652e636f6d2f6c6976652f465f476374464a6e695f6f10001a02656e2207796f7574756265587160019a010808011001180128049a0109080210a906180128049a0109080310910b180128049a0109080410f10e18002802a00102a80199eca304a801b5d8f126a8019cd1f728a80185c48d44a801e3feca0da801e3b98446a801bad88b0fa801f087e82ca8019e99c410a801d8d6d814a801c8efab0fa8018ed78b0fa801a8feca0d0a090801120508bc181001"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='length_delimited', data=ParsedResults(
        results=[ParsedResult(field=1, wire_type='varint', data=3134),
                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                     results=[ParsedResult(field=1, wire_type='varint', data=1),
                              ParsedResult(field=3, wire_type='varint', data=18),
                              ParsedResult(field=7, wire_type='varint', data=3),
                              ParsedResult(field=7, wire_type='varint', data=9),
                              ParsedResult(field=7, wire_type='varint', data=13),
                              ParsedResult(field=7, wire_type='varint', data=15),
                              ParsedResult(field=7, wire_type='varint', data=19),
                              ParsedResult(field=8, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=4),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5101169),
                                                        ParsedResult(field=2, wire_type='varint', data=1912),
                                                        ParsedResult(field=3, wire_type='string', data='9I2B'),
                                                        ParsedResult(field=4, wire_type='string', data='2_3_59_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=24774)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5200992),
                                                        ParsedResult(field=2, wire_type='varint', data=1949),
                                                        ParsedResult(field=3, wire_type='string', data='2949'),
                                                        ParsedResult(field=4, wire_type='string', data='10_3_56_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=40116)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5149038),
                                                        ParsedResult(field=2, wire_type='varint', data=1929),
                                                        ParsedResult(field=3, wire_type='string', data='29HX'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_14_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=29960)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5279625),
                                                        ParsedResult(field=2, wire_type='varint', data=1978),
                                                        ParsedResult(field=3, wire_type='string', data='RoW>'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_62_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=7366)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5530935),
                                                        ParsedResult(field=2, wire_type='varint', data=2069),
                                                        ParsedResult(field=3, wire_type='string', data='69:F'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='14_16_12_4_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=32532)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5083804),
                                                        ParsedResult(field=2, wire_type='varint', data=1906),
                                                        ParsedResult(field=3, wire_type='string', data='06~A'),
                                                        ParsedResult(field=4, wire_type='string', data='7_5_13_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=80558)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5345328),
                                                        ParsedResult(field=2, wire_type='varint', data=2001),
                                                        ParsedResult(field=3, wire_type='string', data='01HT'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_13_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2406)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5245768),
                                                        ParsedResult(field=2, wire_type='varint', data=1966),
                                                        ParsedResult(field=3, wire_type='string', data='966A'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_19_6_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5644)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5193341),
                                                        ParsedResult(field=2, wire_type='varint', data=1946),
                                                        ParsedResult(field=3, wire_type='string', data='R46D'),
                                                        ParsedResult(field=4, wire_type='string', data='7_16_18_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=48918)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5187275),
                                                        ParsedResult(field=2, wire_type='varint', data=1944),
                                                        ParsedResult(field=3, wire_type='string', data='Df44'),
                                                        ParsedResult(field=4, wire_type='string', data='4_15_34_2_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=15980)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5214690),
                                                        ParsedResult(field=2, wire_type='varint', data=1954),
                                                        ParsedResult(field=3, wire_type='string', data='YWN~'),
                                                        ParsedResult(field=4, wire_type='string', data='3_4_38_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1842)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5276604),
                                                        ParsedResult(field=2, wire_type='varint', data=1977),
                                                        ParsedResult(field=3, wire_type='string', data='8MC'),
                                                        ParsedResult(field=4, wire_type='string', data='3_7_16_4_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5574)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5546073),
                                                        ParsedResult(field=2, wire_type='varint', data=2075),
                                                        ParsedResult(field=3, wire_type='string', data='75MK'),
                                                        ParsedResult(field=4, wire_type='string', data='4_9_14_6_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=15140)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5080858),
                                                        ParsedResult(field=2, wire_type='varint', data=1905),
                                                        ParsedResult(field=3, wire_type='string', data='DnT4'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='13_14_37_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=709332)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5241015),
                                                        ParsedResult(field=2, wire_type='varint', data=1964),
                                                        ParsedResult(field=3, wire_type='string', data='HELL'),
                                                        ParsedResult(field=4, wire_type='string', data='10_1_5_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=13718)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5339605),
                                                        ParsedResult(field=2, wire_type='varint', data=1999),
                                                        ParsedResult(field=3, wire_type='string', data='99FY'),
                                                        ParsedResult(field=4, wire_type='string', data='2_1_16_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=6734)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5353291),
                                                        ParsedResult(field=2, wire_type='varint', data=2004),
                                                        ParsedResult(field=3, wire_type='string', data='O4BB'),
                                                        ParsedResult(field=4, wire_type='string', data='3_10_56_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=22718)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5143865),
                                                        ParsedResult(field=2, wire_type='varint', data=1927),
                                                        ParsedResult(field=3, wire_type='string', data='!ED!'),
                                                        ParsedResult(field=4, wire_type='string', data='2_9_57_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=21948)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5518837),
                                                        ParsedResult(field=2, wire_type='varint', data=2065),
                                                        ParsedResult(field=3, wire_type='string', data='65AC'),
                                                        ParsedResult(field=4, wire_type='string', data='1_5_14_4_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=29226)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5107289),
                                                        ParsedResult(field=2, wire_type='varint', data=1914),
                                                        ParsedResult(field=3, wire_type='string', data='14IN'),
                                                        ParsedResult(field=4, wire_type='string', data='11_6_49_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=45394)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5163962),
                                                        ParsedResult(field=2, wire_type='varint', data=1934),
                                                        ParsedResult(field=3, wire_type='string', data='@W34'),
                                                        ParsedResult(field=4, wire_type='string', data='11_16_1_1_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=8773314)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5203924),
                                                        ParsedResult(field=2, wire_type='varint', data=1950),
                                                        ParsedResult(field=3, wire_type='string', data='50EW'),
                                                        ParsedResult(field=4, wire_type='string', data='6_16_2_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=7234)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5307956),
                                                        ParsedResult(field=2, wire_type='varint', data=1988),
                                                        ParsedResult(field=3, wire_type='string', data='L88M'),
                                                        ParsedResult(field=4, wire_type='string', data='4_16_54_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=6956)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5259078),
                                                        ParsedResult(field=2, wire_type='varint', data=1971),
                                                        ParsedResult(field=3, wire_type='string', data='71GG'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='14_12_61_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2368)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5293607),
                                                        ParsedResult(field=2, wire_type='varint', data=1983),
                                                        ParsedResult(field=3, wire_type='string', data='83GG'),
                                                        ParsedResult(field=4, wire_type='string', data='10_8_14_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=4990)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5209460),
                                                        ParsedResult(field=2, wire_type='varint', data=1952),
                                                        ParsedResult(field=3, wire_type='string', data='52NM'),
                                                        ParsedResult(field=4, wire_type='string', data='11_16_5_7_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1640)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5198111),
                                                        ParsedResult(field=2, wire_type='varint', data=1948),
                                                        ParsedResult(field=3, wire_type='string', data='#Q48'),
                                                        ParsedResult(field=4, wire_type='string', data='2_10_59_1_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1796)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5264674),
                                                        ParsedResult(field=2, wire_type='varint', data=1973),
                                                        ParsedResult(field=3, wire_type='string', data='A~BB'),
                                                        ParsedResult(field=4, wire_type='string', data='7_14_60_3_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=24224)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5195577),
                                                        ParsedResult(field=2, wire_type='varint', data=1947),
                                                        ParsedResult(field=3, wire_type='string', data=':47R'),
                                                        ParsedResult(field=4, wire_type='string', data='4_3_4_6_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=7232)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5253091),
                                                        ParsedResult(field=2, wire_type='varint', data=1969),
                                                        ParsedResult(field=3, wire_type='string', data='G~NM'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='14_10_53_6_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2396)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5184471),
                                                        ParsedResult(field=2, wire_type='varint', data=1943),
                                                        ParsedResult(field=3, wire_type='string', data='RL43'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_10_61_1_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=22438)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5270547),
                                                        ParsedResult(field=2, wire_type='varint', data=1975),
                                                        ParsedResult(field=3, wire_type='string', data='75DC'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_16_12_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=234290)]))])),
                              ParsedResult(field=8, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=1),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1523606),
                                                        ParsedResult(field=2, wire_type='varint', data=647),
                                                        ParsedResult(field=3, wire_type='string', data='W-SA'),
                                                        ParsedResult(field=4, wire_type='string', data='12_4_38_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2454)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=983708),
                                                        ParsedResult(field=2, wire_type='varint', data=446),
                                                        ParsedResult(field=3, wire_type='string', data='LX46'),
                                                        ParsedResult(field=4, wire_type='string', data='11_4_24_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=334)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=352648),
                                                        ParsedResult(field=2, wire_type='varint', data=175),
                                                        ParsedResult(field=3, wire_type='string', data='MIMI'),
                                                        ParsedResult(field=4, wire_type='string', data='7_1_31_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=125514)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1433866),
                                                        ParsedResult(field=2, wire_type='varint', data=615),
                                                        ParsedResult(field=3, wire_type='string', data='A615'),
                                                        ParsedResult(field=4, wire_type='string', data='4_12_7_1_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=542)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1405163),
                                                        ParsedResult(field=2, wire_type='varint', data=606),
                                                        ParsedResult(field=3, wire_type='string', data='iNSL'),
                                                        ParsedResult(field=4, wire_type='string', data='5_16_12_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1562)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1525733),
                                                        ParsedResult(field=2, wire_type='varint', data=648),
                                                        ParsedResult(field=3, wire_type='string', data='V648'),
                                                        ParsedResult(field=4, wire_type='string', data='4_8_13_7_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2714)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1678134),
                                                        ParsedResult(field=2, wire_type='varint', data=709),
                                                        ParsedResult(field=3, wire_type='string', data='=AX='),
                                                        ParsedResult(field=4, wire_type='string', data='7_7_7_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=862)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=483948),
                                                        ParsedResult(field=2, wire_type='varint', data=235),
                                                        ParsedResult(field=3, wire_type='string', data='eV~'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_16_13_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5232)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=183540),
                                                        ParsedResult(field=2, wire_type='varint', data=93),
                                                        ParsedResult(field=3, wire_type='string', data='93P'),
                                                        ParsedResult(field=4, wire_type='string', data='10_7_27_5_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=32048)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=846238),
                                                        ParsedResult(field=2, wire_type='varint', data=393),
                                                        ParsedResult(field=3, wire_type='string', data='LN93'),
                                                        ParsedResult(field=4, wire_type='string', data='7_1_23_2_0_6'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2060)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1786375),
                                                        ParsedResult(field=2, wire_type='varint', data=753),
                                                        ParsedResult(field=3, wire_type='string', data='NE53'),
                                                        ParsedResult(field=4, wire_type='string', data='14_7_13_2_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=772)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1074142),
                                                        ParsedResult(field=2, wire_type='varint', data=484),
                                                        ParsedResult(field=3, wire_type='string', data='84OF'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='15_12_55_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=9496)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=779150),
                                                        ParsedResult(field=2, wire_type='varint', data=365),
                                                        ParsedResult(field=3, wire_type='string', data='BLN!'),
                                                        ParsedResult(field=4, wire_type='string', data='3_16_37_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1592)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1703985),
                                                        ParsedResult(field=2, wire_type='varint', data=718),
                                                        ParsedResult(field=3, wire_type='string', data='1718'),
                                                        ParsedResult(field=4, wire_type='string', data='3_14_25_6_0_7'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5982)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=321465),
                                                        ParsedResult(field=2, wire_type='varint', data=158),
                                                        ParsedResult(field=3, wire_type='string', data='1158'),
                                                        ParsedResult(field=4, wire_type='string', data='11_4_12_5_0_8'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=4682)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=160048),
                                                        ParsedResult(field=2, wire_type='varint', data=79),
                                                        ParsedResult(field=3, wire_type='string', data='S79'),
                                                        ParsedResult(field=4, wire_type='string', data='3_8_27_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=7396)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=521051),
                                                        ParsedResult(field=2, wire_type='varint', data=254),
                                                        ParsedResult(field=3, wire_type='string', data='~TR-'),
                                                        ParsedResult(field=4, wire_type='string', data='4_9_27_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5202)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=915699),
                                                        ParsedResult(field=2, wire_type='varint', data=419),
                                                        ParsedResult(field=3, wire_type='string', data='419E'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_13_6_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1236)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=622742),
                                                        ParsedResult(field=2, wire_type='varint', data=301),
                                                        ParsedResult(field=3, wire_type='string', data='E3O1'),
                                                        ParsedResult(field=4, wire_type='string', data='14_3_15_5_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1078)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=780950),
                                                        ParsedResult(field=2, wire_type='varint', data=365),
                                                        ParsedResult(field=3, wire_type='string', data='~OG'),
                                                        ParsedResult(field=4, wire_type='string', data='4_3_14_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2296)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=72617),
                                                        ParsedResult(field=2, wire_type='varint', data=34),
                                                        ParsedResult(field=3, wire_type='string', data='PLA>'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_19_5_0_6'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=95604)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=779424),
                                                        ParsedResult(field=2, wire_type='varint', data=365),
                                                        ParsedResult(field=3, wire_type='string', data='JST'),
                                                        ParsedResult(field=4, wire_type='string', data='7_1_38_5_1_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=631648)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1176757),
                                                        ParsedResult(field=2, wire_type='varint', data=525),
                                                        ParsedResult(field=3, wire_type='string', data='ELK'),
                                                        ParsedResult(field=4, wire_type='string', data='10_1_40_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=738)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=211375),
                                                        ParsedResult(field=2, wire_type='varint', data=93),
                                                        ParsedResult(field=3, wire_type='string', data='93T'),
                                                        ParsedResult(field=4, wire_type='string', data='16_14_1_7_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=273180)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1585883),
                                                        ParsedResult(field=2, wire_type='varint', data=671),
                                                        ParsedResult(field=3, wire_type='string', data='71D'),
                                                        ParsedResult(field=4, wire_type='string', data='3_10_23_5_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2696)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=631402),
                                                        ParsedResult(field=2, wire_type='varint', data=306),
                                                        ParsedResult(field=3, wire_type='string', data='Pe@K'),
                                                        ParsedResult(field=4, wire_type='string', data='11_1_14_1_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1298)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=655531),
                                                        ParsedResult(field=2, wire_type='varint', data=316),
                                                        ParsedResult(field=3, wire_type='string', data='16OT'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_15_13_5_0_7'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=7616)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=72483),
                                                        ParsedResult(field=2, wire_type='varint', data=34),
                                                        ParsedResult(field=3, wire_type='string', data='OneV'),
                                                        ParsedResult(field=4, wire_type='string', data='14_6_67_6_2_6'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=8218866)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1900169),
                                                        ParsedResult(field=2, wire_type='varint', data=797),
                                                        ParsedResult(field=3, wire_type='string', data='S797'),
                                                        ParsedResult(field=4, wire_type='string', data='3_16_54_4_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=602)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=184463),
                                                        ParsedResult(field=2, wire_type='varint', data=93),
                                                        ParsedResult(field=3, wire_type='string', data='93L'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_12_18_6_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=10400)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=377454),
                                                        ParsedResult(field=2, wire_type='varint', data=188),
                                                        ParsedResult(field=3, wire_type='string', data='1188'),
                                                        ParsedResult(field=4, wire_type='string', data='2_16_60_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=20500)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1051031),
                                                        ParsedResult(field=2, wire_type='varint', data=473),
                                                        ParsedResult(field=3, wire_type='string', data='RYF'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='11_12_64_6_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=374)]))])),
                              ParsedResult(field=8, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=2),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3255859),
                                                        ParsedResult(field=2, wire_type='varint', data=1268),
                                                        ParsedResult(field=3, wire_type='string', data='SV68'),
                                                        ParsedResult(field=4, wire_type='string', data='7_15_60_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=8772)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=1986990),
                                                        ParsedResult(field=2, wire_type='varint', data=830),
                                                        ParsedResult(field=3, wire_type='string', data='T30'),
                                                        ParsedResult(field=4, wire_type='string', data='5_9_49_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=724890)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2940670),
                                                        ParsedResult(field=2, wire_type='varint', data=1149),
                                                        ParsedResult(field=3, wire_type='string', data='WA49'),
                                                        ParsedResult(field=4, wire_type='string', data='15_3_54_7_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=3402)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2648762),
                                                        ParsedResult(field=2, wire_type='varint', data=1050),
                                                        ParsedResult(field=3, wire_type='string', data='50CN'),
                                                        ParsedResult(field=4, wire_type='string', data='7_16_38_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1532)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2363533),
                                                        ParsedResult(field=2, wire_type='varint', data=949),
                                                        ParsedResult(field=3, wire_type='string', data='>CHA'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_16_34_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=10628)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2535213),
                                                        ParsedResult(field=2, wire_type='varint', data=1010),
                                                        ParsedResult(field=3, wire_type='string', data='V_10'),
                                                        ParsedResult(field=4, wire_type='string', data='5_1_28_1_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1650)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2127227),
                                                        ParsedResult(field=2, wire_type='varint', data=875),
                                                        ParsedResult(field=3, wire_type='string', data='W/75'),
                                                        ParsedResult(field=4, wire_type='string', data='4_3_18_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=16034)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2281080),
                                                        ParsedResult(field=2, wire_type='varint', data=921),
                                                        ParsedResult(field=3, wire_type='string', data='CN21'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_13_6_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=54034)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2080249),
                                                        ParsedResult(field=2, wire_type='varint', data=862),
                                                        ParsedResult(field=3, wire_type='string', data='62DJ'),
                                                        ParsedResult(field=4, wire_type='string', data='13_4_7_4_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=23442)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2452740),
                                                        ParsedResult(field=2, wire_type='varint', data=981),
                                                        ParsedResult(field=3, wire_type='string', data='LB81'),
                                                        ParsedResult(field=4, wire_type='string', data='4_9_37_6_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1618)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2034947),
                                                        ParsedResult(field=2, wire_type='varint', data=846),
                                                        ParsedResult(field=3, wire_type='string', data='WIB!'),
                                                        ParsedResult(field=4, wire_type='string', data='16_1_12_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=518306)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3428045),
                                                        ParsedResult(field=2, wire_type='varint', data=1332),
                                                        ParsedResult(field=3, wire_type='string', data='SJ32'),
                                                        ParsedResult(field=4, wire_type='string', data='7_16_16_1_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1618)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2583271),
                                                        ParsedResult(field=2, wire_type='varint', data=1026),
                                                        ParsedResult(field=3, wire_type='string', data='PK26'),
                                                        ParsedResult(field=4, wire_type='string', data='3_16_14_6_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2148)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3569060),
                                                        ParsedResult(field=2, wire_type='varint', data=1377),
                                                        ParsedResult(field=3, wire_type='string', data='Ao77'),
                                                        ParsedResult(field=4, wire_type='string', data='3_8_38_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=11538)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2504624),
                                                        ParsedResult(field=2, wire_type='varint', data=1000),
                                                        ParsedResult(field=3, wire_type='string', data='RD2K'),
                                                        ParsedResult(field=4, wire_type='string', data='4_15_26_6_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=4058)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2685556),
                                                        ParsedResult(field=2, wire_type='varint', data=1061),
                                                        ParsedResult(field=3, wire_type='string', data='61BG'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='11_15_13_6_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=866)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2711383),
                                                        ParsedResult(field=2, wire_type='varint', data=1072),
                                                        ParsedResult(field=3, wire_type='string', data="'DM'"),
                                                        ParsedResult(field=4, wire_type='string', data='1_16_5_4_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=556)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2913382),
                                                        ParsedResult(field=2, wire_type='varint', data=1139),
                                                        ParsedResult(field=3, wire_type='string', data='DQ39'),
                                                        ParsedResult(field=4, wire_type='string', data='16_1_18_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=9506)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2795162),
                                                        ParsedResult(field=2, wire_type='varint', data=1098),
                                                        ParsedResult(field=3, wire_type='string', data='1ee8'),
                                                        ParsedResult(field=4, wire_type='string', data='2_14_6_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=37662)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3556181),
                                                        ParsedResult(field=2, wire_type='varint', data=1373),
                                                        ParsedResult(field=3, wire_type='string', data='~5G'),
                                                        ParsedResult(field=4, wire_type='string', data='4_16_54_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=640)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2628546),
                                                        ParsedResult(field=2, wire_type='varint', data=1042),
                                                        ParsedResult(field=3, wire_type='string', data='xBOT'),
                                                        ParsedResult(field=4, wire_type='string', data='2_1_5_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1650)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2318706),
                                                        ParsedResult(field=2, wire_type='varint', data=937),
                                                        ParsedResult(field=3, wire_type='string', data='S~37'),
                                                        ParsedResult(field=4, wire_type='string', data='2_16_12_7_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5970)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3569067),
                                                        ParsedResult(field=2, wire_type='varint', data=1377),
                                                        ParsedResult(field=3, wire_type='string', data='GV77'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_12_27_5_1_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=125656)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2445381),
                                                        ParsedResult(field=2, wire_type='varint', data=979),
                                                        ParsedResult(field=3, wire_type='string', data='S!N7'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_15_12_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=6890)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3598727),
                                                        ParsedResult(field=2, wire_type='varint', data=1386),
                                                        ParsedResult(field=3, wire_type='string', data='CPLW'),
                                                        ParsedResult(field=4, wire_type='string', data='16_1_63_4_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2306)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2344488),
                                                        ParsedResult(field=2, wire_type='varint', data=945),
                                                        ParsedResult(field=3, wire_type='string', data='NJR'),
                                                        ParsedResult(field=4, wire_type='string', data='4_16_1_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5862)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3194708),
                                                        ParsedResult(field=2, wire_type='varint', data=1244),
                                                        ParsedResult(field=3, wire_type='string', data='K244'),
                                                        ParsedResult(field=4, wire_type='string', data='7_16_9_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=33772)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3157179),
                                                        ParsedResult(field=2, wire_type='varint', data=1230),
                                                        ParsedResult(field=3, wire_type='string', data='PnX-'),
                                                        ParsedResult(field=4, wire_type='string', data='1_16_12_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=488)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2158931),
                                                        ParsedResult(field=2, wire_type='varint', data=885),
                                                        ParsedResult(field=3, wire_type='string', data='885N'),
                                                        ParsedResult(field=4, wire_type='string', data='4_10_5_5_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=6388)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2384869),
                                                        ParsedResult(field=2, wire_type='varint', data=960),
                                                        ParsedResult(field=3, wire_type='string', data='60GT'),
                                                        ParsedResult(field=4, wire_type='string', data='1_16_14_6_3_8'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=8973712)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2382789),
                                                        ParsedResult(field=2, wire_type='varint', data=960),
                                                        ParsedResult(field=3, wire_type='string', data='60Mx'),
                                                        ParsedResult(field=4, wire_type='string', data='15_5_2_5_0_8'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=17592)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=2127407),
                                                        ParsedResult(field=2, wire_type='varint', data=875),
                                                        ParsedResult(field=3, wire_type='string', data='I/75'),
                                                        ParsedResult(field=4, wire_type='string', data='4_9_29_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=10938)]))])),
                              ParsedResult(field=8, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=3),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5019569),
                                                        ParsedResult(field=2, wire_type='varint', data=1884),
                                                        ParsedResult(field=3, wire_type='string', data='F84D'),
                                                        ParsedResult(field=4, wire_type='string', data='4_16_5_7_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=152824)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4870513),
                                                        ParsedResult(field=2, wire_type='varint', data=1827),
                                                        ParsedResult(field=3, wire_type='string', data='SF:G'),
                                                        ParsedResult(field=4, wire_type='string', data='2_8_12_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1266)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4152894),
                                                        ParsedResult(field=2, wire_type='varint', data=1573),
                                                        ParsedResult(field=3, wire_type='string', data='73CG'),
                                                        ParsedResult(field=4, wire_type='string', data='1_12_49_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1216)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4772179),
                                                        ParsedResult(field=2, wire_type='varint', data=1793),
                                                        ParsedResult(field=3, wire_type='string', data='NeO1'),
                                                        ParsedResult(field=4, wire_type='string', data='4_1_27_6_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1624)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4419526),
                                                        ParsedResult(field=2, wire_type='varint', data=1679),
                                                        ParsedResult(field=3, wire_type='string', data='79LB'),
                                                        ParsedResult(field=4, wire_type='string', data='12_16_3_3_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=590)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3737611),
                                                        ParsedResult(field=2, wire_type='varint', data=1429),
                                                        ParsedResult(field=3, wire_type='string', data='S2S!'),
                                                        ParsedResult(field=4, wire_type='string', data='5_6_18_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=39262)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4152900),
                                                        ParsedResult(field=2, wire_type='varint', data=1574),
                                                        ParsedResult(field=3, wire_type='string', data='74~F'),
                                                        ParsedResult(field=4, wire_type='string', data='5_7_53_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2200)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4545436),
                                                        ParsedResult(field=2, wire_type='varint', data=1717),
                                                        ParsedResult(field=3, wire_type='string', data='E717'),
                                                        ParsedResult(field=4, wire_type='string', data='7_15_5_6_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=826)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3897817),
                                                        ParsedResult(field=2, wire_type='varint', data=1484),
                                                        ParsedResult(field=3, wire_type='string', data='84NL'),
                                                        ParsedResult(field=4, wire_type='string', data='4_1_54_6_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=9506)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3910270),
                                                        ParsedResult(field=2, wire_type='varint', data=1489),
                                                        ParsedResult(field=3, wire_type='string', data='489'),
                                                        ParsedResult(field=4, wire_type='string', data='16_2_36_1_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=305688)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3911480),
                                                        ParsedResult(field=2, wire_type='varint', data=1489),
                                                        ParsedResult(field=3, wire_type='string', data='89VC'),
                                                        ParsedResult(field=4, wire_type='string', data='10_1_61_6_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=177348)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4334709),
                                                        ParsedResult(field=2, wire_type='varint', data=1650),
                                                        ParsedResult(field=3, wire_type='string', data='SP50'),
                                                        ParsedResult(field=4, wire_type='string', data='16_6_7_5_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1492)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4288574),
                                                        ParsedResult(field=2, wire_type='varint', data=1634),
                                                        ParsedResult(field=3, wire_type='string', data='N634'),
                                                        ParsedResult(field=4, wire_type='string', data='1_12_12_6_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1686)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4081875),
                                                        ParsedResult(field=2, wire_type='varint', data=1545),
                                                        ParsedResult(field=3, wire_type='string', data='IM45'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_16_26_1_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2852)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4610574),
                                                        ParsedResult(field=2, wire_type='varint', data=1737),
                                                        ParsedResult(field=3, wire_type='string', data='37HI'),
                                                        ParsedResult(field=4, wire_type='string', data='3_5_12_4_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=460)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4244341),
                                                        ParsedResult(field=2, wire_type='varint', data=1614),
                                                        ParsedResult(field=3, wire_type='string', data='DVL'),
                                                        ParsedResult(field=4, wire_type='string', data='4_16_5_5_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=11946)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=5040074),
                                                        ParsedResult(field=2, wire_type='varint', data=1891),
                                                        ParsedResult(field=3, wire_type='string', data='D91R'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_16_14_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=19784)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4171362),
                                                        ParsedResult(field=2, wire_type='varint', data=1581),
                                                        ParsedResult(field=3, wire_type='string', data='FaMe'),
                                                        ParsedResult(field=4, wire_type='string', data='4_3_18_6_0_2'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=2764)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3909737),
                                                        ParsedResult(field=2, wire_type='varint', data=1489),
                                                        ParsedResult(field=3, wire_type='string', data='89NR'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='16_12_19_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=12854)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4260845),
                                                        ParsedResult(field=2, wire_type='varint', data=1624),
                                                        ParsedResult(field=3, wire_type='string', data='V_24'),
                                                        ParsedResult(field=4, wire_type='string', data='4_12_54_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=480)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3948763),
                                                        ParsedResult(field=2, wire_type='varint', data=1502),
                                                        ParsedResult(field=3, wire_type='string', data='02VA'),
                                                        ParsedResult(field=4, wire_type='string', data='4_12_11_2_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=7320)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3882570),
                                                        ParsedResult(field=2, wire_type='varint', data=1479),
                                                        ParsedResult(field=3, wire_type='string', data='79-A'),
                                                        ParsedResult(field=4, wire_type='string', data='4_9_33_4_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=10952)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4985520),
                                                        ParsedResult(field=2, wire_type='varint', data=1872),
                                                        ParsedResult(field=3, wire_type='string', data='W872'),
                                                        ParsedResult(field=4, wire_type='string', data='2_12_24_3_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=5124)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3909334),
                                                        ParsedResult(field=2, wire_type='varint', data=1489),
                                                        ParsedResult(field=3, wire_type='string', data='89CG'),
                                                        ParsedResult(field=4, wire_type='string', data='6_8_12_6_1_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=4982682)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4225231),
                                                        ParsedResult(field=2, wire_type='varint', data=1605),
                                                        ParsedResult(field=3, wire_type='string', data='S~W'),
                                                        ParsedResult(field=4, wire_type='string', data='16_6_24_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=161052)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4511178),
                                                        ParsedResult(field=2, wire_type='varint', data=1707),
                                                        ParsedResult(field=3, wire_type='string', data='AneL'),
                                                        ParsedResult(field=4, wire_type='string',
                                                                     data='10_16_14_6_0_5'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=3394)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4299784),
                                                        ParsedResult(field=2, wire_type='varint', data=1638),
                                                        ParsedResult(field=3, wire_type='string', data='OWR&'),
                                                        ParsedResult(field=4, wire_type='string', data='14_5_27_6_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=1496)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4059891),
                                                        ParsedResult(field=2, wire_type='varint', data=1537),
                                                        ParsedResult(field=3, wire_type='string', data='#HLD'),
                                                        ParsedResult(field=4, wire_type='string', data='2_15_34_1_0_0'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=648)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4244283),
                                                        ParsedResult(field=2, wire_type='varint', data=1614),
                                                        ParsedResult(field=3, wire_type='string', data='DVL2'),
                                                        ParsedResult(field=4, wire_type='string', data='2_7_61_5_0_1'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=570)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3908750),
                                                        ParsedResult(field=2, wire_type='varint', data=1488),
                                                        ParsedResult(field=3, wire_type='string', data='88VH'),
                                                        ParsedResult(field=4, wire_type='string', data='10_6_38_5_0_4'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=71968)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=4669154),
                                                        ParsedResult(field=2, wire_type='varint', data=1755),
                                                        ParsedResult(field=3, wire_type='string', data='C55T'),
                                                        ParsedResult(field=4, wire_type='string', data='7_5_38_5_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=3512)])),
                                           ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                               results=[ParsedResult(field=1, wire_type='varint', data=3724982),
                                                        ParsedResult(field=2, wire_type='varint', data=1425),
                                                        ParsedResult(field=3, wire_type='string', data='FC:K'),
                                                        ParsedResult(field=4, wire_type='string', data='11_5_34_6_0_3'),
                                                        ParsedResult(field=5, wire_type='varint', data=0),
                                                        ParsedResult(field=6, wire_type='varint', data=191558)]))])),
                              ParsedResult(field=9, wire_type='varint', data=1685318400000),
                              ParsedResult(field=11, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=1),
                                           ParsedResult(field=2, wire_type='varint', data=2384869),
                                           ParsedResult(field=3, wire_type='string', data='60GT'),
                                           ParsedResult(field=4, wire_type='string', data='黑人抬棺'),
                                           ParsedResult(field=5, wire_type='varint', data=30),
                                           ParsedResult(field=6, wire_type='varint', data=30),
                                           ParsedResult(field=7, wire_type='varint', data=960),
                                           ParsedResult(field=8, wire_type='varint', data=5178906966),
                                           ParsedResult(field=12, wire_type='string', data='1_16_14_6_3_8'),
                                           ParsedResult(field=13, wire_type='string', data='ᴳᵀ 任命'),
                                           ParsedResult(field=14, wire_type='varint', data=15),
                                           ParsedResult(field=15, wire_type='varint', data=30),
                                           ParsedResult(field=16, wire_type='varint', data=5753466042),
                                           ParsedResult(field=17, wire_type='varint', data=2)])),
                              ParsedResult(field=11, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=1),
                                           ParsedResult(field=2, wire_type='varint', data=3910270),
                                           ParsedResult(field=3, wire_type='string', data='489'),
                                           ParsedResult(field=4, wire_type='string', data='89#N 89CG 89VC 89NR'),
                                           ParsedResult(field=5, wire_type='varint', data=30),
                                           ParsedResult(field=6, wire_type='varint', data=30),
                                           ParsedResult(field=7, wire_type='varint', data=1489),
                                           ParsedResult(field=8, wire_type='varint', data=2643468287),
                                           ParsedResult(field=12, wire_type='string', data='16_2_36_1_0_0'),
                                           ParsedResult(field=13, wire_type='string', data='Skilled worker'),
                                           ParsedResult(field=14, wire_type='varint', data=14),
                                           ParsedResult(field=15, wire_type='varint', data=30),
                                           ParsedResult(field=16, wire_type='varint', data=5397329290),
                                           ParsedResult(field=17, wire_type='varint', data=3)])),
                              ParsedResult(field=11, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=1),
                                           ParsedResult(field=2, wire_type='varint', data=5270547),
                                           ParsedResult(field=3, wire_type='string', data='75DC'),
                                           ParsedResult(field=4, wire_type='string', data='Dynastic Conqueror'),
                                           ParsedResult(field=5, wire_type='varint', data=30),
                                           ParsedResult(field=6, wire_type='varint', data=30),
                                           ParsedResult(field=7, wire_type='varint', data=1975),
                                           ParsedResult(field=8, wire_type='varint', data=3120517770),
                                           ParsedResult(field=12, wire_type='string', data='10_16_12_5_0_2'),
                                           ParsedResult(field=13, wire_type='string', data='Liam GiaHân'),
                                           ParsedResult(field=14, wire_type='varint', data=15),
                                           ParsedResult(field=15, wire_type='varint', data=30),
                                           ParsedResult(field=16, wire_type='varint', data=5629543764),
                                           ParsedResult(field=17, wire_type='varint', data=4)])),
                              ParsedResult(field=13, wire_type='varint', data=1),
                              ParsedResult(field=16, wire_type='varint', data=4),
                              ParsedResult(field=17, wire_type='varint', data=1),
                              ParsedResult(field=18, wire_type='length_delimited', data=ParsedResults(results=[
                                  ParsedResult(field=1, wire_type='length_delimited', data=ParsedResults(
                                      results=[ParsedResult(field=1, wire_type='varint', data=1),
                                               ParsedResult(field=2, wire_type='varint', data=779424),
                                               ParsedResult(field=3, wire_type='string', data='JST'),
                                               ParsedResult(field=4, wire_type='string', data='JUSTICE'),
                                               ParsedResult(field=5, wire_type='varint', data=30),
                                               ParsedResult(field=6, wire_type='varint', data=30),
                                               ParsedResult(field=7, wire_type='varint', data=365),
                                               ParsedResult(field=8, wire_type='varint', data=4031286988),
                                               ParsedResult(field=12, wire_type='string', data='7_1_38_5_1_4'),
                                               ParsedResult(field=13, wire_type='string', data='SАVE'),
                                               ParsedResult(field=14, wire_type='varint', data=15),
                                               ParsedResult(field=15, wire_type='varint', data=30),
                                               ParsedResult(field=16, wire_type='varint', data=5682234186),
                                               ParsedResult(field=17, wire_type='varint', data=1)])),
                                  ParsedResult(field=1, wire_type='length_delimited', data=ParsedResults(
                                      results=[ParsedResult(field=1, wire_type='varint', data=0),
                                               ParsedResult(field=2, wire_type='varint', data=211375),
                                               ParsedResult(field=3, wire_type='string', data='93T'),
                                               ParsedResult(field=4, wire_type='string', data='Scuffed Tigers'),
                                               ParsedResult(field=5, wire_type='varint', data=30),
                                               ParsedResult(field=6, wire_type='varint', data=30),
                                               ParsedResult(field=7, wire_type='varint', data=93),
                                               ParsedResult(field=8, wire_type='varint', data=3165993975),
                                               ParsedResult(field=12, wire_type='string', data='16_14_1_7_0_5'),
                                               ParsedResult(field=13, wire_type='string', data='Silentflow'),
                                               ParsedResult(field=14, wire_type='varint', data=15),
                                               ParsedResult(field=15, wire_type='varint', data=30),
                                               ParsedResult(field=16, wire_type='varint', data=5616018698),
                                               ParsedResult(field=17, wire_type='varint', data=1)])),
                                  ParsedResult(field=4, wire_type='varint', data=0),
                                  ParsedResult(field=5, wire_type='varint', data=1694955600000),
                                  ParsedResult(field=6, wire_type='varint', data=1694959200000),
                                  ParsedResult(field=8, wire_type='varint', data=18),
                                  ParsedResult(field=9, wire_type='varint', data=33),
                                  ParsedResult(field=10, wire_type='length_delimited', data=ParsedResults(
                                      results=[ParsedResult(field=2, wire_type='varint', data=0),
                                               ParsedResult(field=3, wire_type='varint', data=0),
                                               ParsedResult(field=4, wire_type='varint', data=1),
                                               ParsedResult(field=5, wire_type='length_delimited', data=ParsedResults(
                                                   results=[ParsedResult(field=1, wire_type='string',
                                                                         data='https://youtube.com/live/F_GctFJni_o'),
                                                            ParsedResult(field=2, wire_type='varint', data=0),
                                                            ParsedResult(field=3, wire_type='string', data='en'),
                                                            ParsedResult(field=4, wire_type='string',
                                                                         data='youtube')]))])),
                                  ParsedResult(field=11, wire_type='varint', data=113),
                                  ParsedResult(field=12, wire_type='varint', data=1)])),
                              ParsedResult(field=19, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=1),
                                           ParsedResult(field=2, wire_type='varint', data=1),
                                           ParsedResult(field=3, wire_type='varint', data=1),
                                           ParsedResult(field=5, wire_type='varint', data=4)])),
                              ParsedResult(field=19, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=2),
                                           ParsedResult(field=2, wire_type='varint', data=809),
                                           ParsedResult(field=3, wire_type='varint', data=1),
                                           ParsedResult(field=5, wire_type='varint', data=4)])),
                              ParsedResult(field=19, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=3),
                                           ParsedResult(field=2, wire_type='varint', data=1425),
                                           ParsedResult(field=3, wire_type='varint', data=1),
                                           ParsedResult(field=5, wire_type='varint', data=4)])),
                              ParsedResult(field=19, wire_type='length_delimited', data=ParsedResults(
                                  results=[ParsedResult(field=1, wire_type='varint', data=4),
                                           ParsedResult(field=2, wire_type='varint', data=1905),
                                           ParsedResult(field=3, wire_type='varint', data=0),
                                           ParsedResult(field=5, wire_type='varint', data=2)])),
                              ParsedResult(field=20, wire_type='varint', data=2),
                              ParsedResult(field=21, wire_type='varint', data=8975897),
                              ParsedResult(field=21, wire_type='varint', data=81554485),
                              ParsedResult(field=21, wire_type='varint', data=85846172),
                              ParsedResult(field=21, wire_type='varint', data=142828037),
                              ParsedResult(field=21, wire_type='varint', data=28491619),
                              ParsedResult(field=21, wire_type='varint', data=146873571),
                              ParsedResult(field=21, wire_type='varint', data=31648826),
                              ParsedResult(field=21, wire_type='varint', data=93979632),
                              ParsedResult(field=21, wire_type='varint', data=34671774),
                              ParsedResult(field=21, wire_type='varint', data=43395928),
                              ParsedResult(field=21, wire_type='varint', data=32176072),
                              ParsedResult(field=21, wire_type='varint', data=31648654),
                              ParsedResult(field=21, wire_type='varint', data=28491560)]))])),
                                                 ParsedResult(field=1, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=1, wire_type='varint', data=1),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=3132),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1)]))]))])


def test_inner_protobuf_3():
    test_target = "08f03e12d2020a04100008010a04100108020a04100008030a04100108040a04100108050a04100008060a04100108070a04100108080a04100008090a041000080a0a041000080b0a041000080c0a041001080d0a041003080e0a041003080f0a04100008100a04100008110a04100108120a04100108130a04100008140a04100108150a04100008160a04100108170a04100108180a04100108190a041001081a0a041001081b0a041001081c0a041001081d0a041001081e0a041000081f0a04100108200a04100108210a04100108220a04100108230a04100008240a04100108250a04100008260a04100108270a04100108280a04100108290a041000082a0a041000082b0a041000082d0a041000082e0a041000082f0a04100008300a04100008310a04100008320a04100008330a04100008340a04100108350a04100008360a04100008370a04100008380a04100108391001"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=8048),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=1)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=2)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=3)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=4)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=5)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=6)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=7)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=8)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=9)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=10)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=11)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=12)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=13)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=3),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=14)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=3),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=15)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=16)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=17)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=18)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=19)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=20)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=21)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=22)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=23)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=24)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=25)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=26)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=27)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=28)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=29)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=30)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=31)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=32)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=33)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=34)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=35)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=36)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=37)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=38)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=39)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=40)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=41)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=42)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=43)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=45)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=46)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=47)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=48)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=49)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=50)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=51)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=52)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=53)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=54)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=55)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=56)])),
                                                              ParsedResult(field=1, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=57)])),
                                                              ParsedResult(field=2, wire_type='varint', data=1)]))])


def test_inner_protobuf_4():
    test_target = "089404120b180012000a056576656e74"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=532),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=3, wire_type='varint', data=0),
                                                              ParsedResult(field=2, wire_type='string', data=''),
                                                              ParsedResult(field=1, wire_type='string',
                                                                           data='event')]))])


def test_inner_protobuf_5():
    test_target = "08df3d121810010a143234353136373434313639343634323838333130"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=7903),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=2, wire_type='varint', data=1),
                                                              ParsedResult(field=1, wire_type='string',
                                                                           data='24516744169464288310')]))])


def test_inner_protobuf_6():
    test_target = "08ea3d121818010a143234353136373432313639343634323838333130"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=7914),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=3, wire_type='varint', data=1),
                                                              ParsedResult(field=1, wire_type='string',
                                                                           data='24516742169464288310')]))])


def test_inner_protobuf_7():
    test_target = "089247123012040801103d12040803103512040806101012040808100612040804102112040802104712040805102f120408651000"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=9106),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=1),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=61)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=3),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=53)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=6),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=16)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=8),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=6)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=4),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=33)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=2),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=71)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=5),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=47)])),
                                                              ParsedResult(field=2, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=101),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=0)]))]))])


def test_inner_protobuf_8():
    test_target = "08 8C 23 12 08 42 04 08 04 10 01 60 00"
    parsed_data = Parser().parse(test_target)
    assert parsed_data == ParsedResults(results=[ParsedResult(field=1, wire_type='varint', data=4492),
                                                 ParsedResult(field=2, wire_type='length_delimited', data=ParsedResults(
                                                     results=[ParsedResult(field=8, wire_type='length_delimited',
                                                                           data=ParsedResults(results=[
                                                                               ParsedResult(field=1, wire_type='varint',
                                                                                            data=4),
                                                                               ParsedResult(field=2, wire_type='varint',
                                                                                            data=1)])),
                                                              ParsedResult(field=12, wire_type='varint', data=0)]))])
