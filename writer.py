from io import BufferedWriter, BytesIO
import zlib


class CoCMessageWriter(BufferedWriter):

    def __init__(self, messageid, unknown):
        self._messageid = messageid
        self._unknown = unknown
        super(CoCMessageWriter, self).__init__(BytesIO())

    def write_byte(self, data):
        self.write(bytes(data)[:1])

    def write_int(self, data, length=4):
        self.write(int(data).to_bytes(length, byteorder="big"))

    def write_long(self, data):
        self.write_int(data, 8)

    def write_string(self, data):
        if len(data):
            self.write_int(len(data))
            self.write(data)
        else:
            self.write_int(pow(2, 32) - 1)

    def write_zstring(self, data):
        if len(data):
            compressed = zlib.compress(data.encode(), 9)
            self.write_int(len(compressed) + 4)
            self.write(int.to_bytes(len(data), 4, byteorder="little"))
            self.write(compressed)
        else:
            self.write_int(pow(2, 32) - 1)

    def to_bytes(self):
        length = self.tell()
        return self._messageid.to_bytes(2, byteorder="big") + length.to_bytes(3, byteorder="big") + self._unknown.to_bytes(2, byteorder="big") + self.detach().getvalue()
