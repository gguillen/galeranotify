#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 sts=4 et
#
# galeranotify - persistant storage backend
#
# Copyright (c) Jan-Jonas Sämann <sprinterfreak@binary-kitchen.de>, 2019
# available under the ISC licence

import sys
import yaml
import tempfile
import collections

class DatabaseFactory(collections.MutableMapping,dict):
    _state_changed = False
    _prop = {}

    def __init__(self, persistance_file):
        self.persistance_file = persistance_file
        try:
            with file(self.persistance_file, 'r') as fh:
                self._prop = yaml.load(fh, Loader=yaml.SafeLoader)
        except IOError, e:
            self._prop = {}
            self._state_changed = True
            pass

    def __getitem__(self, key):
        return self._prop[key]

    def __setitem__(self, key, value):
        if key not in self._prop or self._prop[key] != value:
            self._state_changed = True
        self._prop[key] = value

    def __iter__(self):
        return iter(self._prop)

    def __len__(self):
        return len(self._prop)

    def changed(self):
        return (self._state_changed or False)

    def __del__(self):
        try:
            with file(self.persistance_file, 'w') as fh:
                yaml.dump(self._prop, fh, explicit_start=True)
        except IOError, e:
            sys.stderr.write('Can not write database file: {} ({})\n'.format(self.persistance_file, e))
            pass
