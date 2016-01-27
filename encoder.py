from coc.message.writer import CoCMessageWriter
from coc.message.definitions import CoCMessageDefinitions
import json
import math


class CoCMessageEncoder:

    _debug = True

    def __init__(self, definitions):
        if not definitions:
            self._definitions = CoCMessageDefinitions.read()
        self._definitions = definitions

    def encode(self, messageid, unknown, data):
        if self._debug:
            self._i = 0
            self._component_stack = []
            self._count_stack = []
        if messageid in self._definitions:
            writer = CoCMessageWriter(messageid, unknown)
            if "fields" in self._definitions[messageid]:
                self._encode_fields(writer, data["fields"], self._definitions[messageid]["fields"])
            return writer.to_bytes()
        else:
            raise KeyError("Message definition missing ({}).".format(messageid))

    def _encode_fields(self, writer, data, fields):
        for index, field in enumerate(fields):
            if "name" not in field:
                field["name"] = "unknown_{}".format(str(index).zfill(math.floor(math.log10(len(fields)))))
            self._encode_field(writer, data[field["name"]], field["name"], field["type"])

    def _encode_field(self, writer, data, name, type):
        if type[:1] == "?":
            if data:
                writer.write_int(True, 1)
                type = type[1:]
            else:
                writer.write_int(False, 1)
                return None
        found = type.find("[")
        if found >= 0:
            count = type[found + 1:-1]
            type = type[:found]
            if not count:
                count = len(data)
                writer.write_int(count)
            for i in range(int(count)):
                self._encode_field(writer, data[i], "{}[{}]".format(name, i), type)
        elif type == "BOOLEAN":
            writer.write_int(int(data), 1)
        elif type == "BYTE":
            writer.write_byte(data)
        elif type == "INT":
            writer.write_int(data)
        elif type == "LONG":
            writer.write_long(data)
        elif type == "STRING":
            writer.write_string(data)
        elif type == "ZIP_STRING":
            writer.write_zstring(json.dumps(data))
        elif type in self._definitions["component"]:
            self._encode_fields(writer, data, self._definitions["component"][type]["fields"])
            if "extensions" in self._definitions["component"][type]:
                if not data["payload"]["id"] in self._definitions["component"][type]["extensions"]:
                    raise NotImplementedError("{}(id={}) has not yet been implemented.".format(type, data["payload"]["id"]))
                self._encode_fields(writer, data["payload"], self._definitions["component"][type]["extensions"][data["payload"]["id"]]["fields"])
        else:
            raise NotImplementedError("{} has not yet been implemented.".format(type))
