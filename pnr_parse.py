import re
import os
import sys
import logging
import optparse

from datetime import datetime

from pnr_types import *
from pnr_utils import *


################################################################################
# UTILS
################################################################################

def guess_paxnum(raw_pnr, where):
    """
    Guess paxnum for passenger in some pnr object when `/P` occurred and
    paxnum has been forgoten.

    Its work correct if one passenger in order only.
    """
    if raw_pnr and \
       (
           (raw_pnr["name"] and len(raw_pnr["name"]) == 1) or
           (raw_pnr["group_name"] and len(raw_pnr['group_name']) == 1 and \
            group_name_size(raw_pnr["group_name"][0]) == 1)
       ):
        return "1"

    raise PnrParseException("can't guess paxnum in '{0}'".format(where))


def pass_in_group(name, surname, raw_pnr):
    """
    Check if pass with `name` and `surname` in group.
    """
    assert surname is not None, "no surname for pass! {0}".format(raw_pnr)

    passname = "/".join([surname, name]) if name is not None else surname
    if raw_pnr and raw_pnr["group_name"]:
        for record in raw_pnr["name"]:
            if passname in record:
                return True

    return False


def cut_regnum_from_pax(text):
    """
    Cut regnum from last pax in pax list.
    """
    pass_data = text.split()

    return " ".join(pass_data[:-1]), pass_data[-1]


def cut_regnum(raw_pnr):
    """
    Cut regnum from group or paxes in raw pnr.

    This regnum goes to raw pnr dictionary element.
    """
    REGNUM_LEN = 5

    regnum = None
    for name in ('group_name', 'name'):
        if raw_pnr.get(name):
            raw_pnr[name][-1], regnum = cut_regnum_from_pax(raw_pnr[name][-1])
            break;

    assert regnum is not None, \
        "something wrong! i can't find regnum!\n%s" % raw_pnr
    assert len(regnum) == REGNUM_LEN, \
        "wrong regnum {0} length: {1}!".format(regnum, len(regnum))

    raw_pnr['regnum'] = regnum

    return raw_pnr


def init_raw_pnr():
    """
    Create raw empty pnr with empty lists of each object.
    """
    d = {}
    for field in PNR_OBJS:
        d[field] = []

    return d


def combine_fields(record):
    """
    Concatenates string fields of objects.
    """
    def get_code(line):
        for name, value in PNR_OBJS.items():
            if line[:2] == value.code:
                return name

        raise PnrParseException("wrong code in line: '%s'" % line)


    def parse_paxes(line):
        return (s.strip() for s in re.split("\s*[0-9]{1,2}\.", line) if s.strip())


    def is_continued(line):
        return '.' not in line.lstrip()[:4]


    def is_passengers(code):
        return code == 'name'


    d = init_raw_pnr()

    for line in record:
        code = get_code(line)
        line = line[2:]

        if is_continued(line):
            line = line.lstrip()
            if line and line[0] == '/' or d[code][-1][-1] == '/':
                line = line
            else:
                line = ' ' + line

            d[code][-1] += line
        else:
            if is_passengers(code):
                [d[code].append(l) for l in parse_paxes(line[2:]) if l]
            else:
                dot = line.find('.') + 1
                without_line_num = line[dot:].strip()
                d[code].append(without_line_num)

    return d


def parse_raw_pnr(record):
    """
    Parses raw PNR from `record` string.

    On output - lists of objects string representation.
    """
    return cut_regnum(combine_fields(record))


def get_depdate(s, settings):
    if not s:
        return None

    if len(s) == 9:
        f = '%d%b%y'
        fixed_date = s[2:]
    elif len(s) == 7:
        if s[:2].isdigit():
            f = '%d%b%y'
            fixed_date = s
        else:
            f = '%d%b%Y'
            fixed_date = s[2:] + settings.current_year
    elif len(s) == 5:
        f = '%d%b%Y'
        fixed_date = s + settings.current_year
    else:
        raise PnrParseException('Wrong depdate: {0}'.format(s))

    return datetime.strptime(fixed_date, f).date()


################################################################################
# MAIN PARSE FUNCTIONS
################################################################################

def parse_pax(text, raw_pnr, settings):
    m = re.search((r"^\s*(?P<surname>[^/]+)"
                   "(?:/(?P<name>.*?)\s*"
                   "(?:(?P<status>(?:MISS|MS|MRS|MSS|"
                                    "CHD|CHLD|CH|"
                                    "INF|INFT|"
                                    "MSTR|MR)))?)?$"), text)
    if not m:
        raise PnrParseException("can't parse pax: '{0}'".format(text))

    return Pax(name = m.group("name"),
               surname = m.group("surname"),
               status = m.group("status"),
               nseats = 1,
               group = pass_in_group(name = m.group("name"),
                                     surname = m.group("surname"),
                                     raw_pnr = raw_pnr))


