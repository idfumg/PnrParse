#!/usr/bin/env python


import unittest
# from datetime import datetime
import datetime

from pnr_read import read_pnr
from pnr_types import (Itin, Ssr, Pax, Contact, PnrParseException, Responsibility, Osi,
                       Remarks, Group)
from pnr_parse import (cut_regnum_from_pax, parse_itin, parse_ssr, parse_pax, parse_pnr,
                      collect_pnr, parse_osi, parse_remarks, parse_group)

from pnr_telegram import (make_telegram, find_remote_data)


RECORD = r"""03   1.HOULE/LANCE M MR T02XL
04   2.   AC 003  C   MO09JUN  YVRNRT HK    1210 1425+1
04   3.   HZ 9234 C   TU10JUN  NRTUUS HK1   1630 2100
04   4.   HZ 9233 Y   TH10JUL  UUSNRT HK1   1305 1350
04   5.   AC 004  P   TH10JUL  NRTYVR HK    1700 1000
06   6.YYC/T 403 508 3000 A
06   7.YQM/P 1 800 378 7587 A AFTER HOURS
06   8.YEG/H 1 780 238 0369 H
06   9.YEG/B 1 832 254 8022 B
06  10.CTC/P LANCE.M.HOULE EXXONMOBIL.COM E
06  11.CTC/B LANCE HOULE 1 832 254 8022 B
13  12.SSR DOCS HZ  HK1 /////26MAY59/M//HOULE/LANCE/M/P1
13  13.SSR TKNE HZ  HK1 NRTUUS9234C10JUN.5554830283022C1/P1
13  14.SSR TKNE HZ  HK1 UUSNRT9233Y10JUL.5554830283022C2/P1
14  15.OSI YY  CARLSON WAGONLIT TRAVEL IATA 60734822
14  16.OSI YY  OIN CE23X
15  17.ETA I 10JUN14 NRTUUS 5554830283022C1/P1
15  18.ETA I 10JUL14 UUSNRT 5554830283022C2/P1
31  19.HDQ1S /MOHVEI/8WN4/61734934"""


class Settings:
    def __init__(self):
        self.airline = 'HZ'
        self.src_addr = 'HDQRM5N'
        self.format = 'airimp'
        self.current_year = '2014'
        self.pred_point = 'HDQ5N'
        self.dest_addr = 'MOWRM5N'
        self.local_systems = None
        self.ignored = None


