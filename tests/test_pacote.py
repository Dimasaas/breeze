import unittest

import breeze


class TestPacote(unittest.TestCase):
    def test_versao_definida(self):
        self.assertRegex(breeze.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
