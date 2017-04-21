#!/usr/bin/env python

import collections

class PnrParseException(Exception): pass

Opts = collections.namedtuple("Opts", "filename current_year airline src_addr dest_addr pred_point format_ outfile parallel local_systems")

Pax = collections.namedtuple("Pax", "name surname status nseats group")
Itin = collections.namedtuple("Itin", "airline flightnum itin_class depdate deppoint arrpoint status nseats deptime arrtime text")
Contact = collections.namedtuple("Contact", "text")
Ssr = collections.namedtuple("Ssr", "code airline status nseats text paxnum")
Osi = collections.namedtuple("Osi", "airline text paxnum")
Remarks = collections.namedtuple("Remarks", "text paxnum")
Responsibility = collections.namedtuple("Responsibility", "text")
Endorsement = collections.namedtuple("Endorsement", "text paxnum")
Group = collections.namedtuple("Group", "total name named")
Auxiliary = collections.namedtuple("Auxiliary", "airline status nseats primary_loc_code secondary_loc_code service_date text paxnum")

CodeFn = collections.namedtuple("CodeFn", ('code', 'fn'))

ADULT, CHILD, INFANT = range(3)
MALE, FEMALE = range(2)