class TestPnrParse(unittest.TestCase):
    def setUp(self):
        self.record = RECORD.split('\n')
        self.settings = Settings()


    def test_parse_pnr_on_data(self):
        filename = 'data'
        self.assertEqual(len([parse_pnr(record, self.settings) for record in read_pnr(filename)]), 12)


    def test_cut_regnum_from_pax(self):
        self.assertEqual(cut_regnum_from_pax("ULEZKO/ALINA MRS VZGJZ"),
                         ('ULEZKO/ALINA MRS', 'VZGJZ'))
        self.assertEqual(cut_regnum_from_pax("NIDENS/SVETLANA NIKOL VZHV7"),
                         ('NIDENS/SVETLANA NIKOL', 'VZHV7'))
        self.assertEqual(cut_regnum_from_pax("12GRP/ENL NM12 VYDVJ"),
                         ('12GRP/ENL NM12', 'VYDVJ'))
        self.assertEqual(cut_regnum_from_pax("GUILLAU/DAVID VX141"),
                         ('GUILLAU/DAVID', 'VX141'))


    def test_parse_itin(self):
        self.assertEqual(parse_itin('AC 003  C   MO09JUN  YVRNRT HK    1210 1425+1', None, self.settings),
                         Itin(airline='AC', flightnum='003', itin_class='C', depdate=datetime.date(2014, 6, 9), deppoint='YVR', arrpoint='NRT', status='HK', nseats=None, deptime='1210', arrtime='1425+1', text=''))
        self.assertEqual(parse_itin('HZ 9234 C   TU10JUN  NRTUUS HK1   1630 2100', None, self.settings),
                         Itin(airline='HZ', flightnum='9234', itin_class='C', depdate=datetime.date(2014, 6, 10), deppoint='NRT', arrpoint='UUS', status='HK', nseats='1', deptime='1630', arrtime='2100', text=''))
        self.assertEqual(parse_itin('HZ 9239 Y   WE14MAY14UUSNGK HK12  0900 1030', None, self.settings),
                         Itin(airline='HZ', flightnum='9239', itin_class='Y', depdate=datetime.date(2014, 5, 14), deppoint='UUS', arrpoint='NGK', status='HK', nseats='12', deptime='0900', arrtime='1030', text=''))
        self.assertEqual(parse_itin('HZ OPEN Y        UUSCTS', None, self.settings),
                         Itin(airline='HZ', flightnum='OPEN', itin_class='Y', depdate=None, deppoint='UUS', arrpoint='CTS', status=None, nseats=None, deptime=None, arrtime=None, text=''))
        self.assertEqual(parse_itin('SU 5696 N   TU09SEP  UUSICN HK2   0930 1050   AKYBDQ', None, self.settings),
                         Itin(airline='SU', flightnum='5696', itin_class='N', depdate=datetime.date(2014, 9, 9), deppoint='UUS', arrpoint='ICN', status='HK', nseats='2', deptime='0930', arrtime='1050', text='AKYBDQ'))
        self.assertEqual(parse_itin('HZ 801  Y   MO19MAY  UUSBVV HK1   1250 1410  QTE', None, self.settings),
                         Itin(airline='HZ', flightnum='801', itin_class='Y', depdate=datetime.date(2014, 5, 19), deppoint='UUS', arrpoint='BVV', status='HK', nseats='1', deptime='1250', arrtime='1410', text='QTE'))
        self.assertEqual(parse_itin('HZ 151  M   WE04JUN  UUSCTS HL1   1300 1220  /5', None, self.settings),
                         Itin(airline='HZ', flightnum='151', itin_class='M', depdate=datetime.date(2014, 6, 4), deppoint='UUS', arrpoint='CTS', status='HL', nseats='1', deptime='1300', arrtime='1220', text='/5'))
        self.assertEqual(parse_itin('SU 5697 N   TU17JUN  ICNUUS UN2   1200 1700  S AKYBDQ', None, self.settings),
                         Itin(airline='SU', flightnum='5697', itin_class='N', depdate=datetime.date(2014, 6, 17), deppoint='ICN', arrpoint='UUS', status='UN', nseats='2', deptime='1200', arrtime='1700', text='S AKYBDQ'))
        self.assertEqual(parse_itin('HZ 802  Y   WE04JUN  BVVUUS UN1   1500 1620  S REQ ALL RES', None, self.settings),
                         Itin(airline='HZ', flightnum='802', itin_class='Y', depdate=datetime.date(2014, 6, 4), deppoint='BVV', arrpoint='UUS', status='UN', nseats='1', deptime='1500', arrtime='1620', text='S REQ ALL RES'))
        self.assertEqual(parse_itin('KE 654  T   MO28JUL  BKKICN UN2   2345 0705+1S ET6CT3', None, self.settings),
                         Itin(airline='KE', flightnum='654', itin_class='T', depdate=datetime.date(2014, 7, 28), deppoint='BKK', arrpoint='ICN', status='UN', nseats='2', deptime='2345', arrtime='0705+1', text='S ET6CT3'))
        self.assertEqual(parse_itin('KE 658  T   MO28JUL  BKKICN TK2   2345 0705+1S', None, self.settings),
                         Itin(airline='KE', flightnum='658', itin_class='T', depdate=datetime.date(2014, 7, 28), deppoint='BKK', arrpoint='ICN', status='TK', nseats='2', deptime='2345', arrtime='0705+1', text='S'))


    def test_parse_ssr(self):
        self.assertEqual(parse_ssr('SSR OTHS HZ  NN1 UUSDEE 0799T11OCT.TKSTTREBOVANIE VPDFSB0560002459118.TOLKO NA REYSAKHHZ/P1', None, self.settings),
                         Ssr(code='OTHS', airline='HZ', status='NN', nseats='1', text='UUSDEE 0799T11OCT.TKSTTREBOVANIE VPDFSB0560002459118.TOLKO NA REYSAKHHZ', paxnum='1'))
        self.assertEqual(parse_ssr('SSR OTHS HZ  NN1 UUSDEE 0799T11OCT.TKSTTREBOVANIE VPDFSB0560002459118.TOLKO NA REYSAKHHZ/P1', None, self.settings),
                         Ssr(code='OTHS', airline='HZ', status='NN', nseats='1', text='UUSDEE 0799T11OCT.TKSTTREBOVANIE VPDFSB0560002459118.TOLKO NA REYSAKHHZ', paxnum='1'))
        self.assertEqual(parse_ssr('SSR DOCS HZ  HK1 /P/RU/IFC592312/RU/25MAY10/F//SHEYMUKHOVA/ZLATA/', None, self.settings),
                         Ssr(code='DOCS', airline='HZ', status='HK', nseats='1', text='/P/RU/IFC592312/RU/25MAY10/F//SHEYMUKHOVA/ZLATA/', paxnum=None))
        self.assertEqual(parse_ssr('SSR DOCS HZ  HK1 /P/RU/IFC592312/RU/25MAY10/F//SHEYMUKHOVA/ZLATA', None, self.settings),
                         Ssr(code='DOCS', airline='HZ', status='HK', nseats='1', text='/P/RU/IFC592312/RU/25MAY10/F//SHEYMUKHOVA/ZLATA', paxnum=None))
        self.assertEqual(parse_ssr('SSR DOCS HZ  HK1 /P/RU/IFC592312/RU/25MAY10/F//SHEYMUKHOVA/ZLATA/P2', None, self.settings),
                         Ssr(code='DOCS', airline='HZ', status='HK', nseats='1', text='/P/RU/IFC592312/RU/25MAY10/F//SHEYMUKHOVA/ZLATA', paxnum='2'))
        self.assertEqual(parse_ssr('SSR DOCS HZ  HK1 /P/RU/1FS509011/RU/28OCT02/F//MESHCHANINTSEVA/VIKA/P2', None, self.settings),
                         Ssr(code='DOCS', airline='HZ', status='HK', nseats='1', text='/P/RU/1FS509011/RU/28OCT02/F//MESHCHANINTSEVA/VIKA', paxnum='2'))
        self.assertEqual(parse_ssr('SSR DOCS HZ  HK1 /P/RU/6401175922/RU/08JUN74/F//MESHCHANINTSEVA/SVETA/P1', None, self.settings),
                         Ssr(code='DOCS', airline='HZ', status='HK', nseats='1', text='/P/RU/6401175922/RU/08JUN74/F//MESHCHANINTSEVA/SVETA', paxnum='1'))
        self.assertEqual(parse_ssr('SSR DOCS HZ  HK1 /////26MAY59/M//HOULE/LANCE/M/P1', None, self.settings),
                         Ssr(code='DOCS', airline='HZ', status='HK', nseats='1', text='/////26MAY59/M//HOULE/LANCE/M', paxnum='1'))


    def test_parse_pax(self):
        self.assertEqual(parse_pax('TIKHONOVA/SVETLANA MSS', None, self.settings),
                         Pax(name='SVETLANA', surname='TIKHONOVA', status='MSS', nseats=1, group=False))
        self.assertEqual(parse_pax('DE/KHIDYAMS', None, self.settings),
                         Pax(name='KHIDYA', surname='DE', status='MS', nseats=1, group=False))
        self.assertEqual(parse_pax('BELONOGOVA/KSENIYA CHD', None, self.settings),
                         Pax(name='KSENIYA', surname='BELONOGOVA', status='CHD', nseats=1, group=False))
        self.assertEqual(parse_pax('MESHCHANINTSEVA A', None, self.settings),
                         Pax(name=None, surname='MESHCHANINTSEVA A', status=None, nseats=1, group=False))
        self.assertEqual(parse_pax('MESHCHANINTSEVA/SVETA', None, self.settings),
                         Pax(name='SVETA', surname='MESHCHANINTSEVA', status=None, nseats=1, group=False))
        self.assertEqual(parse_pax('MESHCHANINTSEVA/SVETAMRS', None, self.settings),
                         Pax(name='SVETA', surname='MESHCHANINTSEVA', status='MRS', nseats=1, group=False))
        self.assertEqual(parse_pax('MESHCHANINTSEVA', None, self.settings),
                         Pax(name=None, surname='MESHCHANINTSEVA', status=None, nseats=1, group=False))
        self.assertEqual(parse_pax('MESHCHANINTSEVA/VIKA MS', None, self.settings),
                         Pax(name='VIKA', surname='MESHCHANINTSEVA', status='MS', nseats=1, group=False))
        self.assertEqual(parse_pax('MESHCHANINTSEVA/SVETA MRS', None, self.settings),
                         Pax(name='SVETA', surname='MESHCHANINTSEVA', status='MRS', nseats=1, group=False))
        self.assertEqual(parse_pax('HOULE/LANCE M MR', None, self.settings),
                         Pax(name='LANCE M', surname='HOULE', status='MR', nseats=1, group=False))


    def test_parse_osi(self):
        self.assertEqual(parse_osi('OSI HZ  CTCT 74212568521', None, self.settings),
                         Osi(airline='HZ', text='CTCT 74212568521', paxnum=None))

        self.assertEqual(parse_osi('OSI HZ  TRANZIT OKHA-YUZHKH-MOV-GDZH RS SU-1743/1908', None, self.settings),
                         Osi(airline='HZ', text='TRANZIT OKHA-YUZHKH-MOV-GDZH RS SU-1743/1908', paxnum=None))

        self.assertEqual(parse_osi('OSI YY  CMP EIDESVI/P1', None, self.settings),
                         Osi(airline='YY', text='CMP EIDESVI', paxnum='1'))

        self.assertEqual(parse_osi('OSI #1 YY  1INF NARGUN/SHAKHZODA/P1', None, self.settings),
                         Osi(airline='YY', text='1INF NARGUN/SHAKHZODA', paxnum='1'))

        self.assertEqual(parse_osi('OSI HZ  ///P4984242422701422384', None, self.settings),
                         Osi(airline='HZ', text='///P4984242422701422384', paxnum=None))


    def test_parse_remarks(self):
        self.assertEqual(parse_remarks('ETA I 28AUG14 NRTUUS 5986158928451C1/P1', None, self.settings),
                         Remarks(text='ETA I 28AUG14 NRTUUS 5986158928451C1', paxnum='1'))

        self.assertEqual(parse_remarks('RMK PFS GOSHO HZ802 Y 14AUG14 BVVUUS', None, self.settings),
                         Remarks(text='RMK PFS GOSHO HZ802 Y 14AUG14 BVVUUS', paxnum=None))

        self.assertEqual(parse_remarks('ETA BD 09AUG14 CTSUUS 5982401060372C1/P1', None, self.settings),
                         Remarks(text='ETA BD 09AUG14 CTSUUS 5982401060372C1', paxnum='1'))

        self.assertEqual(parse_remarks('ETA RF 10JUN14 DEEUUS 5982401038557C1/SAC5986A598047CJ/P1', None, self.settings),
                         Remarks(text='ETA RF 10JUN14 DEEUUS 5982401038557C1/SAC5986A598047CJ', paxnum='1'))


    def test_parse_group(self):
        self.assertEqual(parse_group('13RITSUMEIKANUNIVERSITY/GRP NM13', None, self.settings),
                         Group(total='13', name='RITSUMEIKANUNIVERSITY', named='13'))

        self.assertEqual(parse_group('22SOTSZSHITA/GRP NM19', None, self.settings),
                         Group(total='22', name='SOTSZSHITA', named='19'))

        self.assertEqual(parse_group('23SOTSPODDERZHKA/GRP NM0', None, self.settings),
                         Group(total='23', name='SOTSPODDERZHKA', named='0'))


    def test_make_telegram(self):
        pnr = parse_pnr(self.record, self.settings)
        telegram = make_telegram(pnr, self.settings)

        t = telegram.split('\n')
        T = r"""MOWRM5N
.HDQRM1S 181614
HDQ1S MOHVEI
1HOULE/LANCE M MR
AC0003C09JUN14 YVRNRT HK1/1210 1425/1
HZ9234C10JUN14 NRTUUS HK1/1630 2100
HZ9233Y10JUL14 UUSNRT HK1/1305 1350
AC0004P10JUL14 NRTYVR HK1/1700 1000
SSR DOCS HZ HK1 /////26MAY59/M//HOULE/LANCE/M-1HOULE/LANCE M MR
SSR TKNE HZ HK1 NRTUUS9234C10JUN-1HOULE/LANCE M MR.5554830283022C1
SSR TKNE HZ HK1 UUSNRT9233Y10JUL-1HOULE/LANCE M MR.5554830283022C2
OSI YY CARLSON WAGONLIT TRAVEL IATA 60734822
OSI YY OIN CE23X
OSI YY REMARK ETA I 10JUN14 NRTUUS 5554830283022C1-1HOULE/LANCE M MR
OSI YY REMARK ETA I 10JUL14 UUSNRT 5554830283022C2-1HOULE/LANCE M MR
OSI YY CTC YYC/T 403 508 3000 A
OSI YY CTC YQM/P 1 800 378 7587 A AFTER HOURS
OSI YY CTC YEG/H 1 780 238 0369 H
OSI YY CTC YEG/B 1 832 254 8022 B
OSI YY CTC CTC/P LANCE.M.HOULE EXXONMOBIL.COM E
OSI YY CTC CTC/B LANCE HOULE 1 832 254 8022 B
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T02XL
OSI YY 23 POS/HDQ1S /MOHVEI/8WN4/61734934""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


    def test_group_pnr(self):
        GROUP_PNR = """02   0.14SOTSPODDERZHKA/GRP NM0 VSG5F
