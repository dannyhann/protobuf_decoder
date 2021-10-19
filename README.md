![Test Coverage](coverage.svg)

# Protobuf Decoder
Simple protobuf decoder for python


# Motivation
The goal of this project is decode protobuf binary without proto files

# Installation
Install using pip

`pip install protobuf-decoder`

# Simple Examples
```
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
>> parsed_data
>> [ParsedResult(field=1, wire_type="string", data='테스트')]
```


```
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

>> parsed_data
>> [ParsedResult(field=3, wire_type="length_delimited", data=[ParsedResult(field=1, wire_type="varint", data=150)])]
```

```
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
>> parsed_data
>> [ParsedResult(field=1, wire_type="string", data='✊')]
```

# Reference
- [Google protocol-buffers encoding document](https://developers.google.com/protocol-buffers/docs/encoding)