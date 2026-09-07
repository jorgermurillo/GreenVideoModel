import unittest
from .power_models import get_server_energy, network_hop_energy

class TestServerEmissions(unittest.TestCase):

    def test_1(self):
        self.assertEqual('foo'.upper(), 'FOO')
        self.assertTrue(abs(network_hop_energy(stream_data_size =7,  energy_intensity =10) - 2.7777778e-6 ) < 1e-2 )
    # def test_isupper(self):
    #     self.assertTrue('FOO'.isupper())
    #     self.assertFalse('Foo'.isupper())

    # def test_split(self):
    #     s = 'hello world'
    #     self.assertEqual(s.split(), ['hello', 'world'])
    #     # check that s.split fails when the separator is not a string
    #     with self.assertRaises(TypeError):
    #         s.split(2)

if __name__ == '__main__':
    unittest.main()