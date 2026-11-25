import unittest

import ventoinha_macbook


class TestPacote(unittest.TestCase):
    def test_versao_definida(self):
        self.assertRegex(ventoinha_macbook.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
