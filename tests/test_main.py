import unittest
from datetime import date
from decimal import Decimal
from main import parse_rate, Rate, make_message, fmt_money

SAMPLE = b'''<?xml version="1.0"?>
<rates><item><title>EUR</title><description>620.10</description><quant>1</quant></item>
<item><title>USD</title><description>536,42</description><quant>1</quant></item></rates>'''

class TestRates(unittest.TestCase):
    def test_parse_usd(self):
        rate = parse_rate(SAMPLE, date(2026, 10, 15))
        self.assertEqual(rate.kzt_per_usd, Decimal("536.42"))

    def test_quant(self):
        xml = b'<rates><item><title>USD</title><description>5300</description><quant>10</quant></item></rates>'
        self.assertEqual(parse_rate(xml, date(2026, 10, 15)).kzt_per_usd, Decimal('530'))

    def test_changes(self):
        now = Rate(date(2026, 10, 15), Decimal("536.42"))
        before = Rate(date(2026, 10, 14), Decimal("535.00"))
        text = make_message(now, before)
        self.assertIn("+1,42 ₸", text)
        self.assertIn("📈", text)
        self.assertIn("536,42", text)

    def test_decline(self):
        now = Rate(date(2026, 10, 15), Decimal('535.00'))
        before = Rate(date(2026, 10, 14), Decimal('536.42'))
        self.assertIn("−1,42 ₸", make_message(now, before))

    def test_no_change(self):
        x = Rate(date(2026, 10, 15), Decimal('530'))
        self.assertIn('Без изменений', make_message(x, x))

if __name__ == '__main__':
    unittest.main()
