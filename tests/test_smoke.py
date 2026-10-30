"""표준 라이브러리 unittest. 실행: python3 -I -m unittest discover -s tests (PREREG v1 시험 3건)"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import planner

ICS = os.path.join(HERE, '..', 'samples', 'day1.ics')
STA = os.path.join(HERE, '..', 'samples', 'stations.json')
REQUIRED = ('station', 'start', 'end', 'minutes', 'reason')
ORIGIN = {'lat': 37.3800, 'lon': 126.6500, 'summary': '출발(인천 송도, 예시)'}

def run(soc, block=None, stations=None):
    ev = planner.parse_ics(ICS)
    st = stations or json.load(open(STA, encoding='utf-8'))
    return planner.plan(ev, st, soc, origin=ORIGIN, blocked=block)

class Prereg(unittest.TestCase):
    def test_soc55_one_charge_in_lunch_slot(self):
        r = run(55)
        self.assertEqual(len(r['charges']), 1)
        c = r['charges'][0]
        self.assertEqual(c['during'], '점심 판교')
        self.assertTrue('12:00' <= c['start'] and c['end'] <= '13:00', c)
        self.assertGreaterEqual(r['final_soc'], 20.0)
        for k in REQUIRED:
            self.assertIn(k, c)
            self.assertNotIn(c[k], (None, ''))

    def test_soc90_no_charge(self):
        r = run(90)
        self.assertEqual(len(r['charges']), 0)
        self.assertGreaterEqual(r['final_soc'], 20.0)

    def test_blocked_a_switches_to_b(self):
        st = json.load(open(STA, encoding='utf-8'))
        st[0]['status'] = '점검중'
        r = run(55, stations=st)
        self.assertEqual(len(r['charges']), 1)
        c = r['charges'][0]
        self.assertEqual(c['station'], '판교 B 급속(예시)')
        self.assertIn('점검중', c['reason'])
        self.assertIn('교체', c['reason'])

if __name__ == '__main__':
    unittest.main()
