import unittest
import util
from util import utf8
from binascii import hexlify
from ctypes import create_string_buffer

class AddressCase(object):
    def __init__(self, lines):
        # https://github.com/ThePiachu/Bitcoin-Unit-Tests/blob/master/Address
        self.ripemd_network = lines[4]
        self.checksummed = lines[8]
        self.base58 = lines[9]

class Base58Tests(unittest.TestCase):

    CHECKSUM = 1
    CHECKSUM_RESERVED = 2

    def setUp(self):
        if not hasattr(self, 'base58_from_bytes'):
            util.bind_all(self, util.bip38_funcs)

            # Test cases from https://github.com/ThePiachu/Bitcoin-Unit-Tests/
            self.cases = []
            cur = []
            with open(util.root_dir + 'src/data/address_vectors.txt', 'r') as f:
                for l in f.readlines():
                    if len(l.strip()):
                        cur.append(l.strip())
                    else:
                        self.cases.append(AddressCase(cur))
                        cur = []

    def encode(self, hex_in, flags):
        if (flags == self.CHECKSUM_RESERVED):
            hex_in += '00000000' # Reserve checksum space
        buf, buf_len = util.make_cbuffer(hex_in)
        return self.base58_from_bytes(buf, buf_len, flags)

    def decode(self, str_in, flags):
        buf, buf_len = util.make_cbuffer('00' * 1024)
        buf_len = self.base58_to_bytes(utf8(str_in), flags, buf, buf_len)
        self.assertNotEqual(buf_len, 0)
        return hexlify(buf)[0:buf_len * 2].upper()


    def test_address_vectors(self):
        """Tests for encoding and decoding with and without checksums"""

        for c in self.cases:
            # Checksummed should match directly in base 58
            base58 = self.encode(c.checksummed, 0)
            self.assertEqual(base58, c.base58)
            # Decode it and make sure it matches checksummed again
            decoded = self.decode(c.base58, 0)
            self.assertEqual(decoded, utf8(c.checksummed))

            # Compute the checksum in the call, appended to a temp
            # buffer or in-place, depending on the flags
            for flags in [self.CHECKSUM, self.CHECKSUM_RESERVED]:
                base58 = self.encode(c.ripemd_network, flags)
                self.assertEqual(base58, c.base58)

                # Decode without checksum validation/stripping, should match
                # checksummed value
                decoded = self.decode(c.base58, 0)
                self.assertEqual(decoded, utf8(c.checksummed))

                # Decode with checksum validation/stripping and compare
                # to original ripemd + network
                decoded = self.decode(c.base58, self.CHECKSUM)
                self.assertEqual(decoded, utf8(c.ripemd_network))


    def test_to_bytes(self):
        fn = lambda s, f, b, l: self.base58_to_bytes(utf8(s), f, b, l)

        buf, buf_len = util.make_cbuffer('00' * 1024)

        # Bad input base58 strings
        for bad in [ '',      # Empty string can't be represented
                     '0',     # Forbidden ASCII character
                     '\x80',  # High bit set
                   ]:
            self.assertEqual(fn(bad, 0, buf, buf_len), 0)

        # Bad checksummed base58 strings
        for bad in [ # libbase58: decode-b58c-fail
                    '19DXstMaV43WpYg4ceREiiTv2UntmoiA9a',
                    # libbase58: decode-b58c-toolong
                    '1119DXstMaV43WpYg4ceREiiTv2UntmoiA9a',
                    # libbase58: decode-b58c-tooshort
                    '111111111111111111114oLvT2'
                ]:
            self.assertEqual(fn(bad, self.CHECKSUM, buf, buf_len), 0)

        # Test output buffer too small
        valid = '16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM' # decodes to 25 bytes
        self.assertEqual(fn(valid, 0, buf, 24), 0)


    def test_from_bytes(self):

        # Leading zeros become ones
        self.assertEqual(self.encode('00', 0), '1')

        # Invalid flags
        self.assertEqual(self.encode('00', 0x7), None)

        buf, buf_len = util.make_cbuffer('00' * 8)
        fn = self.base58_from_bytes

        # O length buffer, no checksum -> NULL
        self.assertEqual(fn(buf, 0, 0), None)

        # O length buffer, append checksum -> NULL
        self.assertEqual(fn(buf, 0, self.CHECKSUM), None)

        # 4 length buffer, checksum in place -> NULL
        self.assertEqual(fn(buf, 4, self.CHECKSUM_RESERVED), None)


if __name__ == '__main__':
    unittest.main()
