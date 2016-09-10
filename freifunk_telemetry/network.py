import itertools
import re
import socket

import pyroute2

from freifunk_telemetry.util import pairwise


def read_interface_counters(update):
    device_name_mapping = {
        'freifunk': 'ffda-br',
        'bat0': 'ffda-bat',
        'mesh-vpn': 'ffda-vpn'
    }
    device_whitelist = [
        'eth0',
        'tun-ffrl-ber',
        'tun-ffrl-dus',
        'tun-ffrl-fra',
        'tun-ffda-gw01',
        'tun-ffda-gw02',
        'tun-ffda-gw03',
        'tun-ffda-gw04',
        'ffda-vpn',
        'ffda-bat',
        'ffda-br',
        'icvpn',
        'ffda-transport',
        'services',
    ]

    fields = [
        'bytes', 'packets', 'errs', 'drop', 'fifo',
        'frame', 'compressed', 'multicast',
    ]
    field_format = '(?P<{direction}_{field}>\d+)'

    pattern = re.compile(
        '^\s*(?P<device_name>[\w-]+):\s+' + '\s+'.join(
            itertools.chain.from_iterable((field_format.format(direction=direction, field=field)
                                           for field in fields) for direction in ['rx', 'tx'])
        )
    )

    with open('/proc/net/dev') as fh:
        lines = fh.readlines()
        for line in lines:
            m = pattern.match(line)
            if m:
                groupdict = m.groupdict()
                device_name = groupdict.pop('device_name')
                device_name = device_name_mapping.get(device_name, device_name)
                if device_name in device_whitelist or device_name.endswith('-vpn') or \
                        device_name.endswith('-bat') or \
                        device_name.endswith('-br') or \
                        device_name.endswith('-transport'):
                    for key, value in groupdict.items():
                        direction, metric = key.split('_')
                        update['%s.%s.%s' % (device_name, direction, metric)] = value


def read_conntrack(update):
    for key in ['count', 'max']:
        with open('/proc/sys/net/netfilter/nf_conntrack_%s' % key, 'r') as fh:
            update['netfilter.%s' % key] = fh.read().strip()


def read_snmp6(update):
    with open('/proc/net/snmp6', 'r') as fh:
        for line in fh.readlines():
            key, value = line.split(' ', 1)
            value = value.strip()
            update['ipv6.%s' % key] = value


def read_snmp(update):
    with open('/proc/net/snmp', 'r') as fh:
        for heading, values in pairwise(fh.readlines()):
            section, headings = heading.split(':')
            headings = headings.strip().split(' ')
            _, values = values.split(':')
            values = values.strip().split(' ')
            for key, value in zip(headings, values):
                update['ipv4.%s.%s' % (section, key)] = value


def read_neigh(update):
    ip_route = pyroute2.IPRoute()
    families = {
        'ipv4': socket.AF_INET,
        'ipv6': socket.AF_INET6,
    }
    for label, family in families.items():
        for idx, ifname in socket.if_nameindex():
            neigh = ip_route.get_neighbours(family=family, ifindex=idx)
            update['%s.neigh.%s.count' % (label, ifname)] = len(neigh)

        for key in ['gc_thresh1', 'gc_thresh2', 'gc_thresh3']:
            with open('/proc/sys/net/%s/neigh/default/%s' % (label, key), 'r') as fh:
                update['%s.neigh.%s' % (label, key)] = fh.read().strip()