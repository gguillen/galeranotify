galeranotify
============

Python E-Mail script for use with Galera wsrep\_notify\_cmd

This script immediately generates an E-Mail if Your cluster state changes, so You won't miss a second.
Also duplicates are dropped. Using Galera for instance in combination with commercial backup software like Comvault leads to a whole buch of notifications without a state change.
This is caused by Comvault illegaly LOCKing slave-tables while dumping data out of the cluster. Since the LOCK didn't last too long, the locked slave is pulled back to synced shortly after.
Each locked table causes an E-Mail. Therefore galeranotify remembers its previous state and drops the message if no state change has really happend. 


Installation
------

Install it via pip is the easiest way
```
pip install git+https://git.binary-kitchen.de/sprinterfreak/galeranotify
```

- Place the galeranotify.yml under /etc/mysql and configure it.
- Set 'wsrep\_notify\_cmd = galeranotify' in your my.cnf file
- Restart MySql.

SELinux
-------

A SELinux policy (galeranotify.pp) is also included that allows the mysql user to connect to a standard remote smtp port (port 25).  If you are using an alternate SMTP port (common with SSL), this rule will not work for you.

Usage:

    semodule -i galeranotify.pp

This rule was generated on Centos 6.4 64-bit.  It may or may not work for your particular setup.
