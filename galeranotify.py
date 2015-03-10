#!/usr/bin/env python
#
# Script to send email notifications when a change in Galera cluster membership
# occurs.
#
# Complies with http://www.codership.com/wiki/doku.php?id=notification_command
#
# Author: Gabe Guillen <gguillen@gesa.com>
# Version: 1.3
# Release: 2013-10-03
#
# Author: Valdemar Jakobsen <valdemar@jakobsen.pro>
# Version: 1.4
# Release: 2015-03-10
#
# Use at your own risk.  No warranties expressed or implied.

import os
import sys
import getopt

import smtplib

try:
    from email.mime.text import MIMEText
except ImportError:
    # Python 2.4 (CentOS 5.x)
    from email.MIMEText import MIMEText

import socket

# Mail Sender Address
# MAIL_FROM = 'SENDER_EMAIL_ADDRESS'
MAIL_FROM = 'mysql'

# Mail Recipient Addresses
# MAIL_TO = ['RECIPIENT1_EMAIL_ADDRESS', 'RECIPIENT2_EMAIL_ADDRESS']
MAIL_TO = ['root']

# Change this to some value if you don't want your server hostname to show in
# the notification emails
THIS_SERVER = socket.gethostname()
MAIL_SUBJECT = 'Galera Notification for host "%s"' % THIS_SERVER

# SMTP Server hostname/IP address and port number
# SMTP_SERVER = THIS_SERVER
SMTP_SERVER = 'localhost'
SMTP_PORT = 25

# SMTP SSL and TLS Default Ports
SMTP_SSL_PORTS = [465]
SMTP_TLS_PORTS = [587]

# Explicitly set SSL and TLS if you need to override the defaults and/or operating on a non-standard port
# SMTP_SSL_OVERRIDE = True
SMTP_SSL_OVERRIDE = ''
# SMTP_TLS_OVERRIDE = False
SMTP_TLS_OVERRIDE = ''

# Transport Layer Encryption Settings
# only one of [SSL,TLS] may be set
# SSL has priority over TLS
if SMTP_PORT in SMTP_SSL_PORTS:
    SMTP_SSL = SMTP_SSL_OVERRIDE if SMTP_SSL_OVERRIDE else True
    SMTP_TLS = SMTP_TLS_OVERRIDE if SMTP_TLS_OVERRIDE else False
elif SMTP_PORT in SMTP_TLS_PORTS:
    SMTP_SSL = SMTP_SSL_OVERRIDE if SMTP_SSL_OVERRIDE else False
    SMTP_TLS = SMTP_TLS_OVERRIDE if SMTP_TLS_OVERRIDE else True
else:
    SMTP_SSL = SMTP_SSL_OVERRIDE if SMTP_SSL_OVERRIDE else False
    SMTP_TLS = SMTP_TLS_OVERRIDE if SMTP_TLS_OVERRIDE else True

# Set SMTP Authentication Credentials if required by server
SMTP_USERNAME = ''
SMTP_PASSWORD = ''
SMTP_AUTH = True if (SMTP_USERNAME and SMTP_PASSWORD) else False


