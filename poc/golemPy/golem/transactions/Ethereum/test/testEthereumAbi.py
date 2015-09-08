import unittest
import sys
import os

sys.path.append(os.environ.get('GOLEM'))

from golem.transactions.Ethereum.ethereum_abi import encode_abi

class TestEthereumAbi(unittest.TestCase):
    def testEncodeAbi(self):
        enc = encode_abi(['uint32','uint32[]','bytes10','bytes'], [int(0x123), [int(0x456), int(0x789)],
                                                                     "1234567890", "Hello, world!"]).encode('hex')
        data = "00000000000000000000000000000000000000000000000000000000000001230000000000000000000000000000000000000000000000000000000000000080313233343536373839300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000004560000000000000000000000000000000000000000000000000000000000000789000000000000000000000000000000000000000000000000000000000000000d48656c6c6f2c20776f726c642100000000000000000000000000000000000000"
        self.assertEqual(enc, data)

    def testAddress(self):
        addr = '407d73d8a49eeb85d32cf465507dd71d507100c1'
        enc = encode_abi(['address'], [str(bytearray.fromhex('407d73d8a49eeb85d32cf465507dd71d507100c1'))]).encode('hex')
        self.assertEqual(enc[-40:], addr)

if __name__ == '__main__':
    unittest.main()