04   1.   HZ 802  Y   FR26SEP  BVVUUS HK14  1500 1620
05   2.BKD 14 CNL 0 SPLIT 0
06   3.8-42454-42963
07   4.TL/X/1900/21SEP/UUS005
31   5.UUS005//UUS/HZ/A/RU"""

        pnr = parse_pnr(GROUP_PNR.split('\n'), self.settings)
        telegram = make_telegram(pnr, self.settings)

        t = telegram.split('\n')
        T = r"""MOWRM5N
.MOWRM1H 271206
MOW1H IMPORTVSG5F
14SOTSPODDERZHKA
HZ0802Y26SEP14 BVVUUS HK14/1500 1620
SSR GRPS YY TCP14 SOTSPODDERZHKA
OSI YY CTC 8-42454-42963
OSI YY 23 AUTOMATIC IMPORT HDQ5N/VSG5F
OSI YY 23 POS/UUS005//UUS/HZ/A/RU""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


    def test_find_remote_system_pnr(self):
        text = r'MOW1H /N3PG3K/08HBR/KHBRE40/TKP08KHBR0059'
        self.assertEqual(find_remote_data(text, self.settings), ('MOW1H', 'N3PG3K'))

        text = 'UUS012//UUS/HZ/A/RU'
        self.assertEqual(find_remote_data(text, self.settings), ('UUS012', None))

        text = 'SPK002/00000000/SPK/HZ/N/JP'
        self.assertEqual(find_remote_data(text, self.settings), ('SPK002', None))

        text = 'UUS001'
        self.assertEqual(find_remote_data(text, self.settings), ('UUS001', None))

        text = 'HDQ1J /MZ29UV'
        self.assertEqual(find_remote_data(text, self.settings), ('HDQ1J', 'MZ29UV'))


    def test_change_chld_airline(self):
        CHLD_PNR = """03   1.MISHNEV/ALEXANDR ALEKSEEVICH MR 2.TSUBENKO/ARTEM VYACHESLAVOVICH CHD
