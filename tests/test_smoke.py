"""표준 라이브러리 unittest. 실행: python3 -I -m unittest discover -s tests"""
import unittest

class Smoke(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
