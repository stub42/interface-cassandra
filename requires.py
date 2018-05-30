# Copyright 2015-2018 Canonical Ltd.
#
# This file is part of the Cassandra Charm for Juju.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import configparser
import io
import os.path

from charmhelpers.core import host
from charms import reactive
from charms.reactive import (
    endpoints,
    when,
)


class CassandraDetails(object):
    relation_id = None
    username = None  # None if authentication is disabled
    password = None
    cluster_name = None
    datacenter = None
    rack = None
    native_transport_port = None
    rpc_port = None
    hosts = None  # set of IP addresses


class CassandraEndpoint(reactive.Endpoint):
    '''
    Usage:
        from charms import reactive
        from charms.reactive.flags import register_trigger

        register_trigger('endpoint.mydb.changed', clear_flag='myapp.configured')

        @when('endpoint.mydb.available')
        @when_not('myapp.configured')
        def configure():
            ep = reactive.endpoint_from_flag('endpoint.mydb.available')
            do_config(ep.details)
            ep.write_cqlshrc('root')
            reactive.set_flag('myapp.configured')
    '''
    @when('endpoint.{endpoint_name}.changed.host')
    def server_changed(self):
        self.set_available()
        reactive.clear_flag(self.expand_name('endpoint.{endpoint_name}.changed.host'))

    @when('endpoint.{endpoint_name}.departed')
    def server_departed(self):
        self.set_available()

    def set_available(self):
        reactive.toggle_flag(self.expand_name('endpoint.{endpoint_name}.available'),
                             len(self.details) > 0)

    @when('endpoint.{endpoint_name}.changed')
    def changed(self):
        # We need to reset the .changed state, so do it. Charms can react to it
        # by registering a trigger.
        reactive.clear_flag(self.expand_name('endpoint.{endpoint_name}.changed'))

    @property
    def details(self):
        '''Cassandra server details

        Returns a charms.reactive.endpoint.KeyList of CassandraDetails
        instances. This object can be iterated over or accessed by relation id.

        >>> ep = reactive.endpoint_from_flag('endpoint.mydb.available')
        >>> first_details = ep.details[0] if ep.details else None
        >>> all_details = set(ep.details)
        >>> rel_details = ep.details['db:0']

        '''
        return endpoints.KeyList((d for d in (self._details(rel) for rel in self.relations) if d is not None),
                                 'relation_id')

    def _details(self, rel):
        raw = rel.joined_units.received_raw
        if 'username' not in raw:
            return None
        d = CassandraDetails()
        d.relation_id = rel.relation_id
        for k in ['username', 'password', 'cluster_name', 'datacenter', 'rack', 'native_transport_port', 'rpc_port']:
            setattr(d, k, raw.get(k))
        d.hosts = set(u.received_raw.get('host') for u in rel.joined_units if 'host' in u.received_raw)
        return d

    def write_cqlshrc(self, owner):
        '''Helper to write a cqlsh configuration file

        Creates a ~user/.cassandra/cqlshrc for interactive use with
        the cqlsh command line tool.
        '''
        cqlshrc_path = os.path.expanduser('~{}/.cassandra/cqlshrc'.format(owner))

        details = self.details
        if not details:
            if os.path.exists(cqlshrc_path):
                os.remove(cqlshrc_path)
            return
        first = details[0]

        cqlshrc = configparser.ConfigParser(interpolation=None)
        cqlshrc.read([cqlshrc_path])
        cqlshrc.setdefault('authentication', {})
        if first.username:
            cqlshrc['authentication']['username'] = first.username
            cqlshrc['authentication']['password'] = first.password
        cqlshrc.setdefault('connection', {})
        cqlshrc['connection']['hostname'] = first.hosts.pop()
        cqlshrc['connection']['port'] = str(first.native_transport_port)

        ini = io.StringIO()
        cqlshrc.write(ini)
        host.mkdir(os.path.dirname(cqlshrc_path), perms=0o700, owner=owner)
        host.write_file(cqlshrc_path, ini.getvalue().encode('UTF-8'), perms=0o600, owner=owner)