03     T1774
04   3.   HZ 806  Y   FR22AUG  EKSUUS HK2   1045 1145
04   4.   SU 5629 T   FR22AUG  UUSKHV HK2   1705 1825   IWFHMZ QTE
06   5.79294100800
06   6.H/74243227243
07   7.T/ *T
13   8.SSR CHLD SU  HK1 /20JUL06/P2
13   9.SSR DOCS HZ  HK1 /P/RU/0813214708/RU/14JAN00/M/25FEB16/MISHNEV/
13      ALEXANDRALEKSEEVICH/P1
13  10.SSR DOCS HZ  HK1 /P/RU/IDV677942/RU/20JUL06/M/03AUG16/TSUBENKO/
13      ARTEMVYACHESLAVOVICH/P2
13  11.SSR FOID SU  HK1 PP6413214708/P1
13  12.SSR FOID HZ  HK1 PPSRIDV677942/P2
13  13.SSR FOID SU  HK1 PPSRIDV677942/P2
13  14.SSR PCTC HZ  HK/ MISHNEV/ALEXANDR ALEKSEEVICH/79294100800
13  15.SSR PCTC HZ  HK/ MISHNEV/ALEXANDR LEKSEEVICH/74243227243
13  16.SSR PCTC HZ  HK/ TSUBENKO/ARTEM VYACHESLAVOVICH/79294100800
13  17.SSR PCTC HZ  HK/ TSUBENKO/ARTEM VYACHESLAVOVICH/74243227243
13  18.SSR TKNE HZ  HK1 EKSUUS 0806Y22AUG.5982400856246C1/P1
13  19.SSR TKNE HZ  HK1 EKSUUS 0806Y22AUG.5982400856247C1/P2
13  20.SSR TKNE SU  HK1 UUSKHV 5629T22AUG.5982400856248C1/P1
13  21.SSR TKNE SU  HK1 UUSKHV 5629T22AUG.5982400856249C1/P2
15  22.ETA I 22AUG14 EKSUUS 5982400856246C1/P1
15  23.ETA I 22AUG14 EKSUUS 5982400856247C1/P2
15  24.ETA AL 22AUG14 UUSKHV 5982400856248C1/P1
15  25.ETA AL 22AUG14 UUSKHV 5982400856249C1/P2
21  26.TN/2400856246/HZ /59805524 /0722/E //P1 A 18JUL14
21  27.TN/2400856247/HZ /59805524 /0722/E //P2 A 18JUL14
21  28.TN/2400856248/HZ /59805524 /0722/E //P1 A 18JUL14
21  29.TN/2400856249/HZ /59805524 /0722/E //P2 A 18JUL14
31  30.EKS001//EKS/HZ/A/RU"""

        pnr = parse_pnr(CHLD_PNR.split('\n'), self.settings)
        telegram = make_telegram(pnr, self.settings)

        t = telegram.split('\n')
        T = r"""MOWRM5N
.MOWRM1H 191106
MOW1H IMPORTT1774
1MISHNEV/ALEXANDR ALEKSEEVICH MR
1TSUBENKO/ARTEM VYACHESLAVOVICH CHD
HZ0806Y22AUG14 EKSUUS HK2/1045 1145
SU5629T22AUG14 UUSKHV HK2/1705 1825
SSR CHLD HZ HK1 /20JUL06-1TSUBENKO/ARTEM VYACHESLAVOVICH CHD
SSR DOCS HZ HK1 /P/RU/0813214708/RU/14JAN00/M/25FEB16/MISHNEV
SSR DOCS HZ////ALEXANDRALEKSEEVICH-1MISHNEV/ALEXANDR ALEKSEEVICH MR
SSR DOCS HZ HK1 /P/RU/IDV677942/RU/20JUL06/M/03AUG16/TSUBENKO
SSR DOCS HZ////ARTEMVYACHESLAVOVICH-1TSUBENKO/ARTEM VYACHESLAVOVICH
SSR DOCS HZ/// CHD
SSR FOID SU HK1 PP6413214708-1MISHNEV/ALEXANDR ALEKSEEVICH MR
SSR FOID HZ HK1 PPSRIDV677942-1TSUBENKO/ARTEM VYACHESLAVOVICH CHD
SSR FOID SU HK1 PPSRIDV677942-1TSUBENKO/ARTEM VYACHESLAVOVICH CHD
SSR PCTC HZ HK/ MISHNEV/ALEXANDR ALEKSEEVICH/79294100800
SSR PCTC HZ HK/ MISHNEV/ALEXANDR LEKSEEVICH/74243227243
SSR PCTC HZ HK/ TSUBENKO/ARTEM VYACHESLAVOVICH/79294100800
SSR PCTC HZ HK/ TSUBENKO/ARTEM VYACHESLAVOVICH/74243227243
SSR TKNE HZ HK1 EKSUUS 0806Y22AUG-1MISHNEV/ALEXANDR ALEKSEEVICH
SSR TKNE HZ/// MR.5982400856246C1
SSR TKNE HZ HK1 EKSUUS 0806Y22AUG-1TSUBENKO/ARTEM VYACHESLAVOVICH
SSR TKNE HZ/// CHD.5982400856247C1
SSR OTHS HZ SSR TKNE SU HK1 UUSKHV 5629T22AUG-1MISHNEV/ALEXANDR
SSR OTHS HZ/// ALEKSEEVICH MR.5982400856248C1
SSR OTHS HZ SSR TKNE SU HK1 UUSKHV 5629T22AUG-1TSUBENKO/ARTEM
SSR OTHS HZ/// VYACHESLAVOVICH CHD.5982400856249C1
OSI YY REMARK ETA I 22AUG14 EKSUUS 5982400856246C1-1MISHNEV/ALEXANDR
OSI YY REMARK /// ALEKSEEVICH MR
OSI YY REMARK ETA I 22AUG14 EKSUUS 5982400856247C1-1TSUBENKO/ARTEM
OSI YY REMARK /// VYACHESLAVOVICH CHD
OSI YY REMARK ETA AL 22AUG14 UUSKHV 5982400856248C1-1MISHNEV
OSI YY REMARK ////ALEXANDR ALEKSEEVICH MR
OSI YY REMARK ETA AL 22AUG14 UUSKHV 5982400856249C1-1TSUBENKO/ARTEM
OSI YY REMARK /// VYACHESLAVOVICH CHD
OSI YY CTC 79294100800
OSI YY CTC H/74243227243
OSI YY REMARK TN/2400856246/HZ /59805524 /0722/E /-1MISHNEV/ALEXANDR
OSI YY REMARK /// ALEKSEEVICH MR
OSI YY REMARK TN/2400856247/HZ /59805524 /0722/E /-1TSUBENKO/ARTEM
OSI YY REMARK /// VYACHESLAVOVICH CHD
OSI YY REMARK TN/2400856248/HZ /59805524 /0722/E /-1MISHNEV/ALEXANDR
OSI YY REMARK /// ALEKSEEVICH MR
OSI YY REMARK TN/2400856249/HZ /59805524 /0722/E /-1TSUBENKO/ARTEM
OSI YY REMARK /// VYACHESLAVOVICH CHD
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T1774
OSI YY 23 POS/EKS001//EKS/HZ/A/RU""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


    def test_skip_pnr(self):
        """
        No one airline (HZ) segments in PNR.
        """

        SKIP_PNR = """03   1.TCOI/DENSUN MRS VZJJP
