#!/usr/bin/env python
#
# Script to send email notifications when a change in Galera cluster membership
# occurs.
#
# Complies with http://www.codership.com/wiki/doku.php?id=notification_command
#
# Author: Gabe Guillen <gabeguillen@outlook.com>
# Version: 1.5
# Release: 3/5/2015
# Use at your own risk.  No warranties expressed or implied.
#

import os
import sys
import argparse
import configparser
from datetime import datetime
import email.utils
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo.errors import WriteError
from pymongo.errors import PyMongoError
import smtplib
from smtplib import SMTPException
from smtplib import SMTPAuthenticationError
from smtplib import SMTPResponseException
import socket
import time

try:
    from email.mime.text import MIMEText
except ImportError:
    # Python 2.4 (CentOS 5.x)
    from email.MIMEText import MIMEText


# Change this to some value if you don't want your server hostname to show in
# the notification emails
THIS_SERVER = socket.gethostname()
CONFIGURATION = "/etc/mysql/galeranotify.cnf"
# Need Date in Header for SMTP RFC Compliance
DATE = email.utils.formatdate()
logger = None


# Edit below at your own risk
###############################################################################
def main(config=None, options=None):

    if config is None:
        print("A configparser object is required", file=sys.stderr)
        sys.exit(1)
    if options is None:
        print("A argparse object is required", file=sys.stderr)
        sys.exit(1)

    message_obj = GaleraStatus(THIS_SERVER)
    global logger
    logger = logging.basicConfig(filename=config.get('GENERAL', 'logfile'),
                                 level=config.get('GENERAL', 'log_level'))
    logger.info("Parsing the options")
    if options.status:
        logger.debug("Setting status value")
        message_obj.set_status(options.status)
    if options.uuid:
        logger.debug("Setting uuid value")
        message_obj.set_uuid(options.uuid)
    if options.primary:
        logger.debug("Setting primary value")
        message_obj.set_primary(options.primary)
    if options.members:
        logger.debug("Setting members value")
        message_obj.set_members(options.members)
    if options.index:
        logger.debug("Setting index value")
        message_obj.set_index(options.index)
    try:
        logger.info("Connecting to MongoDB")
        save_to_mongo(dbname=config.get('MONGO', 'mongo_db'),
                      user=config.get('MONGO', 'mongo_user'),
                      passwd=config.get('MONGO', 'mongo_pass'),
                      port=config.getint('MONGO', 'mongo_port'),
                      data=GaleraStatus)
        logger.info("Sending email to recipient")
        send_notification(mail_from=config.get('SMTP', 'mail_from'),
                          mail_to=config.get('SMTP', 'mail_to'),
                          subject='[Galera] Notification from {}'.format(
                          THIS_SERVER),
                          message=message_obj,
                          smtp_port=config.getint('SMPT', 'smtp_port'),
                          smtp_server=config.get('SMTP', 'smtp_server'),
                          smtp_ssl=config.get('SMTP', 'smtp_ssl'),
                          smtp_auth=config.get('SMTP', 'smtp_atuh'),
                          smtp_user=config.get('SMTP', 'smtp_user'),
                          smtp_pass=config.get('SMTP', 'smtp_pass'))
    except Exception as err:
        logger.critical("Unable to send notifications: {}".format(str(err)))
        print("Unable to send notification: {}".format(str(err)))
        sys.exit(1)


def save_to_mongo(dbname='wsrep_notify', user=None, passwd=None, port=27017,
                  data=None, host='localhost'):
    if data is None:
        return
    try:
        logger.debug("Creating MongoClient")
        client = MongoClient(host=host, port=int(port), username=user,
                             password=passwd)
        db = client[dbname]
        membership = db['membership']
        # Log time it happend
        now_date = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        now_time = time.time()
        i = 1
        members = []
        for node in data._members:
            # <node UUID> / <node name> / <incoming address>
            node_uuid, node_name, node_address = node.split('/')
            node_address, node_port = node_address.split(':')
            logger.debug("Adding node {}, index {}".format(node_name, str(i)))
            members.append({'idx': i, 'node_uuid': node_uuid,
                            'node_name': node_name,
                            'node_adress': node_address,
                            'node_port': node_port})
            i += 1
        logger.debug("Inserting data into MongoDB")
        doc = membership.insert_one({'status': data.getstatus(),
                                     'cluster_uuid': data.getuuid(),
                                     'primary': data.getprimary(),
                                     'cluster_size': len(members),
                                     'time': now_time,
                                     'date': now_date,
                                     'members': members})
    except ConnectionFailure as err:
        raise Exception("Problem connection to server: {}".format(str(err)))
    except WriteError as err:
        raise Exception("Problem writing data: {}".format(str(err)))
    except PyMongoError as err:
        raise Exception("Problem inserting data: {}".format(str(err)))
    return doc