def parse_ssr(text, raw_pnr, settings):
    m = re.search((r"^SSR\s+(?P<code>[^\s]+)\s+"
                   "(?P<airline>[^\s]+)\s+"
                   "(?:(?P<status>[^\d]{1,3})(?P<nseats>[\d]{1})?)?"
                   "\s+(?P<text>.*?)"
                   "(?:(?P<slashp>/P)(?P<paxnum>[\d]{1,2})?)?$"), text)
    if not m:
        raise PnrParseException("can't parse ssr: '{0}'".format(text))

    paxnum = m.group("paxnum")
    if (m.group("slashp") and not paxnum):
        paxnum = guess_paxnum(raw_pnr, text)

    return Ssr(code = m.group("code").strip(),
               airline = m.group("airline"),
               status = m.group("status"),
               nseats = m.group("nseats"),
               text = m.group("text").strip(),
               paxnum = paxnum)


def parse_itin(text, raw_pnr, settings):
    m = re.search((r"^\s*(?P<airline>[^\s]+)"
                   "\s+(?P<flightnum>[^\s]+)"
                   "\s+(?P<itin_class>[^\s]{1})\s+"
                   "(?P<depdate>[^\s]{7,9})?"
                   "\s*(?P<deppoint>[^\s]{3})(?P<arrpoint>[^\s]{3})?"
                   "(?:\s+(?P<status>[^\s]{2}))?"
                   "(?P<nseats>[^\s]+)?"
                   "(?:\s+(?P<deptime>[^\s]+))?"
                   "(?:\s+(?P<arrtime>[^\sa-zA-Z]+))?"
                   "\s*(?P<text>.*?)?$"), text)

    if not m and text.startswith('ARNK'):
        return Itin(airline = None,
                    flightnum = None,
                    itin_class = None,
                    depdate = None,
                    deppoint = None,
                    arrpoint = None,
                    status = None,
                    nseats = None,
                    deptime = None,
                    arrtime = None,
                    text = 'ARNK')

    if not m:
        raise PnrParseException("can't parse itin: '{0}'".format(text))

    return Itin(airline = m.group("airline"),
                flightnum = m.group("flightnum"),
                itin_class = m.group("itin_class"),
                depdate = get_depdate(m.group("depdate"), settings),
                deppoint = m.group("deppoint"),
                arrpoint = m.group("arrpoint"),
                status = m.group("status"),
                nseats = m.group("nseats"),
                deptime = m.group("deptime"),
                arrtime = m.group("arrtime"),
                text = m.group("text"))


def parse_osi(text, raw_pnr, settings):
    m = re.search((r"^OSI\s+(?:\#\d+\s+)?(?P<airline>[^\s]+)\s+"
                   "(?P<text>.*?)"
                   "(?:(?P<slashp>/P)(?P<paxnum>[\d]{1,2})?)?$"), text)

    # m = re.search((r"^OSI\s+(?P<airline>[^\s]+)\s+"
    #                "(?P<text>.*?)"
    #                "(?:(?P<slashp>/P)(?P<paxnum>[\d]{1,2})?)?$"), text)

    if not m:
        raise PnrParseException("can't parse osi: {0}".format(text))

    paxnum = m.group("paxnum")
    if (m.group("slashp") and not paxnum):
        paxnum = guess_paxnum(raw_pnr, text)

    return Osi(airline = m.group('airline').strip(),
               text = m.group('text').strip(),
               paxnum = paxnum)


def parse_remarks(text, raw_pnr, settings):
    m = re.search(r'^(?P<text>.+?)(?:(?P<slashp>/P)(?P<paxnum>[\d]{1,2})?)?$', text)

    if not m:
        raise PnrParseException("can't parse remarks: '{0}'".format(text))

    paxnum = m.group("paxnum")
    if (m.group("slashp") and not paxnum):
        paxnum = guess_paxnum(raw_pnr, text)

    return Remarks(text = m.group('text').strip(),
                   paxnum = paxnum)


def parse_contacts(text, raw_pnr, settings):
    return Contact(text)


def parse_responsibility(text, raw_pnr, settings):
    return Responsibility(text)


def parse_endorsement(text, raw_pnr, settings):
    m = re.search(r'^(?P<text>.+?)'
                  '(?:/P(?P<paxnum>[\d]{1,2}))?'
                  ' [^/]+$', text)

    if not m:
        raise PnrParseException('wrong endorsement: {0}'.format(text))

    return Endorsement(text = m.group('text').strip(),
                       paxnum = m.group("paxnum"))