04   2.   SU 5696 N   SA11OCT  UUSICN HK1   0930 1050   NISEJA
06   3.031-981-6361
07   4.T/ *T
13   5.SSR DOCS SU  HK1 /P/RU/721630319/RU/16JAN43/F/19OCT22/TCOI/DENSUN/P1
13   6.SSR FOID HZ  HK1 PP721630319/P1
13   7.SSR FOID SU  HK1 PP721630319/P1
13   8.SSR TKNE SU  HK1 UUSICN 5696N11OCT.5982401056580C2/P1
15   9.ETA AL 20JUL14 ICNUUS 5982401056580C1/P1
15  10.ETA AL 11OCT14 UUSICN 5982401056580C2/P1
21  11.TN/2401056580/HZ /59801276 /0046/E //P1 M 18APR14
31  12.SEL001//SEL/HZ/A/KR"""

        pnr = parse_pnr(SKIP_PNR.split('\n'), self.settings)
        telegram = make_telegram(pnr, self.settings)

        self.assertEqual(telegram, None)


    def test_skip_pass_name(self):
        """
        Skip PNR with no passenger name (fictive PNR).
        """

        SKIP_PNR = """03   1.OX 2.OX VMSKJ
04   3.   HZ 782  Y   TU02SEP  OHHUUS HK2   1310 1510
06   4.OURR
07   5.TL/X/1510/01SEP/UUS001
31   6.UUS001//UUS/HZ/A/RU"""

        pnr = parse_pnr(SKIP_PNR.split('\n'), self.settings)
        telegram = make_telegram(pnr, self.settings)

        self.assertEqual(telegram, None)


    def test_replace_undescore_in_docs(self):
        """
        Replace all underscore in SSR DOCS text.
        """

        PNR = """03   1.MAGOMEDOVA/AMINAT MRS 2.RAMAZANOVA/SIYANA MRS T167C
04   3.   HZ 801  Y   TU19AUG  UUSBVV HK2   1250 1410  QTE
06   4.89241964635
07   5.T/ *T
13   6.SSR CHLD HZ  HK1 /19AUG07/P1
13   7.SSR DOCS HZ  HK1 /P/RU/II+BD576987/RU/19AUG07/F//MAGOMEDOVA/AMINAT/P1
13   8.SSR DOCS HZ  HK1 /P/RU/8504308551/RU/08SEP85/F//RAMAZANOVA/SIYANA/P2
13   9.SSR FOID HZ  HK1 PPSRIIBD576987/P1
13  10.SSR FOID HZ  HK1 PP8504308551/P2
13  11.SSR PCTC HZ  HK/ RAMAZANOVA/SIYANA 79241964635/P2
13  12.SSR TKNE HZ  HK1 UUSBVV 0801Y19AUG.5982401074556C1/P1
13  13.SSR TKNE HZ  HK1 UUSBVV 0801Y19AUG.5982401074557C1/P2
15  14.ETA I 19AUG14 UUSBVV 5982401074556C1/P1
15  15.ETA I 19AUG14 UUSBVV 5982401074557C1/P2
15  16.ETA RF 11AUG14 BVVUUS 5982401074554C1/SAC59888598016US/P1
15  17.ETA RF 11AUG14 BVVUUS 5982401074555C1/SAC59888598016V5/P2
21  18.TN/2401074554/HZ /59805141 /0551/E //P1 A 18JUL14
21  19.TN/2401074555/HZ /59805141 /0551/E //P2 A 18JUL14
21  20.TN/2401074556/HZ /59805141 /0551/E //P1 A 18JUL14
21  21.TN/2401074557/HZ /59805141 /0551/E //P2 A 18JUL14
31  22.BVV001//BVV/HZ/A/RU"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 181615
MOW1H IMPORTT167C
1MAGOMEDOVA/AMINAT MRS
1RAMAZANOVA/SIYANA MRS
HZ0801Y19AUG14 UUSBVV HK2/1250 1410
SSR CHLD HZ HK1 /19AUG07-1MAGOMEDOVA/AMINAT MRS
SSR DOCS HZ HK1 /P/RU/IIBD576987/RU/19AUG07/F//MAGOMEDOVA
SSR DOCS HZ////AMINAT-1MAGOMEDOVA/AMINAT MRS
SSR DOCS HZ HK1 /P/RU/8504308551/RU/08SEP85/F//RAMAZANOVA
SSR DOCS HZ////SIYANA-1RAMAZANOVA/SIYANA MRS
SSR FOID HZ HK1 PPSRIIBD576987-1MAGOMEDOVA/AMINAT MRS
SSR FOID HZ HK1 PP8504308551-1RAMAZANOVA/SIYANA MRS
SSR PCTC HZ HK/ RAMAZANOVA/SIYANA 79241964635-1RAMAZANOVA/SIYANA MRS
SSR TKNE HZ HK1 UUSBVV 0801Y19AUG-1MAGOMEDOVA/AMINAT
SSR TKNE HZ/// MRS.5982401074556C1
SSR TKNE HZ HK1 UUSBVV 0801Y19AUG-1RAMAZANOVA/SIYANA
SSR TKNE HZ/// MRS.5982401074557C1
OSI YY REMARK ETA I 19AUG14 UUSBVV 5982401074556C1-1MAGOMEDOVA
OSI YY REMARK ////AMINAT MRS
OSI YY REMARK ETA I 19AUG14 UUSBVV 5982401074557C1-1RAMAZANOVA
OSI YY REMARK ////SIYANA MRS
OSI YY REMARK ETA RF 11AUG14 BVVUUS 5982401074554C1
OSI YY REMARK ////SAC59888598016US-1MAGOMEDOVA/AMINAT MRS
OSI YY REMARK ETA RF 11AUG14 BVVUUS 5982401074555C1
OSI YY REMARK ////SAC59888598016V5-1RAMAZANOVA/SIYANA MRS
OSI YY CTC 89241964635
OSI YY REMARK TN/2401074554/HZ /59805141 /0551/E /-1MAGOMEDOVA
OSI YY REMARK ////AMINAT MRS
OSI YY REMARK TN/2401074555/HZ /59805141 /0551/E /-1RAMAZANOVA
OSI YY REMARK ////SIYANA MRS
OSI YY REMARK TN/2401074556/HZ /59805141 /0551/E /-1MAGOMEDOVA
OSI YY REMARK ////AMINAT MRS
OSI YY REMARK TN/2401074557/HZ /59805141 /0551/E /-1RAMAZANOVA
OSI YY REMARK ////SIYANA MRS
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T167C
OSI YY 23 POS/BVV001//BVV/HZ/A/RU""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


        PNR = """03   1.EPIFANTSEVA/RAISA ANDRIYAN 2.GALIMULINA/NADEZHDA YUREV VZJN4