def send_notification(mail_from=None, mail_to=None, smtp_server=None,
                      subject="[GALERA] Notification", message=None,
                      smtp_port=25, smtp_auth=False, smtp_ssl=False,
                      smtp_user=None, smtp_pass=None):
    logger.debug("Creating MIMEText message")
    msg = MIMEText(message)

    msg['From'] = mail_from
    msg['To'] = ', '.join(mail_to)
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate()

    if smtp_ssl:
        logger.debug("Creating SMTP_SSL object")
        mailer = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        logger.debug("Creating SMTP object")
        mailer = smtplib.SMTP(smtp_server, smtp_port)

    if smtp_auth:
        logger.debug("Authenticating user")
        try:
            mailer.login(smtp_user, smtp_pass)
        except SMTPAuthenticationError as err:
            raise Exception("Problem authenticating to SMTP server: {}"
                            .format(str(err)))
    try:
        logger.debug("Sending email")
        mailer.sendmail(mail_from, mail_to, msg.as_string())
        mailer.close()
    except SMTPResponseException as err:
        raise Exception("Problem with SMTP server: {}".format(str(err)))
    except SMTPException as err:
        raise Exception("Problem sending email: {}".format(str(err)))
    return 0


class GaleraStatus:

    """This class is made to handle and describe what changed on a Galera
    cluster node"""
    def __init__(self, server):
        self._server = server
        self._status = ""
        self._uuid = ""
        self._primary = ""
        self._members = ""
        self._index = ""
        self._count = 0

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status
        self._count += 1

    def get_uuid(self):
        return self._uuid

    def set_uuid(self, uuid):
        self._uuid = uuid
        self._count += 1

    def get_primary(self):
        return self._primary

    def set_primary(self, primary):
        self._primary = primary.capitalize()
        self._count += 1

    def get_members(self):
        return self._members

    def set_members(self, members):
        self._members = members.split(',')
        self._count += 1

    def get_index(self):
        return self._index

    def set_index(self, index):
        self._index = index
        self._count += 1

    def __str__(self):
        message = "Galera running on {} has reported the following cluster" \
                  " membership change".format(str(self._server))

        if self._count > 1:
            message += "s"

        message += ":\n\n"

        if self._status:
            message += "Status of this node: {}\n\n".format(str(self._status))

        if self._uuid:
            message += "Cluster state UUID: {}\n\n".format(str(self._uuid))

        if self._primary:
            message += "Current cluster component is primary: {}\n\n"\
                       .format(self._primary)

        if self._members:
            message += "Current members of the component:\n"

            if self._index:
                for i in range(len(self._members)):
                    if i == int(self._index):
                        message += "{} ".format(str('->'))
                    else:
                        message += "{} ".format(str('--'))

                    message += "{}\n".format(str(self._members[i]))
            else:
                message += "\n".join(("  " + str(x)) for x in self._members)

            message += "\n"

        if self._index:
            message += "Index of this node in the member list: {}\n"\
                       .format(str(self._index))

        return message


if __name__ == "__main__":

    if not os.path.exists(CONFIGURATION):
        print("Can't find configuration file!", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(CONFIGURATION)

    description = "Python script for use with Galera wsrep_notify_cmd. It "\
                  "sends email and save Galera nodes states in MongoDB."

    epilog = "Usage: " + os.path.basename(sys.argv[0]) + " --status " \
             "<status str> --uuid <state UUID> --primary <yes/no> --members " \
             "<comma-seperated list of the component member UUIDs> --index <n>"
    epilog += "Originally written by Gabe Guillen, modified by Emmanuel "\
              "Quevillon."
    parser = argparse.ArgumentParser(epilog=epilog, description=description)
    parser.add_argument('--index', default=None, type=int, action="store",
                        dest="index", required=True,
                        help="Indicates node index value in the membership "
                             "list.")
    parser.add_argument('--members', default=None, type=str, action="store",
                        dest="members", required=True,
                        help="List containing entries for each node that is "
                             "connected to the cluster.")
    parser.add_argument('--primary', default=None, type=str, action="store",
                        dest="primary", required=True,
                        help="The node passes a string of either yes or no, "
                             "indicating whether it considers itself part of"
                             " the Primary Component")
    parser.add_argument('--status', default=None, type=str, action="store",
                        dest="status", require=True,
                        help="The node passes a string indicating it’s current"
                             " state")
    parser.add_argument('--uuid', default=None, type=str, action="store",
                        dest="uuid", required=True,
                        help="Refers to the unique identifier the node "
                             "receives from the wsrep Provider.")
    options = parser.parse_args()

    if not len(sys.argv) > 1:
        parser.print_usage()
        parser.print_help()
        parser.exit(status=1)

    main(config=config, options=options)
    sys.exit(0)
