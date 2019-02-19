galeranotify
============

Python E-Mail script for use with Galera `wsrep_notify_cmd`

Why do I need / want this?
--------------------------

[Galera](http://codership.com/products/galera_replication) makes my life easier with near synchronous replication for MySQL.  We have monitoring tools in place, but its nice to get updates in real time about how the cluster is operating.  So I wrote galeranotify.

I've been using this on our [Percona XtraDB Cluster](http://www.percona.com/software/percona-xtradb-cluster) for quite a while now with no issues.

I hope someone finds it useful.

Added by Emmanuel Quevillon:

In order to keep track of what Galera cluster has operating on, I added the possibility to log cluster operation in a MongoDB database.
Edit `galeranotify.py` to point `CONFIGURATION` to the appropriate configuration file (check `galeranotify.cnf` for example).

Set up
------

1. Edit galeranotify.py to change the configuration options.  They should be pretty straightforward.

2. Place galeranotify.py in a common location and make sure you and your MySql user have execute permissions.

3. Manually execute galeranotify.py with several of the options set (check usage) and check to make sure the script executes with no errors and that you receive the notification e-mail.

4. Set '`wsrep_notify_cmd` = <path of galeranotify.py>' in your my.cnf file or in your Galera cluster `set global wsrep_notify_cmd="<path of galeranotify.py>";`

5. Restart MySql if you edited my.cnf.

SELinux
-------

A SELinux policy (galeranotify.pp) is also included that allows the mysql user to connect to a standard remote smtp port (port 25).  If you are using an alternate SMTP port (common with SSL), this rule will not work for you.

Usage:

    semodule -i galeranotify.pp

This rule was generated on Centos 6.4 64-bit.  It may or may not work for your particular setup.
