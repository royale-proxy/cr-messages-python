from collections import OrderedDict
from coc.message.reader import CoCMessageReader
from coc.message.definitions import CoCMessageDefinitions
import json
import math



class CoCMessageDecoder:

    _bitfield = None

    def __init__(self, definitions=None):
        if not definitions:
            self._definitions = CoCMessageDefinitions.read()
        self._definitions = definitions

    def decode(self, messageid, unknown, payload):
        if messageid in self._definitions:
            reader = CoCMessageReader(messageid, unknown, payload)
            if "fields" in self._definitions[messageid]:
                decoded = {
                    "name": self._definitions[messageid]["name"],
                    "fields": self._decode_fields(reader, self._definitions[messageid]["fields"])
                }
            else:
                decoded = {
                    "name": self._definitions[messageid]["name"]
                }
            unused = reader.read()
            if unused:
                self.dump(decoded)
                raise IndexError("Unused buffer remains.")
            return decoded
        else:
            raise KeyError("Message definition missing ({}).".format(messageid))

    def _decode_fields(self, reader, fields):
        decoded = OrderedDict()
        for index, field in enumerate(fields):
            if "name" not in field:
                field["name"] = "unknown_{}".format(str(index).zfill(math.floor(math.log10(len(fields)))))
            decoded[field["name"]] = self._decode_field(reader, field["name"], field["type"])
        return decoded


    def _decode_field(self, reader, name, type):
        if not len(reader.peek(1)):
            raise IndexError("Read buffer out of data.")
        if type[:1] == "?":
            if self._bitfield:
                self._bitfield = (self._bitfield << 1) % 16
                if not self._bitfield:
                    return None
            else:
                self._bitfield = 1
            if reader.peek_int(1) & self._bitfield:
                type = type[1:]
                reader.read(1)
                self._bitfield = None
            else:
                return None
        elif self._bitfield:
            reader.read(1)
            self._bitfield = None
        found = type.find("[")
        if found >= 0:
            count = type[found + 1:-1]
            type = type[:found]
            if not count:
                count = reader.read_int()
            decoded = []
            for i in range(int(count)):
                decoded.append(self._decode_field(reader, "{}[{}]".format(name, i), type))
            return decoded
        elif type == "BOOLEAN":
            return bool(reader.read_int(1))
        elif type == "BYTE":
            return reader.read_byte()
        elif type == "SHORT":
            return reader.read_short()
        elif type == "INT":
            return reader.read_int()
        elif type == "LONG":
            return reader.read_long()
        elif type == "STRING":
            return reader.read_string()
        elif type == "ZIP_STRING":
            decoded = reader.read_zstring()
            if not decoded:
                return decoded
            try:
                decoded = decoded.decode()
            except UnicodeDecodeError:
                raise ValueError("Failed to decode JSON.")
            else:
                return json.loads(decoded)
        elif type in self._definitions["component"]:
            decoded = self._decode_fields(reader, self._definitions["component"][type]["fields"])
            if "extensions" in self._definitions["component"][type]:
                if not decoded["id"] in self._definitions["component"][type]["extensions"]:
                    raise NotImplementedError("{}(id={}) has not yet been implemented.".format(type, decoded["id"]))
                decoded["payload"] = self._decode_fields(reader, self._definitions["component"][type]["extensions"][decoded["id"]]["fields"])
            return decoded
        else:
            raise NotImplementedError("{} has not yet been implemented.".format(type))

    def dump(self, decoded, hide_unknown=False):
        if "fields" in decoded:
            print("{}: {}".format(decoded["name"], json.dumps(self.stringify(decoded["fields"], hide_unknown), indent=2)))
        else:
            print("{}: {{}}".format(decoded["name"]))

    def stringify(self, decoded, hide_unknown=False):
        stringified = type(decoded)()
        if type(decoded) is list:
            keys = range(len(decoded))
        else:
            keys = decoded.keys()
        for key in keys:
            if hide_unknown and key[:len("unknown_")] == "unknown_":
                continue
            value = decoded[key]
            if type(value) is bytes:
                try:
                    str = value.decode()
                except UnicodeDecodeError:
                    str = value.hex()
            elif type(value) in {dict, list, OrderedDict}:
                str = self.stringify(value)
            else:
                str = value
            if type(stringified) is list:
                stringified.append(str)
            else:
                stringified[key] = str
        return stringified
