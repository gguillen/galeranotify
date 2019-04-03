#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 sts=4 et
#
# galeranotify - configuration backend
#
# Copyright (c) Jan-Jonas Sämann <sprinterfreak@binary-kitchen.de>, 2019
# available under the ISC licence

import sys
import yaml
import socket
import operator
from functools import reduce

class ConfigFactory(dict):
    _defaults = {
        'hostname': socket.gethostname(),
        'smtp': {
            'server':'127.0.0.1',
            'port': 25,
            'ssl': True,
            'auth_enable': False,
            'username': None,
            'password': None
        },
        'email_from': 'galera@localhost',
        'email_to': 'root@localhost'
    }
    def __init__(self, cf):
        try:
            with file(cf, 'r') as fh:
                prop = yaml.load(fh, Loader=yaml.SafeLoader)
        except IOError, e:
            sys.stderr.write('Load configuration from {} failed with {}'.format(cf, e))
            prop = self._defaults
            pass

        self._prop = prop

    def __getitem__(self, key):
        if isinstance(key, tuple):
            try:
                return reduce(operator.getitem, key, self._prop)
            except:
                return reduce(operator.getitem, key, self._defaults)
        else:
            if key in self._prop:
                return self._prop[key]
            elif key in self._defaults:
                return self._defaults[key]

    def __setitem__(self, key, value):
        raise NotImplementedError('Config modify')

    def __iter__(self):
        return iter(self._prop)

    def __len__(self):
        return len(self._prop)

    def __str__(self):
        return repr(self._prop)
