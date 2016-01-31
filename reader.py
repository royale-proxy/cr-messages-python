from io import BufferedReader, BytesIO, SEEK_CUR
import zlib


class CoCMessageReader(BufferedReader):

    def __init__(self, messageid, unknown, initial_bytes):
        super(CoCMessageReader, self).__init__(BytesIO(initial_bytes))
        self._messageid = messageid
        self._unknown = unknown

    @classmethod
    def frombytes(cls, initial_bytes):
        reader = cls(None, None, initial_bytes)
        reader._messageid = reader.read_int(2)
        reader.seek(3, SEEK_CUR)
        reader._unknown = reader.read_int(2)
        return reader

    @property
    def messageid(self):
        return self._messageid

    @messageid.setter
    def messageid(self, messageid):
        raise AttributeError("Message ID is read-only.")

    @property
    def unknown(self):
        return self._unknown

    @unknown.setter
    def unknown(self, messageid):
        raise AttributeError("Unknown is read-only.")

    def read_byte(self):
        return self.read(1)

    def read_int(self, length=4):
        return int.from_bytes(self.read(length), byteorder="big")

    def read_long(self):
        return self.read_int(8)

    def read_string(self):
        length = self.read_int()
        if length == pow(2, 32) - 1:
            return b""
        else:
            try:
                decoded = self.read(length)
            except MemoryError:
                raise IndexError("String out of range.")
            else:
                return decoded

    def read_zstring(self):
        length = int.from_bytes(self.read(4), byteorder="big")
        if length == pow(2, 32) - 1:
            return b""
        zlength = int.from_bytes(self.read(4), byteorder="little")
        try:
            decoded = zlib.decompress(self.read(length - 4), 15, zlength)
        except MemoryError:
            raise IndexError("String out of range.")
        except (ValueError, zlib.error) as e:
            raise IndexError("Decompress error: {}".format(e))
        else:
            return decoded

    def peek_int(self, length=4):
        return int.from_bytes(self.peek(length)[:length], byteorder="big")