04   3.   HZ 781  Y   FR05SEP  UUSOHH HK2   1030 1220
06   4.KHV/T G.KHABAROVSK AMURSKIY B-R 5
13   5.SSR TKNA HZ  HK1 UUSOHH0781Y05SEP.5986175627349/P1
13   6.SSR TKNA HZ  HK1 UUSOHH0781Y05SEP.5986175627350/P2
13   7.SSR TKTL HZ  SS/ MOW 0601/18APR
13   8.SSR DOCS HZ  HK1 /P/RUS/6401166392/RUS/01JAN41/F/31DEC49/EPIFANTSEVA/
13      RAISA ANDRIYAN/P1
13   9.SSR DOCS HZ  HK1 /P/RUS/6409715465/RUS/23AUG89/F/31DEC49/GALIMULINA/
13      NADEZHDA YUREV/P2
13  10.SSR TKTL HZ  SS/ MOW NOW TKTD
14  11.OSI HZ  CTCT 74212568521
14  12.OSI HZ  CTCH 74243721042-EPIFANTSEVA/RAISA ANDRIYAN
14  13.OSI HZ  CTCM 79146493416-EPIFANTSEVA/RAISA ANDRIYAN
14  14.OSI HZ  TRANZIT OKHA-YUZHKH-OVB RS S7-3504/0308
31  15.MOW1H /N3P4DW/08HBR/KHBRE40/TKP08KHBR0059"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 181812
MOW1H N3P4DW
1EPIFANTSEVA/RAISA ANDRIYAN
1GALIMULINA/NADEZHDA YUREV
HZ0781Y05SEP14 UUSOHH HK2/1030 1220
SSR TKNA HZ HK1 UUSOHH0781Y05SEP-1EPIFANTSEVA/RAISA
SSR TKNA HZ/// ANDRIYAN.5986175627349
SSR TKNA HZ HK1 UUSOHH0781Y05SEP-1GALIMULINA/NADEZHDA
SSR TKNA HZ/// YUREV.5986175627350
SSR DOCS HZ HK1 /P/RUS/6401166392/RUS/01JAN41/F/31DEC49/EPIFANTSEVA
SSR DOCS HZ////RAISA ANDRIYAN-1EPIFANTSEVA/RAISA ANDRIYAN
SSR DOCS HZ HK1 /P/RUS/6409715465/RUS/23AUG89/F/31DEC49/GALIMULINA
SSR DOCS HZ////NADEZHDA YUREV-1GALIMULINA/NADEZHDA YUREV
SSR TKTL HZ SS/ MOW NOW TKTD
OSI HZ CTCT 74212568521
OSI HZ CTCH 74243721042-EPIFANTSEVA/RAISA ANDRIYAN
OSI HZ CTCM 79146493416-EPIFANTSEVA/RAISA ANDRIYAN
OSI HZ TRANZIT OKHA-YUZHKH-OVB RS S7-3504/0308
OSI YY CTC KHV/T G.KHABAROVSK AMURSKIY B-R 5
OSI YY 23 AUTOMATIC IMPORT HDQ5N/VZJN4
OSI YY 23 POS/MOW1H /N3P4DW/08HBR/KHBRE40/TKP08KHBR0059""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


        PNR = """03   1.SMIRNOV/MIKHAIL MR T3Y6W
04   2.   HZ 801  Z   MO08SEP  UUSBVV HK1   1250 1410
06   3.89241969737
07   4.T/ *T
13   5.SSR CHLD HZ  HK1 /25SEP09/P1
13   6.SSR DOCS HZ  HK1 /P/RU/I+-+--+OT702140/RU/25SEP09/M//SMIRNOV/MIKHAIL/P1
13   7.SSR FOID HZ  HK1 PPSRIOT702140/P1
13   8.SSR PCTC HZ  HK/ SMIRNOV/MIKHAIL/79241969737/P1
13   9.SSR TKNE HZ  HK1 UUSBVV0801Z08SEP.5982401021969C1/P1
15  10.ETA BD 29MAY14 BVVUUS 5982401059063C1/P1
15  11.ETA RV 08SEP14 UUSBVV 5982401021969C1/P1
15  12.RMK S/MILITARY FARE
21  13.TN/2401059063/HZ /59805141 /0445/E //P1 A 07MAY14
21  14.TN/2401021969/HZ /59805152 /0599/E //P1 A 30MAY14
31  15.BVV001//BVV/HZ/A/RU"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 191551
MOW1H IMPORTT3Y6W
1SMIRNOV/MIKHAIL MR
HZ0801Z08SEP14 UUSBVV HK1/1250 1410
SSR CHLD HZ HK1 /25SEP09-1SMIRNOV/MIKHAIL MR
SSR DOCS HZ HK1 /P/RU/IOT702140/RU/25SEP09/M//SMIRNOV
SSR DOCS HZ////MIKHAIL-1SMIRNOV/MIKHAIL MR
SSR FOID HZ HK1 PPSRIOT702140-1SMIRNOV/MIKHAIL MR
SSR PCTC HZ HK/ SMIRNOV/MIKHAIL/79241969737-1SMIRNOV/MIKHAIL MR
SSR TKNE HZ HK1 UUSBVV0801Z08SEP-1SMIRNOV/MIKHAIL MR.5982401021969C1
OSI YY REMARK ETA BD 29MAY14 BVVUUS 5982401059063C1-1SMIRNOV/MIKHAIL
OSI YY REMARK /// MR
OSI YY REMARK ETA RV 08SEP14 UUSBVV 5982401021969C1-1SMIRNOV/MIKHAIL
OSI YY REMARK /// MR
OSI YY REMARK RMK S/MILITARY FARE
OSI YY CTC 89241969737
OSI YY REMARK TN/2401059063/HZ /59805141 /0445/E /-1SMIRNOV/MIKHAIL
OSI YY REMARK /// MR
OSI YY REMARK TN/2401021969/HZ /59805152 /0599/E /-1SMIRNOV/MIKHAIL
OSI YY REMARK /// MR
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T3Y6W
OSI YY 23 POS/BVV001//BVV/HZ/A/RU""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


    def test_svc_status(self):
        """
        Replace code HK to HI.

        HK code is not supported by sirena parser.
        """

        PNR = """03   1.OSANAI/MICHIKO MS T1660
