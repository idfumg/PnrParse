"""
Module for create airimp telegram from pnr objects and settings.
"""

import logging

from datetime import datetime

from pnr_types import *
from pnr_utils import *


def find_pax(pnr, paxnum):
    """
    Pax number is paxnum - 1 because paxes stored in list.
    """
    paxes = pnr["name"]
    if len(paxes) < int(paxnum):
        return None

    return paxes[int(paxnum) - 1]


def guess_pax(pnr):
    """
    GUESS PAX IF IT MANDATORY AND ONLY ONE PASSENGER IN ORDER.
    """
    def first_pax():
        pnr_name = pnr['name']
        if pnr_name and len(pnr_name) == 1:
            return pnr_name[0]

    return first_pax()


def split_elem(text, head, width = 69, preffix = '///'):
    """
    Split SSR by line `width` with `preffix` on new line.
    """
    l = len(text)
    if l < width:
        return text

    lhead = len(head) + len(preffix)
    if lhead > width / 2:
        logging.error("invalid ssr head: '{0}'".format(head))

    ind = 0
    ind_prev = 0
    dx1 = 0
    for i in range(l):
        dx1 = ind
        dx2 = width + ind
        if i > 0:
            dx2 -= lhead

        slash = text.rfind('/', dx1 + lhead, dx2)
        space = text.rfind(' ', dx1 + lhead, dx2)
        ind = max(slash, space)
        if ind == -1:
            ind = dx2
        if dx2 > l and (lhead + ind - ind_prev) <= width:
            ind = dx2

        # logging.info('i = %d, ind = %d, dx1 = %d, dx2 = %d, text[dx1:dx2]=[%s]' % (i, ind, dx1, dx2, text[dx1:dx2]))

        if i == 0:
            res = text[dx1:ind]
        else:
            res += '\n' + head + preffix + text[ind_prev:ind]

        ind_prev = ind
        if dx2 > l:
            break

    return res


def output_group_name(group, pnr, settings):
    """
    Output <num><group_name> if it's a group PNR and has no paxes.
    Output <`unnamed seats number`><group_name> if free seats exists.

    Group contains total seats and some named seats.

    Example:

    `0.22SOTSZSHITA/GRP NM3 TE252`
    `1.CHURBANOV/STEPAN MR 2.DARENKOVA/MARINA MRS 3.EGOROV/NIKITA MR`
    """
    def no_paxes():
        """
        Order have no paxes.
        """
        return not pnr['name'] or len(pnr['name']) == 0


    def named_seats():
        """
        Returns named seats in group.
        """
        nseats = 0
        for pax in pnr['name']:
            nseats += pax.nseats

        return nseats


    if no_paxes():
        return group.total + group.name

    nseats = named_seats()

    if int(group.total) > nseats:
        return str(int(group.total) - nseats) + group.name

    return None


def output_pax(pax, pnr, settings):
    """
    Output passenger data like `1IVANOV/VITALIY VLADIMIROVICH MR`.

    Where:
    1 - seats count.
    IVANOV - surname.
    VITALIY VLADIMIROVICH- name (optional).
    MR - class (optional).

    Passengers can be belong to group.
    """
    def name():
        """
        Compose a pax name.
        """
        out = []
        out_append = out.append
        out_append(pax.surname)

        if pax.name:
            out_append('/' + pax.name)

        if pax.status:
            out_append(' ' + pax.status)

        return ''.join(out)


    return str(pax.nseats) + name()


