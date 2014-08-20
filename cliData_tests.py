from clidata import *
import unittest
import numpy as np


class test_CliData(unittest.TestCase):
	def setUp(self):
		self.seasons={"year": range(1, 13), "summer": [6, 7, 8], "winter": [-1, 1, 2]}
		self.cd = cliData.load('test')
		self.cd.getSeasonsData(self.seasons)

	def test_valsReading(self):
		self.assertEqual(self.cd[1969][12], -20.9)
		self.assertEqual(self.cd[1972][1], -24.0)
		self.assertEqual(self.cd[2007][13], -23.1)
		self.assertEqual(self.cd[2008][-2], -16.9)
		self.assertEqual(self.cd[2008][15], None)
		self.assertEqual(self.cd[3298][1], None)

	def test_slice(self):
		slc = self.cd[1961:1990]
		yNlist = [v.year for v in slc]
		self.assertEqual(yNlist, range(1961, 1991))

	def test_metaInf(self):
		self.assertEqual(self.cd.meta['lat'], 79.55)
		self.assertEqual(self.cd.meta['lon'], 90.62)

	def test_MinMaxY(self):
		self.assertEqual(self.cd.yMin, 1940)
		self.assertEqual(self.cd.yMax, 2008)

	def test_Iter(self):
		r = [1940, 1941, 1942,1943,1944, 1945, 1946, 1947, 1948, 1949, 1950, 1951, 1952, 1953, 1954, 1955, 1956, 1957,
		   1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973,
		   1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989,
		   1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005,
		   2006, 2007, 2008]
		self.assertEqual([v.year for v in self.cd], r)

	def test_norm(self):
		r = [-31.09, -29.79, -29.14, -21.30, -12.47, -2.16, 0.89, 0.01, -3.53, -13.47, -21.41, -24.57]
		cr=self.cd.norm(1961, 1969)
		self.assertEqual(cr, r)

	def test_s_norm(self):
		r = {'summer':-0.54, 'winter':-29.51, 'year':-16.1}
		self.assertEqual(self.cd.s_norm(1961, 1964,self.seasons), r)

	def test_anomal(self):
		r = [[0.49, 1.19, 4.24, 3.6, 0.27, 0.76, 0.51, 0.69, 1.83, 3.47, 0.41, -2.63]]
		cr=self.cd.anomal(1961, 1969, 1961, 1961)
		self.assertEqual(False in r==cr, False)

	def test_meanAnomal(self):
		r = np.array([0.49, 1.19, 4.24, 3.6, 0.27, 0.76, 0.51, 0.69, 1.83, 3.47, 0.41, -2.63])
		cr=self.cd.meanAnomal(1961, 1969, 1961, 1961)
		self.assertEqual(False in r==cr, False)

	def test_yearDatapass(self):
		self.assertEqual(self.cd[1948].datapass, 0)
		self.assertEqual(self.cd[1968].datapass, 16.67)

	def test_yearS_ampl(self):
		r = {'winter':5.9, 'summer':3.2, 'year': 29.6}
		self.assertEqual(self.cd[2008].s_ampl(), r)

	def test_yearAmpl(self):
		self.assertEqual(self.cd[2006].ampl, 26.1)

	def test_yearIter(self):
		r1 = [-28.4, -25.8, -28.2, -19.9, -8.9, -1.6, 1, 1, -3.1, -11.4, -21.7, -18.7]
		self.assertEqual([v for v in self.cd[1999]], r1)
		r2 = [-28.3, None, None, None, None, None, None, None, None, None, None, None]
		self.assertEqual([v for v in self.cd[1994]], r2)

	def test_yearS_avg(self):
		r = {'winter':-26., 'summer':0.03, 'year':-12.28}
		self.assertEqual(self.cd[2007].s_avg(), r)
		r1 = {'winter':-28.8, 'summer':-0.4, 'year': None}
		self.assertEqual(self.cd[1974].s_avg(), r1)

	def test_yearAvg(self):
		self.assertEqual(self.cd[2006].avg, -12.76)
		self.assertEqual(self.cd[1995].avg, None)

	def test_yearSumMoreThen(self):
		self.assertEqual(self.cd[2005].sumMoreThen(-10), -15.4)
		self.assertEqual(self.cd[1996].sumMoreThen(-10), None)
		self.assertEqual(self.cd[1974].sumMoreThen(-10), -14.8)

	def test_yearPassedMonth(self):
		self.assertEqual(self.cd[1997].missedMonth, 2)
		self.assertEqual(self.cd[2005].missedMonth, 0)

	def test_yearSumLessThen(self):
		self.assertEqual(self.cd[2005].sumLessThen(-10), -126.1)

	def test_saveload(self):
		from clidata import cliData
		self.cd.save('tmp', replace=True)
		aco = cliData.load('tmp')
		self.assertEqual(self.cd.eq(aco), True)

	def test_eq(self):
		self.assertEqual(self.cd.eq(self.cd), True)
		self.assertEqual(self.cd[2005].eq(self.cd[2004]), False)

	def test_ccInsertNone(self):
		v,t=cc.insertNone([2.3, 4.5, 6.7], [1,3,4])
		self.assertEqual(v, [2.3, None, 4.5, 6.7])
		self.assertEqual(t, [1,2,3,4])



if __name__ == '__main__':
	unittest.main()
