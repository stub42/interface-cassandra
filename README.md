= Cassandra interface for charms.reactive Juju charms

charms.reactive Endpoint for Cassandra clients. To use,
add 'interface:cassandra' to your layer.yaml:

```yaml
includes:
    - layer:basic
    - interface:cassandra
```

== Flags

- `endpoint.{endpoint_name}.joined`: The relation has been joined, but may not be available.
- `endpoint.{endpoint_name}.available`: The Cassandra database is available.

== Usage

For a relation defined in metadata.yaml named 'mydb':

```python
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
```

== Details

The 'details' property on the endpoint provides a list-like collection
(a charms.reactive.endpoint.KeyList) of CassandraDetails objects:

```python
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
```

The list may be iterated over or access by relation id:

```python
>>> ep = charms.reactive.endpoint_from_flag('endpoint.mydb.available')
>>> any_details = ep.details[0]
>>> all_details = set(ep.details)
>>> rel_details = ep.details['db:0']
```
