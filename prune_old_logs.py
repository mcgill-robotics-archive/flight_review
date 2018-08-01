#! /usr/bin/env python3

# Script to delete old log files & DB entries matching a certain criteria

import sqlite3
import sys
import os
import argparse
import datetime

# this is needed for the following imports
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'plot_app'))
from plot_app.config import get_db_filename
from plot_app.helper import get_log_filename


parser = argparse.ArgumentParser(description='Remove old log files & DB entries')

parser.add_argument('--max-age', action='store', type=int, default=30,
        help='maximum age in days (delete logs older than this, default=30)')
parser.add_argument('--source', action='store',
        help='Source DB entry tag to match (empty=all, default=CI)')
parser.add_argument('--interactive', '-i', action='store_true', default=False,
        help='Interative mode: ask whether to delete the entries')

parser.add_argument('--personal-only', '-p', action='store_true', default=False,
        help='Only prune personal logs')
parser.add_argument('--private-only', '-s', action='store_true', default=False,
        help='Only prune private logs')

args = parser.parse_args()


max_age = args.max_age
source = args.source
interactive = args.interactive
personal_only = args.personal_only
private_only = args.private_only


con = sqlite3.connect(get_db_filename(), detect_types=sqlite3.PARSE_DECLTYPES)
with con:
    cur = con.cursor()
    log_ids_to_remove = []

    if source is None or len(source) == 0:
        cur.execute('select Id, Date, Description, Type, Public from Logs')
    else:
        cur.execute('select Id, Date, Description, Type, Public from Logs where Source = ?', [source])

    db_tuples = cur.fetchall()
    print('will delete the following:')
    for log_id, date, description, log_type, is_public in db_tuples:
        # check date
        elapsed_days = (datetime.datetime.now()-date).days
        if elapsed_days > max_age:
            if personal_only and log_type != 'personal':
                continue
            if private_only and is_public:
                continue

            print('{} {} {} {}'.format(log_id, date.strftime('%Y_%m_%d-%H_%M'),
                description, log_type))
            log_ids_to_remove.append(log_id)


    if len(log_ids_to_remove) == 0:
        print('no matches. exiting')
        exit(0)

    cur.execute('select count(*) from Logs')
    num_total = cur.fetchone()
    if num_total is not None:
        print("Will delete {:} logs out of {:}".format(len(log_ids_to_remove), num_total[0]))

    if interactive:
        try:
            confirm = input('Press "y" and ENTER to confirm and delete: ')
            if confirm != 'y':
                print('Not deleting anything')
                exit(0)
        except KeyboardInterrupt:
            exit(0)

    for log_id in log_ids_to_remove:
        print('Removing '+log_id)
        # db entry
        cur.execute("DELETE FROM LogsGenerated WHERE Id = ?", (log_id,))
        cur.execute("DELETE FROM Logs WHERE Id = ?", (log_id,))
        num_deleted = cur.rowcount
        if num_deleted != 1:
            print('Error: not found ({})'.format(num_deleted))
        con.commit()

        # and the log file
        ulog_file_name = get_log_filename(log_id)
        os.unlink(ulog_file_name)

con.close()

