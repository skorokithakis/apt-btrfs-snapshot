import subprocess
import unittest

class TestPyflakesClean(unittest.TestCase):
    """ ensure that the tree is pyflakes clean """

    def test_pyflakes_clean(self):
        self.assertEqual(subprocess.call(["pyflakes", "."]), 0)


if __name__ == "__main__":
    unittest.main()