def output_itin(itin, pnr, settings):
    """
    Output itinerary data like `AC0003C09JUN14 YVRNRT HK1/1210 1425/1`.

    Where:
    AC - airline carrier.
    0003 - flight number.
    C - class.
    09JUN14 - departure date.
    YVR - departure point.
    NRT - arrival point.
    HK - current status.
    1 - seats count.
    1210 - departure time.
    1425 - arrival time.
    /1 - plus a day.

    Note:
    /M1 - minus a day.
    """
    def skip_itin():
        """
        Some ITIN skip conditions.
        """
        return itin.status == 'UN'


    def fix_status(status):
        """
        Some predefined fix status conditions.
        """
        if status in ['NK', 'KK', 'NS']:
            return 'HK'

        return status


    def fix_arrtime(arrtime):
        """
        Fix raw arrival time format to TCH format for SIRENA.
        """
        arrtime = arrtime.replace('+', '/')
        arrtime = arrtime.replace('-', '/M')

        return arrtime


    def guess_nseats():
        """
        Try to guess nseats if current ITINERARY does not have one.
        """
        for itin in pnr['segment']:
            if itin.nseats:
                return itin.nseats

        if pnr['name'] and len(pnr['name']) == 1:
            return '1'

        raise PnrParseException("Unknown segment nseats: '{0}'".format(itin))


    if skip_itin():
        return None

    if itin.text == 'ARNK':
        return 'ARNK'

    out = []
    out_append = out.append
    out_append(itin.airline)
    out_append(itin.flightnum.zfill(4))
    out_append(itin.itin_class)

    if itin.depdate:
        out_append(datetime.strftime(itin.depdate, '%d%b%y').upper())

    out_append(' ')
    out_append(itin.deppoint)
    out_append(itin.arrpoint)
    out_append(' ')

    open_date = not itin.depdate or itin.flightnum == 'OPEN'

    if open_date:
        return ''.join(out)

    if not itin.status:
        out_append('HK')

        if settings.airline == itin.airline:
            logging.error("Unknown segment status code: "
                          "'{0}'".format(itin))
    else:
        out_append(fix_status(itin.status))

    if itin.nseats:
        out_append(itin.nseats)
    else:
        out_append(guess_nseats())

    if itin.deptime:
        out_append('/')
        out_append(itin.deptime)
        out_append(' ')
        out_append(fix_arrtime(itin.arrtime))

    if itin.airline == settings.airline:
# fixme
# Code Share
        pass

    return ''.join(out)


def output_ssr(ssr, pnr, settings, need_split = True):
    """
    Output SSR data.

    Data will be splitted for width of line like if need:
    `SSR DOCS UT HK1/P/RUS/7777777777/RUS/12MAY65/M/31DEC49/СОКОЛОВ/ИВАН`
    `SSR DOCS UT///ПЕТРОВИЧ-1СОКОЛОВ/ИВАН ПЕТРОВИЧ`

    SSR codes: 'TKNE', 'TKNM', 'TKNA', 'INFT' must have pax link.
    """
    def skip_ssr():
        """
        SSR skip conditions.
        """
        return ssr.status == 'XX'


    def head():
        """
        Gives a head of SSR.

        This head occuried in each line of splitted SSR.
        """
        return 'SSR' + ' ' + ssr.code + ' ' + ssr.airline


    def make_default(pax):
        """
        Make default SSR body. Pax may be ommited.
        """
        out = []
        out.append(ssr.text)

        if pax:
            out.append('-')
            out.append(output_pax(pax, pnr, settings))

        return ''.join(out)


    def make_automated(pax):
        """
        Make automated SSR body. Pax is mandatory.
        """
        if not pax:
            pax = guess_pax(pnr)

        out = []

        dot = ssr.text.find('.')
        if dot < 0:
            raise PnrParseException("unable to find a dot in an automated " \
                                    "ssr text: '{0}'".format(ssr.text))

        out.append(ssr.text[:dot])
        out.append('-')
        out.append(output_pax(pax, pnr, settings))
        out.append(ssr.text[dot:])

        return ''.join(out)


    if skip_ssr():
        return None

    if ssr.code == 'PSPT':
        splitted = ssr.text.split('/')
        if len(splitted) < 7:
            raise PnrParseException("Invalid ssr `PSPT`: '{0}'".format(ssr.text))

    out = []
    out_append = out.append
    out_append(head())

    if ssr.status:
        out_append(' ')
        out_append(ssr.status)

    if ssr.nseats:
        out_append(ssr.nseats)

    out_append(' ')

    pax = None
    if ssr.paxnum:
        pax = find_pax(pnr, ssr.paxnum)
        if not pax:
            raise PnrParseException("pax did not found is ssr: '{0}'".format(ssr))

    if ssr.code in ('TKNE', 'TKNM', 'TKNA', 'INFT'):
        out_append(make_automated(pax))
    else:
        out_append(make_default(pax))

    if need_split == True:
        return split_elem(''.join(out), head())
    return ''.join(out)


def output_osi(osi, pnr, settings, code_modifier = ''):
    def skip_osi():
        """
        Osi skip conditions.
        """
        return osi.airline == '#1'


    def head():
        """
        Gives a head of OSI.

        This head occuried in each line of splitted SSR.
        """
        out = 'OSI' + ' ' + osi.airline + ' '
        if code_modifier:
            out += code_modifier + ' '

        return out


    if skip_osi():
        return None

    out = []
    out_append = out.append
    out_append(head())
    out_append(osi.text)

    pax = None
    if osi.paxnum:
        pax = find_pax(pnr, osi.paxnum) or guess_pax(pnr)
        if not pax:
            raise PnrParseException("pax did not found in osi: '{0}'".format(osi))

    if pax:
        out_append('-')
        out_append(output_pax(pax, pnr, settings))

    return split_elem(''.join(out), head())


