#!/usr/bin/env python

import copy
import logging
import optparse
import os
import sys
import time

from multiprocessing import Process, Lock, Queue, Condition

from pnr_read import read_pnr
from pnr_parse import parse_pnr
from pnr_telegram import make_telegram
# from pnr_csv import make_csv

from pnr_types import *


def parse_opts():
    parser = optparse.OptionParser()

    parser.add_option("-i", "--filename", dest = "filename",
                      help = ("name of file with pnr records"))

    parser.add_option("-a", "--airline", dest = "airline",
                      help = ("airline name"))

    parser.add_option("-y", "--current_year", dest = "current_year", default = '2014',
                      help = ("current year if need for broken itin records."
                              "By default: 2014"))

    parser.add_option("-s", "--source-address", dest = "src_addr", default = 'HDQRM5N',
                      help = ("source airimp address"))

    parser.add_option("-d", "--destination-address", dest = "dest_addr", default = 'MOWRM5N',
                      help = ("destination airimp address"))

    parser.add_option("-p", "--pred-point", dest = "pred_point",
                      help = ("airimp predPoint. default build from srcAddr"))

    parser.add_option("-f", "--format", dest = "format_", default = 'airimp',
                      help = ("output format [default: %(default)s], values [airimp, csv]"))

    parser.add_option("-o", "--outfile", dest = "outfile", default = sys.stdout,
                      help = ("output file name"))

    parser.add_option("-m", "--parallel", dest = "parallel", default = '1',
                      help = ("run in parallel"))

    parser.add_option("-l", "--local_systems", dest = "local_systems", default = None,
                      help = ("force local systems"))

    parser.add_option("-g", "--ignored_file", dest = "ignored", default = 'ignored.log',
                      help = ("ignored PNRs file"))

    opts, args = parser.parse_args()

    if not opts.filename:
        parser.error("You must specify a filename.")

    if len(opts.src_addr) != 7:
        parser.error('Invalid source airimp address')

    if len(opts.dest_addr) != 7:
        parser.error('Invalid destination airimp address')

    if opts.pred_point is None:
        opts.pred_point = opts.src_addr[0:3] + opts.src_addr[5:7]

    if isinstance(opts.outfile, str):
        opts.outfile = open(opts.outfile, 'w')

    if opts.parallel not in ('0', '1'):
        parser.error('Wrong `parallel`. Must be 0 or 1.')

    if opts.format_ not in ('airimp', 'csv'):
        parser.error('Wrong `format`. Must be `airimp` or `csv`.')

    systems = opts.local_systems
    if systems:
        systems = systems.split(',')
        for system in systems:
            system = system.strip()

    opts.parallel = True if opts.parallel == '1' else False

    if isinstance(opts.ignored, str):
        opts.ignored = open(opts.ignored, 'w')

    return opts


def print_exception(record, text, e):
    data = "{0}\n"
    "{4}\n"
    "Main process exception.\n"
    "PNR: {1}\nException: {2}\n"
    "{3}\n\n".format('!' * 80, record, e, '!' * 80, text)

    print(data)
    logging.error(data)


def get_telegram(record, settings):
    try:
        pnr = parse_pnr(record, settings)
    except Exception as e:
        print_exception(record, 'PNR exception.', e)
        raise

    try:
        if settings.format_ == 'airimp':
            return make_telegram(pnr, settings)
        else:
            return make_csv(pnr, settings)
    except Exception as e:
        print_exception(record, 'Telegram exception.', e)
        raise

    return None


def write_telegram(telegram, outfile):
    if telegram:
        outfile.write(telegram)
        outfile.write('\n\n')


def process_pnr(q, num, settings, cond):
    with open("parsed{}.txt".format(num), "w") as file,\
         open("ignored{}.txt".format(num), "w") as ignored:
            while True:
                record = q.get()

                if record is None:
                    break

                s = copy.copy(settings)
                s.ignored = ignored

                write_telegram(get_telegram(record, s), file)


def start_current(settings):
    """
    Test function for single treaded process.
    """
    for record in read_pnr(settings.filename):
        write_telegram(get_telegram(record, settings), settings.outfile)


def start_processes(count, settings, queue_size):
    """
    Starts `count` processes for perform PNR data file `filename`.

    `queue_size` - a queue size which contains readed PNR.
    """
    q = Queue(queue_size)
    processes = []
    cond = Condition()

    for num in range(count):
        p = Process(target = process_pnr, args = (q, num, settings, cond))
        processes.append(p)
        p.daemon = True
        p.start()

    for record in read_pnr(settings.filename):
        q.put(record)

    for ignore in range(count):
        q.put(None)

    q.close()

    for process in processes:
        process.join()

    concat_files(settings.outfile, count, 'parsed')
    concat_files(settings.ignored, count, 'ignored')


def concat_files(outfile, n, name):
    files = []
    for i in range(n):
        files.append('{0}{1}.txt'.format(name, i))

    for filename in files:
        with open(filename, 'r') as fd:
            for line in fd:
                outfile.write(line)

        try:
            os.remove(filename)
        except OSError:
            pass


def init_logging():
    logging.basicConfig(format='%(asctime)s %(levelname)s:\n%(message)s',
                        filename='pnr-parse.log',
                        filemode='w',
                        level=logging.DEBUG)


def main():
    opts = parse_opts()
    init_logging()

    start_time = time.time()

    if opts.parallel:
        start_processes(count = 3, settings = opts, queue_size = 500)
    else:
        start_current(opts)

    print('Execution time: {:.3} seconds.'.format(time.time() - start_time))

    opts.outfile.close()


if __name__ == "__main__":
    main()