04   2.   HZ 152  K   WE13AUG14CTSUUS RR1   1310 1630
06   3.H/011-778-1558
07   4.T/ *T
12   5.SVC HZ  HK1 SPK 13AUG14 /D/995/CANCELLATION FEE/NM-1OSANAI/MICHIKO MS
12      5984560039234C1.5982401060339 REFUND LESS THAN 24HOUR BEFORE DEPARTURE
12      /P1
13   6.SSR DOCS HZ  HK1 /P/JPN/TK0997544/JPN/19OCT38/F/25JAN20/OSANAI/MICHIKO
13      /P1
13   7.SSR FOID HZ  HK1 PPTK0997544/P1
15   8.ETA I 20AUG14 UUSCTS 5982401060339C2/P1
31   9.SPK001//SPK/HZ/A/JP"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 181019
MOW1H IMPORTT1660
1OSANAI/MICHIKO MS
HZ0152K13AUG14 CTSUUS RR1/1310 1630
SSR DOCS HZ HK1 /P/JPN/TK0997544/JPN/19OCT38/F/25JAN20/OSANAI
SSR DOCS HZ////MICHIKO-1OSANAI/MICHIKO MS
SSR FOID HZ HK1 PPTK0997544-1OSANAI/MICHIKO MS
OSI YY REMARK ETA I 20AUG14 UUSCTS 5982401060339C2-1OSANAI/MICHIKO
OSI YY REMARK /// MS
OSI YY CTC H/011-778-1558
SVC HZ HI1 SPK 13AUG14 /D/995/CANCELLATION FEE/NM-1OSANAI/MICHIKO MS
SVC HZ////5984560039234C1
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T1660
OSI YY 23 POS/SPK001//SPK/HZ/A/JP""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


    def test_tkn_asterisk(self):
        """
        Move SSR TKN* to SSR OTHS.
        """

        PNR = """03   1.NAKAJO/TOMOYUKIMR T3FMT
04   2.   HZ 151  T   WE27AUG  UUSCTS RR1   1300 1220
04   3.   JL 504  G   TH28AUG  CTSHND RR1   1000 1135
06   4.A/ALI TRAVEL 03-3376-1326 C/O MS.YAMAGATA
07   5.T/5982400492116 TKTD
13   6.SSR DOCS HZ  HK1 /P/JP/TH9418743/JP/09FEB64/M/27JUL19/NAKAJO/TOMOYUKI
13      /P1
13   7.SSR FQTV HZ  HK1 UUSCTS 0151T27AUG.HZ131798/P1
13   8.SSR TKNM HZ  HK1 UUSCTS 0151T27AUG.59824004921161/P1
13   9.SSR TKNM JL  HK1 CTSHND 0504G28AUG.59824004921161/P1
31  10.TYO001/00000000/TYO/HZ/N/JP"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 181618
MOW1H IMPORTT3FMT
1NAKAJO/TOMOYUKI MR
HZ0151T27AUG14 UUSCTS RR1/1300 1220
JL0504G28AUG14 CTSHND RR1/1000 1135
SSR DOCS HZ HK1 /P/JP/TH9418743/JP/09FEB64/M/27JUL19/NAKAJO
SSR DOCS HZ////TOMOYUKI-1NAKAJO/TOMOYUKI MR
SSR FQTV HZ HK1 UUSCTS 0151T27AUG.HZ131798-1NAKAJO/TOMOYUKI MR
SSR TKNM HZ HK1 UUSCTS 0151T27AUG-1NAKAJO/TOMOYUKI MR.59824004921161
SSR OTHS HZ SSR TKNM JL HK1 CTSHND 0504G28AUG-1NAKAJO/TOMOYUKI
SSR OTHS HZ/// MR.59824004921161
OSI YY CTC A/ALI TRAVEL 03-3376-1326 C/O MS.YAMAGATA
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T3FMT
OSI YY 23 POS/TYO001/00000000/TYO/HZ/N/JP""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])

        # second try
        PNR = """03   1.II/DAINA CHD(UM2) T3BG8
