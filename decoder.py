import json
import math
import os
from collections import OrderedDict

from coc.message.reader import CoCMessageReader


class CoCMessageDecoder:

    def __init__(self):
        self.messages = {}
        for entry in os.scandir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "definitions")):
            if entry.is_dir() and entry.name[:1] is not ".":
                if entry.name == "component":
                    self.messages[entry.name] = {}
                for file in os.scandir(entry.path):
                    with open(file.path, 'r') as fh:
                        data = json.load(fh)
                        if entry.name == "component":
                            if "extensions" in data:
                                extensions = {}
                                for extension in data["extensions"]:
                                    extensions[extension["id"]] = extension
                                data["extensions"] = extensions
                            self.messages[entry.name][data["name"]] = data
                        else:
                            self.messages[data["id"]] = data

    def decode(self, messageid, unknown, payload):
        if messageid in self.messages:
            reader = CoCMessageReader(messageid, unknown, payload)
            if "fields" in self.messages[messageid]:
                decoded = {
                    "name": self.messages[messageid]["name"],
                    "fields": self._decode_fields(reader, self.messages[messageid]["fields"])
                }
            else:
                decoded = {
                    "name": self.messages[messageid]["name"]
                }
            unused = reader.read()
            if unused:
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
        if type[:1] == "?":
            if reader.read_int(1):
                type = type[1:]
            else:
                return None
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
        if type == "BOOLEAN":
            return bool(reader.read_int(1))
        elif type == "BYTE":
            return reader.read_byte()
        elif type == "INT":
            return reader.read_int()
        elif type == "LONG":
            return reader.read_long()
        elif type == "STRING":
            return reader.read_string()
        elif type == "ZIP_STRING":
            try:
                decoded = reader.read_zstring().decode()
            except UnicodeDecodeError:
                raise ValueError("Failed to decode JSON.")
            else:
                return json.loads(decoded)
        elif type in self.messages["component"]:
            decoded = self._decode_fields(reader, self.messages["component"][type]["fields"])
            if "extensions" in self.messages["component"][type]:
                if not decoded["id"] in self.messages["component"][type]["extensions"]:
                    raise NotImplementedError("{}(id={}) has not yet been implemented.".format(type, decoded["id"]))
                decoded["payload"] = self._decode_fields(reader, self.messages["component"][type]["extensions"][decoded["id"]]["fields"])
            return decoded
        else:
            raise NotImplementedError("".join([type, " has not yet been implemented."]))

    def dump(self, decoded, hide_unknown=False):
        if "fields" in decoded:
            print("{}: {}".format(decoded["name"], json.dumps(self.stringify(decoded["fields"], hide_unknown), indent=2)))
        else:
            print("".join(["{}: ".format(decoded["name"]), "{}"]))

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
