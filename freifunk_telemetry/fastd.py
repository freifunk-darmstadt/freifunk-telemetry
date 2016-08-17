import json
import os

import psutil
from freifunk_telemetry.util import get_unix_socket


def read_from_fastd_socket(filename):
    with get_unix_socket(filename) as client:
        strings = []
        while True:
            s = client.recv(8096)
            if not s:
                break
            strings.append(s.decode('utf-8'))

        data = json.loads(''.join(strings))
        # pprint.pprint(data['statistics'])

        online_peers = len([None for name, d in data['peers'].items() if d['connection']])

        return {
            'peers.count': len(data['peers']),
            'peers.online': online_peers,
            'rx.packets': data['statistics']['rx']['packets'],
            'rx.bytes': data['statistics']['rx']['bytes'],
            'rx.reordered.bytes': data['statistics']['rx_reordered']['bytes'],
            'rx.reordered.packets': data['statistics']['rx_reordered']['packets'],
            'tx.bytes': data['statistics']['tx']['bytes'],
            'tx.packets': data['statistics']['tx']['packets'],
            'tx.dropped.bytes': data['statistics']['tx_dropped']['bytes'],
            'tx.dropped.packets': data['statistics']['tx_dropped']['packets'],
        }


def get_fastd_process_stats():
    for proc in psutil.process_iter():
        if proc.name() == 'fastd':
            # 11905: 00000000000000000000000001000000:0035 00000000000000000000000000000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 4469598 2 ffff880519be5100 0
            drop_count = 0
            for proto in ['udp', 'udp6']:
                with open('/proc/{}/net/{}'.format(proc.pid, proto), 'r') as fh:
                    for line in (line.strip() for line in fh.read().split('\n')):
                        if not line:
                            continue

                        if line.startswith('sl'):
                            continue

                        parts = line.split(' ')

                        drop_count += int(parts[-1])

            return drop_count

    return None


def read_fastd(update):
    fastd_sockets = (
        ('0', '/run/fastd-ffda-vpn.sock'),
        ('1', '/run/fastd-ffda-vpn1.sock'),
    )

    for name, filename in fastd_sockets:
        if not os.path.exists(filename):
            continue

        data = read_from_fastd_socket(filename)
        if len(data) > 0:
            update.update({'fastd.%s.%s' % (name, key): value for (key, value) in data.items()})

    fastd_drops = get_fastd_process_stats()
    if fastd_drops:
        update['fastd.drops'] = fastd_drops