04   2.   HZ 151  K   SA25OCT  UUSCTS HK1   1830 1750
06   3.M/080-8295-5073/RODION MR
07   4.T/ *T
13   5.SSR CHLD HZ  HK1 /15JUN12/P1
13   6.SSR DOCS HZ  HK1 /P/RU/515540367/RU/15JUN12/F/11MAR18/II/DAINA/P1
13   7.SSR FOID HZ  HK1 PP515540367/P1
13   8.SSR TKNE HZ  HK1 UUSCTS0151K25OCT.5982401074914C2/P1
14   9.OSI HZ  TKT TYPE KEE3M
14  10.OSI HZ  T/W T3BDT
14  11.OSI HZ  T/W TBVW0
15  12.ETA RV 09AUG14 CTSUUS 5982401074914C1/P1
15  13.ETA RV 23AUG14 UUSCTS 5982401074914C2/P1
21  14.TN/2401074914/HZ /59801210A/0064/E //P1 A 30JUN14
31  15.SPK001//SPK/HZ/A/JP"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 181621
MOW1H IMPORTT3BG8
1II/DAINA CHD(UM2)
HZ0151K25OCT14 UUSCTS HK1/1830 1750
SSR CHLD HZ HK1 /15JUN12-1II/DAINA CHD(UM2)
SSR DOCS HZ HK1 /P/RU/515540367/RU/15JUN12/F/11MAR18/II/DAINA-1II
SSR DOCS HZ////DAINA CHD(UM2)
SSR FOID HZ HK1 PP515540367-1II/DAINA CHD(UM2)
SSR TKNE HZ HK1 UUSCTS0151K25OCT-1II/DAINA CHD(UM2).5982401074914C2
OSI HZ TKT TYPE KEE3M
OSI HZ T/W T3BDT
OSI HZ T/W TBVW0
OSI YY REMARK ETA RV 09AUG14 CTSUUS 5982401074914C1-1II/DAINA
OSI YY REMARK /// CHD(UM2)
OSI YY REMARK ETA RV 23AUG14 UUSCTS 5982401074914C2-1II/DAINA
OSI YY REMARK /// CHD(UM2)
OSI YY CTC M/080-8295-5073/RODION MR
OSI YY REMARK TN/2401074914/HZ /59801210A/0064/E /-1II/DAINA
OSI YY REMARK /// CHD(UM2)
OSI YY 23 AUTOMATIC IMPORT HDQ5N/T3BG8
OSI YY 23 POS/SPK001//SPK/HZ/A/JP""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


        # third try
        PNR = """03   1.MARCHENKO/YURIY TN4Q8
04   2.   HZ 782  Y   WE10SEP  OHHUUS HK1   1310 1510
04   3.   HZ 781  Y   TH25SEP  UUSOHH HK1   1030 1220
06   4.MOW/T 7495787-43-05 AGENCY TELETRAIN
06   5.MOW/T G.MOV PEREVEDENOVSKIY PR17
13   6.SSR TKNE HZ  HK1 OHHUUS0782Y10SEP.5986159207281C1/P1
13   7.SSR TKNE HZ  HK1 UUSOHH0781Y25SEP.5986159207281C2/P1
13   8.SSR TKTL HZ  SS/ MOW 0430/13AUG
13   9.SSR DOCS HZ  HK1 /P/RUS/6402380991/RUS/07JUL72/M/31DEC49 MARCHENKO/
13      YURIY/P1
13  10.SSR TKTL HZ  SS/ MOW 0359/14AUG
13  11.SSR TKTL HZ  SS/ MOW NOW TKTD
14  12.OSI HZ  CTCH 79147553703
14  13.OSI HZ  ERSP 92000506
15  14.ETA I 10SEP14 OHHUUS 5986159207281C1/P1
15  15.ETA I 25SEP14 UUSOHH 5986159207281C2/P1
31  16.MOW1H /P58D74/26MOV/VIPS26/TKP26MOV3766"""

        pnr = parse_pnr(PNR.split('\n'), self.settings)
        t = make_telegram(pnr, self.settings).split('\n')

        T = """MOWRM5N
.MOWRM1H 181734
MOW1H P58D74
1MARCHENKO/YURIY
HZ0782Y10SEP14 OHHUUS HK1/1310 1510
HZ0781Y25SEP14 UUSOHH HK1/1030 1220
SSR TKNE HZ HK1 OHHUUS0782Y10SEP-1MARCHENKO/YURIY.5986159207281C1
SSR TKNE HZ HK1 UUSOHH0781Y25SEP-1MARCHENKO/YURIY.5986159207281C2
SSR DOCS HZ HK1 /P/RUS/6402380991/RUS/07JUL72/M/31DEC49/MARCHENKO
SSR DOCS HZ////YURIY-1MARCHENKO/YURIY
SSR TKTL HZ SS/ MOW NOW TKTD
OSI HZ CTCH 79147553703
OSI HZ ERSP 92000506
OSI YY REMARK ETA I 10SEP14 OHHUUS 5986159207281C1-1MARCHENKO/YURIY
OSI YY REMARK ETA I 25SEP14 UUSOHH 5986159207281C2-1MARCHENKO/YURIY
OSI YY CTC MOW/T 7495787-43-05 AGENCY TELETRAIN
OSI YY CTC MOW/T G.MOV PEREVEDENOVSKIY PR17
OSI YY 23 AUTOMATIC IMPORT HDQ5N/TN4Q8
OSI YY 23 POS/MOW1H /P58D74/26MOV/VIPS26/TKP26MOV3766""".split('\n')

        self.assertEqual(t[0], T[0])
        self.assertEqual(t[1][:9], T[1][:9]) # datetime changes every time.
        self.assertEqual(t[2:], T[2:])


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPnrParse)
    unittest.TextTestRunner(verbosity=2).run(suite)