# Edit below at your own risk
# ###########################
def main(argv):
    str_status = ''
    str_uuid = ''
    str_primary = ''
    str_members = ''
    str_index = ''
    email_body = ''

    global MAIL_SUBJECT

    global SMTP_SSL
    global SMTP_TLS
    if SMTP_SSL and SMTP_TLS:
        print 'Only one of SSL and TLS can be set, preferring SSL'
        SMTP_TLS = False

    usage = 'Usage: %s' % os.path.basename(sys.argv[0])
    usage += ' --status <status str> --uuid <state UUID> --primary <yes/no>'
    usage += ' --members <comma-seperated list of the component member UUIDs> --index <n>'

    try:
        opts, args = getopt.getopt(
            argv, 'h',
            ['cluster-name=', 'status=', 'uuid=', 'primary=', 'members=', 'index='])
    except getopt.GetoptError:
        print usage
        sys.exit(2)

    if(len(opts) > 0):
        MAIL_CONTENT = GaleraStatus(THIS_SERVER)
        for opt, arg in opts:
            if opt == '-h':
                print usage
                sys.exit()
            elif opt in ('--status'):
                MAIL_CONTENT.set_status(arg)
            elif opt in ('--uuid'):
                MAIL_CONTENT.set_uuid(arg)
            elif opt in ('--primary'):
                MAIL_CONTENT.set_primary(arg)
            elif opt in ('--members'):
                MAIL_CONTENT.set_members(arg)
            elif opt in ('--index'):
                MAIL_CONTENT.set_index(arg)
            elif opt in ('--cluster-name'):
                MAIL_CONTENT.set_cluster_name(arg)
                MAIL_SUBJECT = 'Galera Notification for cluster "%s", host "%s"' % (arg, THIS_SERVER)
        try:
            send_notification(MAIL_FROM, MAIL_TO, MAIL_SUBJECT, str(MAIL_CONTENT),
                              SMTP_SERVER, SMTP_PORT, SMTP_SSL, SMTP_TLS,
                              SMTP_AUTH, SMTP_USERNAME, SMTP_PASSWORD)
        except Exception, e:
            print 'Unable to send notification: %s' % e
            sys.exit(1)

    else:
        print usage
        sys.exit(2)

    sys.exit(0)


def send_notification(
    email_sender, email_recipients, email_subject, email_body,
    smtp_server, smtp_port, use_ssl, use_tls,
    use_auth, smtp_user, smtp_pass
):
    msg = MIMEText(email_body)
    msg['From'] = email_sender
    msg['To'] = ', '.join(email_recipients)
    msg['Subject'] = email_subject

    if use_ssl:
        try:
            mailer = smtplib.SMTP_SSL(smtp_server, smtp_port)
        except Exception, e:
            print 'Unable to start SMTP SSL connection: %s' % e
            sys.exit(1)
    else:
        try:
            mailer = smtplib.SMTP(smtp_server, smtp_port)
        except Exception, e:
            print 'Unable to connect to SMTP server: %s' % e
            sys.exit(1)
        if use_tls:
            try:
                mailer.starttls()
            except Exception, e:
                print 'Unable to start TLS: %s' % e
                sys.exit(1)

    if use_auth:
        try:
            mailer.login(smtp_user, smtp_pass)
        except Exception, e:
            print 'Unable to authenticate to SMTP server: %s' % e
            sys.exit(1)

    try:
        mailer.sendmail(email_sender, email_recipients, msg.as_string())
    except Exception, e:
        print 'Unable to send email_body: %s' % e
        sys.exit(1)

    mailer.close()


class GaleraStatus:
    def __init__(self, server):
        self._server = server
        self._cluster_name = ''
        self._status = ''
        self._uuid = ''
        self._primary = ''
        self._members = ''
        self._index = ''
        self._count = 0

    def set_cluster_name(self, cluster_name):
        self._cluster_name = cluster_name
        self._count += 1

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
        if self._cluster_name:
            email_body = 'Galera Cluster "%s" running on host "%s" has an updated cluster state:\n\n' % (self._cluster_name, self._server)
        else:
            email_body = 'Galera Cluster running on host "%s" has an updated cluster state:\n\n' % self._server
        email_body += '%s' % '    Cluster Name        ::  %s\n\n' % self._cluster_name if self._cluster_name else ''
        email_body += '%s' % '    Cluster State UUID  ::  %s\n\n' % self._uuid if self._uuid else ''
        email_body += '%s' % '    Node Name           ::  %s\n\n' % self._server
        email_body += '%s' % '    Node Status         ::  %s\n\n' % self._status if self._status else ''
        email_body += '%s' % '    Node Primary        ::  %s\n\n' % self._primary if self._primary else ''
        if self._members:
            email_body += '    Cluster Members:\n\n'
            for index in range(len(self._members)):
                email_body += '        -%s %s\n' % ('>' if index == int(self._index) else '-', self._members[index])
            email_body += '\n%s\n' % '    This node is index [%s] in the member list\n' % self._index if self._index else ''
        return email_body


if __name__ == '__main__':
    main(sys.argv[1:])