def output_remarks(remarks, pnr, settings):
    """
    Output OSI remarks fields.
    """
    osi = Osi(airline = 'YY',
              text = remarks.text,
              paxnum = remarks.paxnum)

    return output_osi(osi, pnr, settings, code_modifier = 'REMARK')


def output_contact(contact, pnr, settings):
    """
    Output OSI contact fields.
    """
    osi = Osi(airline = 'YY',
              text = contact.text,
              paxnum = None)

    return output_osi(osi, pnr, settings, code_modifier = 'CTC')


def output_endorsement(endorsement, pnr, settings):
    """
    Output endorsement OSI.
    """
    osi = Osi(airline = 'YY',
              text = endorsement.text,
              paxnum = endorsement.paxnum)

    return output_osi(osi, pnr, settings, code_modifier = 'REMARK')


def output_auxiliary(svc, pnr, settings):
    """
    Output auxiliary SVC.
    """
    def head():
        out = ['SVC ']
        out.append(svc.airline)

        return ''.join(out)


    def check_format(t):
        m = re.search(r'^/.{1}/.{3,15}/.{1,30}/NM-.+/.+/?\s*.+C.+$', t)

        if not m:
            logging.warning('wrong svc text: {0}'.format(t))


    def skip():
        return svc.status == 'XX'


    check_format(svc.text)

    if skip():
        return

    out = []
    out_append = out.append
    out_append(head())
    out_append(' ')
    out_append(svc.status)
    out_append(svc.nseats)
    out_append(' ')
    out_append(svc.primary_loc_code)

    if svc.secondary_loc_code:
        out_append(' ')
        out_append(svc.secondary_loc_code)

    out_append(' ')
    out_append(datetime.strftime(svc.service_date, '%d%b%y').upper())
    out_append(' ')
    out_append(svc.text)

    return split_elem(''.join(out), head())


def output_automatic(pnr, settings):
    """
    Output manual created automatic OSI.
    """
    out = []
    out_append = out.append
    out_append('23 AUTOMATIC IMPORT ')
    out_append(settings.pred_point)
    out_append('/')
    out_append(pnr['regnum'])

    osi = Osi(airline = 'YY',
              text = ''.join(out),
              paxnum = None)

    return output_osi(osi, pnr, settings)


def output_responsibility(pnr, settings):
    """
    Output manual created responsibility OSI.
    """
    if not pnr['responsibility']:
        return None

    responsibility = pnr['responsibility'][0].text

    osi = Osi(airline = 'YY',
              text = '23 POS/' + responsibility,
              paxnum = None)

    return output_osi(osi, pnr, settings)


def output_dest_addr(pnr, settings):
    """
    Output destination address in pnr header.
    """
    return settings.dest_addr


def output_src_addr(pnr, settings):
    """
    Output source address and current time in pnr header.
    """
    out = []
    out_append = out.append
    out_append('.')

    if pnr['remote_pnr']:
        out_append(pnr['remote_system'][:3])
        out_append('RM')
        out_append(pnr['remote_system'][3:])
    else:
        out_append('MOWRM1H')

    out_append(' ')
    out_append(datetime.now().strftime('%d%H%M'))

    return ''.join(out)


def output_booking_office(pnr, settings):
    """
    Output booking office.
    """
    if pnr['remote_pnr']:
        return pnr['remote_system'] + ' ' + pnr['remote_pnr']

    return 'MOW1H IMPORT' + pnr['regnum']


def fix_group(pnr, settings):
    """
    Add a group ssr to the pnr if it is a group pnr and have no a group ssr.
    """
    def has_group_ssr():
        """
        Check that pnr has no group ssr.
        """
        pnr_ssr = pnr['ssr']

        if not pnr_ssr:
            return False

        for ssr in pnr_ssr:
            if ssr.code == 'GRPS':
                return True

        return False


    if has_group_ssr():
        return pnr, None

    pnr_group_name = pnr['group_name']
    if not pnr_group_name or len(pnr_group_name) == 0:
        return pnr, None

    group = pnr_group_name[0]

    ssr = Ssr(code = 'GRPS',
              airline = 'YY',
              status = 'TCP',
              nseats = group.total,
              text = group.name,
              paxnum = None)

    if not pnr['ssr']:
        pnr['ssr'] = [ssr]
    else:
        pnr['ssr'].append(ssr)


    return pnr, None


