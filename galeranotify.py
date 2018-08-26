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
import getopt

try: from email.mime.text import MIMEText
except ImportError:
    # Python 2.4 (CentOS 5.x)
    from email.MIMEText import MIMEText

import socket
import email.utils

# Set to True to use sendmail for notification message or False for SMTP
LOCAL_METHOD = False

# Change this to some value if you don't want your server hostname to show in
# the notification emails
THIS_SERVER = socket.gethostname()

# Takes a single sender. If LOCAL_METHOD is True you can set this to None and
# the sender will be set to the user the galera node runs under (in accordance
# with your sendmail settings).
MAIL_FROM = 'YOUR_EMAIL_HERE'

# Takes a list of recipients
MAIL_TO = ['SOME_OTHER_EMAIL_HERE']

###                                              ###
# The rest is only needed if LOCAL_METHOD is False #
###                                              ###

# Server hostname or IP address
SMTP_SERVER = 'YOUR_SMTP_HERE'
SMTP_PORT = 25

# Set to True if you need SMTP over SSL
SMTP_SSL = False

# Set to True if you need to authenticate to your SMTP server
SMTP_AUTH = False
# Fill in authorization information here if True above
SMTP_USERNAME = ''
SMTP_PASSWORD = ''

# Need Date in Header for SMTP RFC Compliance
DATE = email.utils.formatdate()

# Edit below at your own risk
################################################################################
def main(argv):
    str_status = ''
    str_uuid = ''
    str_primary = ''
    str_members = ''
    str_index = ''
    message = ''

    usage = "Usage: " + os.path.basename(sys.argv[0]) + " --status <status str>"
    usage += " --uuid <state UUID> --primary <yes/no> --members <comma-seperated"
    usage += " list of the component member UUIDs> --index <n>"

    try:
        opts, args = getopt.getopt(argv, "h", ["status=","uuid=",'primary=','members=','index='])
    except getopt.GetoptError:
        print usage
        sys.exit(2)

    if(len(opts) > 0):
        message_obj = GaleraStatus(THIS_SERVER)

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
        try:
            if(LOCAL_METHOD):
                send_notification_local(MAIL_FROM, MAIL_TO, 'Galera Notification: ' + THIS_SERVER,
                                        DATE, str(message_obj))
            else:
                send_notification_smtp(MAIL_FROM, MAIL_TO, 'Galera Notification: ' + THIS_SERVER,
                                       DATE, str(message_obj), SMTP_SERVER, SMTP_PORT, SMTP_SSL,
                                       SMTP_AUTH, SMTP_USERNAME, SMTP_PASSWORD)
        except Exception, e:
            print "Unable to send notification: %s" % e
            sys.exit(1)
    else:
        print usage
        sys.exit(2)

    sys.exit(0)

def send_notification_local(from_email, to_email, subject, date, message):
    import subprocess
    msg = MIMEText(message)

    env = {}
    env.update(os.environ)

    from_args = []
    if from_email != None and from_email != 'None':
        from_args = ['-r', from_email]

    args = ['mail', '-s', subject] + from_args + to_email
    p = subprocess.Popen(args, env=env, stdin=subprocess.PIPE)
    p.communicate(str(message)+'\n')

    if p.returncode != 0:
        raise Exception('Failed to send email using the local method.', p.returncode,
                        from_email, to_email, subject, message)

def send_notification_smtp(from_email, to_email, subject, date, message, smtp_server,
                           smtp_port, use_ssl, use_auth, smtp_user, smtp_pass):
    import smtplib
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

class GaleraStatus:
    def __init__(self, server):
        self._server = server
        self._status = ""
        self._uuid = ""
        self._primary = ""
        self._members = ""
        self._index = ""
        self._count = 0

    def set_status(self, status):
        self._status = status
        self._count += 1

    def set_uuid(self, uuid):
        self._uuid = uuid
        self._count += 1

    def set_primary(self, primary):
        self._primary = primary.capitalize()
        self._count += 1

    def set_members(self, members):
        self._members = members.split(',')
        self._count += 1

    def set_index(self, index):
        self._index = index
        self._count += 1

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

if __name__ == "__main__":
    main(sys.argv[1:])
