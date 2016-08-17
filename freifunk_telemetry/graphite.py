import socket
import time

from freifunk_telemetry.util import get_socket


def write_to_graphite(data, prefix='freifunk', hostname=None):
    if hostname is None:
        hostname = socket.gethostname()
    if '.' in hostname:
        hostname = hostname.split('.')[0]
    now = time.time()
    with get_socket('stats.darmstadt.freifunk.net', 2013) as s:
        for key, value in data.items():
            line = "%s.%s.%s %s %s\n" % (prefix, hostname, key, value, now)
            s.sendall(line.encode('latin-1'))
