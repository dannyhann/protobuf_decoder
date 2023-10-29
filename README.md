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
from protobuf_decoder.protobuf_decoder import Parser

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
from protobuf_decoder.protobuf_decoder import Parser

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
from protobuf_decoder.protobuf_decoder import Parser

test_target = "0A 03 E2 9C 8A"
parsed_data = Parser().parse(test_target)
>> parsed_data
>> [ParsedResult(field=1, wire_type="string", data='✊')]
```

# Nested Protobuf Detection Logic
Our project implements a distinct method to determine whether a given input is possibly a nested protobuf. 
The core of this logic is the `is_maybe_nested_protobuf` function. 
We recently enhanced this function to provide a more accurate distinction and handle nested protobufs effectively.

### Current Logic
The `is_maybe_nested_protobuf` function works by:

- Attempting to convert the given hex string to UTF-8.
- Checking the ordinal values of the first four characters of the converted data.
- Returning `True` if the data might be a nested protobuf based on certain conditions, otherwise returning False.

### Extensibility
You can extend or modify the `is_maybe_nested_protobuf` function based on your specific requirements or use-cases. 
If you find a scenario where the current logic can be further improved, 
feel free to adapt the function accordingly.

(A big shoutout to **@fuzzyrichie** for their significant contributions to this update!)


# Reference
- [Google protocol-buffers encoding document](https://developers.google.com/protocol-buffers/docs/encoding)