def find_remote_data(text, settings):
    """
    Guess either this pnr is remote or local booking.
    And return remote pnr if exists.
    """
    m = re.search((r'^(?P<system>[^/]+)(/(?P<pnr>[^/]+)?/?.*?)?$'), text)

    if not m:
        raise PnrParseException('Wrong responsibility: {0}'.format(text))

    remote_system = m.group('system').strip()
    remote_pnr = m.group('pnr')

    if remote_pnr == '00000000':
        remote_pnr = None

    if settings.local_systems and remote_system in settings.local_systems:
        remote_pnr = None

    return remote_system, remote_pnr


def fix_responsibility(pnr, settings):
    """
    Detect remote or local system and fetch corresponding data.
    """
    responsibility = pnr['responsibility'][0].text
    pnr['remote_system'], pnr['remote_pnr'] = \
        find_remote_data(responsibility, settings)


    return pnr, None


def fix_osi(pnr, settings):
    def remove_osi_from_pnr(o, pnr):
        """
        Find and remove osi from pnr osis list.
        """
        pnr_osi = pnr['osi']
        for i, osi in enumerate(pnr_osi):
            if osi == o:
                del pnr_osi[i]
                return

    pnr_osi = pnr['osi']
    pnr_ssr = pnr['ssr']

    if not pnr_osi or not pnr_ssr:
        return pnr, None

    osis = [osi for osi in pnr_osi if 'INF ' in osi.text]
    ssrs = [ssr for ssr in pnr_ssr if ssr.code == 'INFT']

    if not osis or not ssrs:
        return pnr, None

    for osi in osis:
        if any(ssr for ssr in ssrs if ssr.paxnum == osi.paxnum):
            remove_osi_from_pnr(osi, pnr)


    return pnr, None


def fix_ssr(pnr, settings):
    def tktl_find_pos(ssrs):
        for i, ssr in enumerate(ssrs):
            if ssr.code == 'TKTL':
                return i


    def tkn_find_pos(ssrs):
        for i, ssr in enumerate(ssrs):
            if ssr.code.startswith('TKN') and ssr.airline != settings.airline:
                return i


    def remove_tktl(ssrs):
        count = len([ssr for ssr in ssrs if ssr.code == 'TKTL'])

        while count > 1:
            i = tktl_find_pos(ssrs)

            del ssrs[i]
            count -= 1


    def fix_child(ssrs):
        if not settings.airline:
            return

        for i, ssr in enumerate(ssrs):
            if ssr.code == 'CHLD' and ssr.airline != settings.airline:
                ssrs[i] = Ssr(code = ssr.code,
                              airline = settings.airline,
                              status = ssr.status,
                              nseats = ssr.nseats,
                              text = ssr.text,
                              paxnum = ssr.paxnum)


    def fix_tkn(ssrs):
        if not settings.airline:
            return

        tkn = tkn_find_pos(ssrs)
        while(tkn is not None):
            ssr_text = output_ssr(ssrs[tkn], pnr, settings, need_split = False)

            if not ssr_text:
                del ssrs[tkn]
            else:
                ssrs[tkn] = Ssr(code = 'OTHS',
                                airline = settings.airline,
                                status = None,
                                nseats = None,
                                text = ssr_text,
                                paxnum = None)

            tkn = tkn_find_pos(ssrs)


    def fix_docs(ssrs):
        def fix_date_to(text):
            count = 0
            found = text.find('/')
            while found is not None and count < 6:
                found = text.find('/', found + 1)
                count += 1

            found2 = text.find('/', found + 1)
            if found2 is not None:
                t = text[found + 1:found2]
                if len(t) > 7 and ' ' in t:
                    text = text[:found + 8] + '/' + text[found + 9:]

            return text


        for i, ssr in enumerate(ssrs):
            if ssr.code == 'DOCS':
                text = fix_date_to(ssr.text.replace('-', '').replace('+', ''))

                ssrs[i] = Ssr(code = ssr.code,
                              airline = ssr.airline,
                              status = ssr.status,
                              nseats = ssr.nseats,
                              text = text,
                              paxnum = ssr.paxnum)


    if not 'ssr' in pnr or not pnr['ssr']:
        return pnr, None

    ssrs = pnr['ssr']

    fixes = [
        remove_tktl,
        fix_child,
        fix_tkn,
        fix_docs
    ]

    for fix in fixes:
        fix(ssrs)

    return pnr, None


def fix_not_allowed_airline(pnr, settings):
    if not pnr:
        return None, None

    if not settings.airline:
        return pnr, None

    itins = pnr['segment']

    airline_itins = [itin for itin in itins if itin.airline == settings.airline]

    if not airline_itins:
        return None, 'no "{0}" itin'.format(settings.airline)

    return pnr, None