def parse_auxiliary(text, raw_pnr, settings):
    m = re.search(r'^SVC\s+(?P<airline>[^\s]+)\s+'
                  '(?:(?P<status>[^\d]{1,3})(?P<nseats>[\d]{1})?)?\s+'
                  '(?P<primary_loc_code>[^\s]{3})(?P<secondary_loc_code>[^\s]{3})?\s+'
                  '(?P<service_date>[^\s]{5,7})\s+'
                  '(?P<text>.+?)'
                  '\..*?'
                  '(?:(?P<slashp>/P)(?P<paxnum>[\d]{1,2})?)?$', text)

    if not m:
        raise PnrParseException("can't parse auxiliary(SVC): '{0}'".format(text))

    paxnum = m.group("paxnum")
    if (m.group("slashp") and not paxnum):
        paxnum = guess_paxnum(raw_pnr, text)

    return Auxiliary(airline = m.group('airline'),
                     status = m.group('status'),
                     nseats = m.group('nseats'),
                     primary_loc_code = m.group('primary_loc_code'),
                     secondary_loc_code = m.group('secondary_loc_code'),
                     service_date = get_depdate(m.group('service_date'), settings),
                     text = m.group('text'),
                     paxnum = paxnum)


def parse_group(text, raw_pnr, settings):
    m = re.search(r'^\s*(?P<total>[0-9]+)?'
                  '(?P<group_1>.+?)(?:/(?P<group_2>.+?))?'
                  '\s+NM(?P<named>[0-9]+)$', text)

    if not m:
        raise PnrParseException("can't parse group: '{0}'".format(text))

    group = None
    if m.group('group_1') == 'GRP':
        group = m.group('group_2')
    else:
        group = m.group('group_1')

    return Group(total = m.group('total'),
                 name = group,
                 named = m.group('named'))


def parse_objs(field_value, raw_pnr, settings, fn):
    """
    Parses PNR objects from a list of objects string representation.
    """
    if not field_value:
        return None

    l = []
    l_append = l.append

    for text in field_value:
        try:

            l_append(fn(text, raw_pnr, settings))

        except PnrParseException as e:
            logging.warning(
                "{0}\n"
                "Parse PNR exception.\n"
                "PNR: {1}\nException: {2}\n"
                "{3}\n\n".format('-' * 80, raw_pnr['regnum'], e, '-' * 80))

    return l


def collect_pnr(raw_pnr, settings):
    """
    Create PNR from text presentation of elements.

    If on of elements throw an exception when created, skip this element.
    """
    pnr = init_raw_pnr()
    pnr['regnum'] = raw_pnr['regnum']
    handled_keys = PNR_OBJS.keys()

    for field, value in raw_pnr.items():
        if field not in handled_keys:
            continue

        fn = PNR_OBJS[field].fn

        if not fn:
            continue

        pnr[field] = parse_objs(value, raw_pnr, settings, fn)


    return pnr


def parse_pnr(record, settings):
    """
    Module entrance.
    """
    return collect_pnr(parse_raw_pnr(record), settings)


PNR_OBJS = {
    "update":                  CodeFn('01', None),
    "group_name":              CodeFn('02', parse_group),
    "name":                    CodeFn('03', parse_pax),
    "segment":                 CodeFn('04', parse_itin),
    "group":                   CodeFn('05', None),
    "contact":                 CodeFn('06', parse_contacts),
    "ticket_status":           CodeFn('07', None),
    "fare_calculation":        CodeFn('08', None),
    "mailing_address":         CodeFn('09', None),
    "billing_address":         CodeFn('10', None),
    "fares":                   CodeFn('11', None),
    "auxiliary_service":       CodeFn('12', parse_auxiliary),
    "ssr":                     CodeFn('13', parse_ssr),
    "osi":                     CodeFn('14', parse_osi),
    "remarks":                 CodeFn('15', parse_remarks),
    "guest_comments":          CodeFn('16', None),
    "fare_box":                CodeFn('17', None),
    "tour_code":               CodeFn('18', None),
    "original_issue":          CodeFn('19', None),
    "ticket_number":           CodeFn('20', None),
    "endorsement_information": CodeFn('21', parse_endorsement),
    "form_of_payment":         CodeFn('22', None),
    "supplementary_name":      CodeFn('23', None),
    "ticketing_data":          CodeFn('24', None),
    "responsibility":          CodeFn('31', parse_responsibility),
}
