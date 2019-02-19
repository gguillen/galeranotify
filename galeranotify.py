#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from __future__ import print_function
import os
import sys
import argparse
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
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


# Change this to some value if you don't want your server hostname to show in
# the notification emails
THIS_SERVER = socket.gethostname()
# PLEASE EDIT ME!
CONFIGURATION = "/path/to/galeranotify.cnf"


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

    logging.info("Parsing options")
    if options.status:
        logging.debug("Setting status value")
        message_obj.set_status(options.status)
    if options.uuid:
        logging.debug("Setting uuid value")
        message_obj.set_uuid(options.uuid)
    if options.primary:
        logging.debug("Setting primary value")
        message_obj.set_primary(options.primary)
    if options.members:
        logging.debug("Setting members value")
        message_obj.set_members(options.members)
    if options.index:
        logging.debug("Setting index value")
        message_obj.set_index(options.index)
    try:
        if config.get('MONGO', 'use_mongo') is True:
            logging.info("Connecting to MongoDB")
            save_to_mongo(dbname=config.get('MONGO', 'mongo_db'),
                          uri=config.get('MONGO', 'mongo_uri'),
                          data=message_obj)
        logging.info("Sending email to recipient")
        send_notification(mail_from=config.get('SMTP', 'mail_from'),
                          mail_to=config.get('SMTP', 'mail_to'),
                          subject='[Galera] Notification from {}'.format(
                          THIS_SERVER),
                          message=message_obj,
                          smtp_port=config.get('SMTP', 'smtp_port'),
                          smtp_server=config.get('SMTP', 'smtp_server'),
                          #smtp_ssl=config.get('SMTP', 'smtp_ssl'),
                          smtp_auth=config.get('SMTP', 'smtp_auth'),
                          smtp_user=config.get('SMTP', 'smtp_user'),
                          smtp_pass=config.get('SMTP', 'smtp_pass'))
        logging.info("Host {} has status {}".format(THIS_SERVER,
                                                    message_obj.get_status()))
    except Exception as err:
        logging.critical("Unable to send notifications: {}".format(str(err)))
        print("Unable to send notification: {}".format(str(err)),
              file=sys.stderr)
        sys.exit(1)


def save_to_mongo(dbname='wsrep_notify', uri=None, data=None):
    if data is None:
        return
    try:
        logging.debug("Creating MongoClient")
        client = MongoClient(uri)
        logging.debug("Connected to MongoDB")
        db = client[dbname]
        membership = db['membership']
        # Log time it happend
        now_date = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        now_time = time.time()
        i = 0
        members = []
        logging.debug("Looping over members")
        for node in data.get_members():
            # <node UUID> / <node name> / <incoming address>
            node_uuid, node_name, node_address = node.split('/')
            # Set default port for our node
            node_port = '3306'
            if ':' in node_address:
                node_address, node_port = node_address.split(':')
            logging.debug("Adding node {} / address {} / index {}"
                          .format(node_name, node_address, str(i)))
            members.append({'idx': i, 'node_uuid': node_uuid,
                            'node_name': node_name,
                            'node_adress': node_address,
                            'node_port': node_port})
            i += 1
        logging.debug("Inserting data into MongoDB")
        doc = membership.insert_one({'status': data.get_status(),
                                     'cluster_uuid': data.get_uuid(),
                                     'primary': data.get_primary(),
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
                      smtp_port=None, smtp_auth=False, smtp_ssl=False,
                      smtp_user=None, smtp_pass=None):
    logging.debug("Creating MIMEText message")
    msg = MIMEText(message.get_message())

    msg['From'] = mail_from
    msg['To'] = mail_to
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate()
    if smtp_port is None or smtp_port == '':
        smtp_port = 25
    if smtp_server is None:
        smtp_server = socket.gethostname()

    logging.debug("Creating SMTP object")
    mailer = smtplib.SMTP(host=smtp_server, port=int(smtp_port))

    if smtp_auth is True:
        logging.debug("Authenticating user")
        try:
            mailer.ehlo()
            mailer.starttls()
            mailer.login(smtp_user, smtp_pass)
        except SMTPAuthenticationError as err:
            raise Exception("Problem authenticating to SMTP server: {}"
                            .format(str(err)))
    try:
        logging.debug("Sending email")
        mailer.connect()
        mailer.sendmail(mail_from, mail_to, msg.as_string())
        mailer.quit()
    except SMTPResponseException as err:
        raise Exception("Problem with SMTP server: {}".format(str(err)))
    except SMTPException as err:
        raise Exception("Problem sending email: {}".format(str(err)))
    return 0


class GaleraStatus(object):

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

    def get_message(self):
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

    description = "Python script for use with Galera wsrep_notify_cmd. It "\
                  "sends email and save Galera nodes states in MongoDB."

    epilog = "Usage: " + os.path.basename(sys.argv[0]) + " --status " \
             "<status str> --uuid <state UUID> --primary <yes/no> --members " \
             "<comma-seperated list of the component member UUIDs> --index <n>"
    epilog += "Originally written by Gabe Guillen, modified by Emmanuel "\
              "Quevillon."
    parser = argparse.ArgumentParser(epilog=epilog, description=description)
    parser.add_argument('--index', default=None, type=str, action="store",
                        dest="index", required=False,
                        help="Indicates node index value in the membership "
                             "list.")
    parser.add_argument('--members', default=None, type=str, action="store",
                        dest="members", required=False,
                        help="List containing entries for each node that is "
                             "connected to the cluster.")
    parser.add_argument('--primary', default=None, type=str, action="store",
                        dest="primary", required=False,
                        help="The node passes a string of either yes or no, "
                             "indicating whether it considers itself part of"
                             " the Primary Component")
    parser.add_argument('--status', default=None, type=str, action="store",
                        dest="status", required=False,
                        help="The node passes a string indicating it’s current"
                             " state")
    parser.add_argument('--uuid', default=None, type=str, action="store",
                        dest="uuid", required=False,
                        help="Refers to the unique identifier the node "
                             "receives from the wsrep Provider.")
    options = parser.parse_args()

    if not len(sys.argv) > 1:
        parser.print_usage()
        parser.print_help()
        parser.exit(status=1)

    if not os.path.exists(CONFIGURATION):
        print("Can't find configuration file!", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(CONFIGURATION)

    logging.basicConfig(filename=config.get('GENERAL', 'log_file'),
                        level=config.get('GENERAL', 'log_level'),
                        format="[%(asctime)s] %(funcName)s:%(lineno)d "
                               "%(levelname)-5s: %(message)s")
    main(config=config, options=options)
    sys.exit(0)