def fix_pass_name(pnr, settings):
    if not pnr:
        return None, None

    if not 'name' in pnr or pnr['name'] is None:
        return pnr, None

    paxes = pnr['name']

    for pax in paxes:
        if pax.surname and (pax.name is None or pax.name == ''):
            return None, 'no pass name: {0}'.format(pax.surname)

    return pnr, None


def fix_svc(pnr, settings):
    if not 'auxiliary_service' in pnr or pnr['auxiliary_service'] is None:
        return pnr, None

    svcs = pnr['auxiliary_service']

    for i, svc in enumerate(svcs):
        text = svc.text
        if text[-16] != '/':
            text = text[:-16].rstrip() + '/' + text[-16:].lstrip()

        status = svc.status
        if status == 'HK':
            status = 'HI'

        svcs[i] = Auxiliary(airline = svc.airline,
                            status = status,
                            nseats = svc.nseats,
                            primary_loc_code = svc.primary_loc_code,
                            secondary_loc_code = svc.secondary_loc_code,
                            service_date = svc.service_date,
                            text = text,
                            paxnum = svc.paxnum)


    return pnr, None


def fix_pnr(pnr, settings):
    """
    Apply some changes to pnr before processing.
    """
    fixes = [
        fix_group,
        fix_responsibility,
        fix_osi,
        fix_ssr,
        fix_svc,
        fix_not_allowed_airline,
        fix_pass_name
    ]

    for fix in fixes:
        pnr, err = fix(pnr, settings)

        if not pnr:
            return pnr, err

    return pnr, None


def output_elems(elems, pnr, settings, fn):
    """
    Generic function for output pnr elements like pnr['segment'].

    All output functions get the same parameters.
    """
    if not elems:
        return None

    out = []
    out_append = out.append

    for elem in elems:
        if not elem:
            continue

        r = fn(elem, pnr, settings)

        if r:
            out_append(r)

    return '\n'.join(out)


def output_pnr(pnr, settings):
    """
    Prints all elements for each pnr data type in fixed order (PNR_OBJS).
    """
    out = []

    try:

        regnum = pnr['regnum']
        pnr, text = fix_pnr(pnr, settings)

        if not pnr:
            if settings.ignored:
                settings.ignored.write('Regnum: {0} Reason: {1}\n'.format(regnum, text))
            return None

        out_append = out.append
        [out_append(fn(pnr, settings)) for key, fn in MANUAL_BEFORE if fn]

        for key, fn in PNR_OBJS:
            if not fn:
                continue

            if key not in pnr:
                continue

            r = output_elems(pnr[key], pnr, settings, fn)

            if r:
                out_append(r)

        [out_append(fn(pnr, settings)) for key, fn in MANUAL_AFTER if fn]

    except PnrParseException as e:
        logging.warning(
            "{0}\n"
            "Create telegram exception.\n"
            "PNR: {1}\nException: {2}\n"
            "Called function: {4}"
            "{3}\n\n".format('+' * 80, pnr['regnum'], e, '+' * 80, key))

    return '\n'.join(out)


def make_telegram(pnr, settings):
    """
    Module entrance.
    """
    return output_pnr(pnr, settings)


"""
This structures reflect output telegram module logic.

MANUAL_BEFORE - a couple of functions to call before output pnr objects.
MANUAL_AFTER - a couple of functions to call after output pnr objects.
PNR_OBJS - functions for output pnr objects like `SSR`, `OSI` e.t.c.
"""

MANUAL_BEFORE = [
    ("output_destination_address", output_dest_addr),
    ("output_source_address", output_src_addr),
    ("output_booking_office", output_booking_office)
]


PNR_OBJS = [
    ("group_name",              output_group_name),
    ("name",                    output_pax),
    ("segment",                 output_itin),
    ("ssr",                     output_ssr),
    ("osi",                     output_osi),
    ("remarks",                 output_remarks),
    ("contact",                 output_contact),
    ("endorsement_information", output_endorsement),
    ("auxiliary_service",       output_auxiliary),
    ("responsibility",          None),
    ("update",                  None),
    ("group",                   None),
    ("ticket_status",           None),
    ("fare_calculation",        None),
    ("mailing_address",         None),
    ("billing_address",         None),
    ("fares",                   None),
    ("guest_comments",          None),
    ("fare_box",                None),
    ("tour_code",               None),
    ("original_issue",          None),
    ("ticket_number",           None),
    ("form_of_payment",         None),
    ("supplementary_name",      None),
    ("ticketing_data",          None),
]


MANUAL_AFTER = [
    ("osi_automatic", output_automatic),
    ("osi_responsibility", output_responsibility),
]
