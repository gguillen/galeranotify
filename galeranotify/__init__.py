#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 sts=4 et
#
# galeranotify - wsrep_notify_cmd applications main functions
#
# Script to send email notifications when a change in Galera cluster membership
# occurs.
#
# Complies with http://www.codership.com/wiki/doku.php?id=notification_command
#
# Copyright (c) Gabe Guillen <gabeguillen@outlook.com>, 2015
# Copyright (c) Jan-Jonas Sämann <sprinterfreak@binary-kitchen.de>, 2019
# available under the GPLv2 licence, see LICENSE

import os
import sys
import getopt
from galeranotify import configuration, persistance

try:
    from email.mime.text import MIMEText
except ImportError:
    # Python 2.4 (CentOS 5.x)
    from email.MIMEText import MIMEText
import smtplib
import email.utils

def main():
    argv = sys.argv[1:]
    str_status = ''
    str_uuid = ''
    str_primary = ''
    str_members = ''
    str_index = ''
    message = ''

    usage = "Usage: " + os.path.basename(sys.argv[0]) + " --status <status str>"
    usage += " --uuid <state UUID> --primary <yes/no> --members <comma-seperated"
    usage += " list of the component member UUIDs> --index <n> --config <file>"

    try:
        opts, args = getopt.getopt(argv, "h", ["status=","uuid=",'primary=','members=','index=','config='])
    except getopt.GetoptError:
        print usage
        sys.exit(2)

    config = configuration.ConfigFactory('/etc/mysql/galeranotify.yml')


    # Need Date in Header for SMTP RFC Compliance
    DATE = email.utils.formatdate()

    if(len(opts) > 0):
        message_obj = GaleraStatus(config['hostname'])

        for opt, arg in opts:
            if opt == '-h':
                print usage
                sys.exit()
            elif opt in ("--status"):
                message_obj.set_status(arg)
            elif opt in ("--uuid"):
                message_obj.set_uuid(arg)
            elif opt in ("--primary"):
                message_obj.set_primary(arg)
            elif opt in ("--members"):
                message_obj.set_members(arg)
            elif opt in ("--index"):
                message_obj.set_index(arg)
            elif opt in ("--config"):
                raise NotImplementedError("Custom configuration path isn't supported yet. Configuration MUST be present in /etc/mysql/galeranotify.yml")

        if not message_obj.state_changed():
            sys.stderr.write('Skip notification. Information didn\'t change\n')
            sys.exit(0)

        try:
            send_notification(config['email_from'], config['email_to'], 'Galera Notification: ' + config['hostname'], DATE,
                str(message_obj), config['smtp','server'], config['smtp','port'], bool(config['smtp','ssl']),
                bool(config['smtp','auth_enable']), config['smtp','username'], config['smtp','password'])
        except Exception, e:
            sys.stderr.write('Unable to send notification: %s'.format(e))
            sys.exit(0)
    else:
        print usage
        sys.exit(2)

    sys.exit(0)

def send_notification(from_email, to_email, subject, date, message, smtp_server,
                      smtp_port, use_ssl, use_auth, smtp_user, smtp_pass):
    msg = MIMEText(message)

    msg['From'] = from_email
    msg['To'] = ', '.join(to_email)
    msg['Subject'] =  subject
    msg['Date'] =  date

    if(use_ssl):
        mailer = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        mailer = smtplib.SMTP(smtp_server, smtp_port)

    if(use_auth):
        mailer.login(smtp_user, smtp_pass)

    mailer.sendmail(from_email, to_email, msg.as_string())
    mailer.close()

class GaleraStatus():
    def __init__(self, server):
        self._server = server
        self._status = ""
        self._uuid = ""
        self._primary = ""
        self._members = ""
        self._index = ""
        self._count = 0
        self.persistance = persistance.DatabaseFactory('/tmp/galeranotify_persistance.yml')

    def set_status(self, status):
        self._status = status
        self.persistance['status'] = status
        self._count += 1

    def set_uuid(self, uuid):
        self._uuid = uuid
        self.persistance['uuid'] = uuid
        self._count += 1

    def set_primary(self, primary):
        self._primary = primary.capitalize()
        self.persistance['primary'] = self._primary
        self._count += 1

    def set_members(self, members):
        self._members = members.split(',')
        self.persistance['members'] = self._members
        self._count += 1

    def set_index(self, index):
        self._index = index
        self.persistance['index'] = index
        self._count += 1

    def state_changed(self):
        return self.persistance.changed()

    def __str__(self):
        message = "Galera running on " + self._server + " has reported the following"
        message += " cluster membership change"

        if(self._count > 1):
            message += "s"

        message += ":\n\n"

        if(self._status):
            message += "Status of this node: " + self._status + "\n\n"

        if(self._uuid):
            message += "Cluster state UUID: " + self._uuid + "\n\n"

        if(self._primary):
            message += "Current cluster component is primary: " + self._primary + "\n\n"

        if(self._members):
            message += "Current members of the component:\n"

            if(self._index):
                for i in range(len(self._members)):
                    if(i == int(self._index)):
                        message += "-> "
                    else:
                        message += "-- "

                    message += self._members[i] + "\n"
            else:
                message += "\n".join(("  " + str(x)) for x in self._members)

            message += "\n"

        if(self._index):
            message += "Index of this node in the member list: " + self._index + "\n"

        return message
