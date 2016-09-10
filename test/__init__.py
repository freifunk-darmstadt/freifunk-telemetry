import os
import socket
import tempfile
import threading
import unittest.mock
from collections import namedtuple
from contextlib import contextmanager
from io import StringIO
from unittest import TestCase

from freifunk_telemetry import read_conntrack
from freifunk_telemetry import read_context_switches
from freifunk_telemetry import read_dhcp_leases
from freifunk_telemetry import read_fastd
from freifunk_telemetry import read_interface_counters
from freifunk_telemetry import read_load
from freifunk_telemetry import read_snmp
from freifunk_telemetry import read_snmp6
from freifunk_telemetry import read_neigh
from freifunk_telemetry import write_to_graphite
from freifunk_telemetry.util import get_unix_socket


def read_test_data(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, 'files', filename), 'r') as fh:
        return fh.read()


@contextmanager
def mock_open_read(filename_data):
    def _open(filename, mode='r'):
        return StringIO(filename_data[filename])

    with unittest.mock.patch('builtins.open', _open) as m:
        yield m


class SystemTest(TestCase):
    def test_read_load(self):
        update = {}
        read_load(update)

        for key in ['load.15', 'load.5', 'load.1']:
            self.assertIn(key, update, key)
            value = update[key]
            float(value)  # ensure it doesn't raise

    def test_read_context_switches(self):
        update = {}
        read_context_switches(update)

        self.assertIn('context_switches', update)
        int(update['context_switches'])


class NetworkTest(TestCase):
    def test_read_conntrack(self):
        update = {}
        mock_data = {
            '/proc/sys/net/netfilter/nf_conntrack_max': '1000\n',
            '/proc/sys/net/netfilter/nf_conntrack_count': '100\n',
        }

        with mock_open_read(mock_data):
            read_conntrack(update)

        self.assertIn('netfilter.count', update)
        self.assertIn('netfilter.max', update)
        self.assertEqual(update['netfilter.count'], '100')
        self.assertEqual(update['netfilter.max'], '1000')

    def test_read_snmp6(self):
        update = {}

        with mock_open_read({'/proc/net/snmp6': read_test_data('snmp6')}):
            read_snmp6(update)

        keys = "Ip6InReceives Ip6InHdrErrors Ip6InTooBigErrors Ip6InNoRoutes Ip6InAddrErrors Ip6InUnknownProtos Ip6InTruncatedPkts Ip6InDiscards Ip6InDelivers Ip6OutForwDatagrams Ip6OutRequests Ip6OutDiscards Ip6OutNoRoutes Ip6ReasmTimeout Ip6ReasmReqds Ip6ReasmOKs Ip6ReasmFails Ip6FragOKs Ip6FragFails Ip6FragCreates Ip6InMcastPkts Ip6OutMcastPkts Ip6InOctets Ip6OutOctets Ip6InMcastOctets Ip6OutMcastOctets Ip6InBcastOctets Ip6OutBcastOctets Ip6InNoECTPkts Ip6InECT1Pkts Ip6InECT0Pkts Ip6InCEPkts Icmp6InMsgs Icmp6InErrors Icmp6OutMsgs Icmp6OutErrors Icmp6InCsumErrors Icmp6InDestUnreachs Icmp6InPktTooBigs Icmp6InTimeExcds Icmp6InParmProblems Icmp6InEchos Icmp6InEchoReplies Icmp6InGroupMembQueries Icmp6InGroupMembResponses Icmp6InGroupMembReductions Icmp6InRouterSolicits Icmp6InRouterAdvertisements Icmp6InNeighborSolicits Icmp6InNeighborAdvertisements Icmp6InRedirects Icmp6InMLDv2Reports Icmp6OutDestUnreachs Icmp6OutPktTooBigs Icmp6OutTimeExcds Icmp6OutParmProblems Icmp6OutEchos Icmp6OutEchoReplies Icmp6OutGroupMembQueries Icmp6OutGroupMembResponses Icmp6OutGroupMembReductions Icmp6OutRouterSolicits Icmp6OutRouterAdvertisements Icmp6OutNeighborSolicits Icmp6OutNeighborAdvertisements Icmp6OutRedirects Icmp6OutMLDv2Reports Udp6InDatagrams Udp6NoPorts Udp6InErrors Udp6OutDatagrams Udp6RcvbufErrors Udp6SndbufErrors Udp6InCsumErrors Udp6IgnoredMulti UdpLite6InDatagrams UdpLite6NoPorts UdpLite6InErrors UdpLite6OutDatagrams UdpLite6RcvbufErrors UdpLite6SndbufErrors UdpLite6InCsumErrors"
        for key in keys.split(" "):
            self.assertIn('ipv6.%s' % key, update)

    def test_read_snmp(self):
        update = {}

        with mock_open_read({'/proc/net/snmp': read_test_data('snmp')}):
            read_snmp(update)

        for key, value in [
            ('Icmp.InErrors', '34'),
            ('UdpLite.IgnoredMulti', '0'),
            ('Ip.Forwarding', '1'),
            ('Ip.FragCreates', '22')
        ]:
            k = 'ipv4.%s' % key
            self.assertIn(k, update)
            self.assertEqual(update[k], value)

    def test_read_interface_counters(self):
        update = {}
        with mock_open_read({'/proc/net/dev': read_test_data('dev')}):
            read_interface_counters(update)

        for interface in ['ffda-vpn', 'ffda-transport', 'eth0', 'ffda-br']:
            self.assertIn('{}.rx.packets'.format(interface), update)
            self.assertIn('{}.rx.bytes'.format(interface), update)
            self.assertIn('{}.tx.packets'.format(interface), update)
            self.assertIn('{}.tx.bytes'.format(interface), update)

            int(update['{}.rx.packets'.format(interface)])
            int(update['{}.tx.packets'.format(interface)])


class UnixSocketServer(threading.Thread):
    def __init__(self, content):
        super().__init__()
        self.tmpfile = tempfile.NamedTemporaryFile()
        self.tmpfile.close()
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.tmpfile.name)
        self.socket.listen(1)
        self.socket.settimeout(0.5)
        self.content = content
        self._run = False

    def run(self):
        self._run = True
        while self._run:
            try:
                conn, add = self.socket.accept()
            except socket.timeout:
                pass
            else:
                conn.send(self.content)
                conn.close()

    def join(self):
        self._run = False
        super().join()
        self.socket.close()
        self.tmpfile.close()


class FastdTest(TestCase):
    def setUp(self):
        self.fakeServer = UnixSocketServer(read_test_data('fastd-ffda-vpn.json').encode('utf-8'))
        self.fakeServer.start()

    def tearDown(self):
        self.fakeServer.join()

    def test_read_process_stats(self):
        update = {}

        FakeProcess = namedtuple('Process', ['pid', 'name'])

        def fake_process_iter():
            return [FakeProcess(1337, lambda: 'fastd')]

        with unittest.mock.patch('freifunk_telemetry.fastd.psutil.process_iter', fake_process_iter):
            with mock_open_read({
                '/proc/1337/net/udp': read_test_data('udp'),
                '/proc/1337/net/udp6': read_test_data('udp6'),
            }):
                read_fastd(update)

        self.assertIn('fastd.drops', update)
        self.assertEqual(update['fastd.drops'], 23)

    def test_read_fastd_socket(self):
        update = {}

        def fake_os_path_exists(path):
            return path == '/run/fastd-ffda-vpn.sock'

        def fake_get_unix_socket(filename):
            return get_unix_socket(self.fakeServer.tmpfile.name)

        with unittest.mock.patch('os.path.exists', fake_os_path_exists):
            with unittest.mock.patch('freifunk_telemetry.fastd.get_unix_socket', fake_get_unix_socket):
                read_fastd(update)

        for key in [
            'peers.count',
            'peers.online',
            'rx.packets',
            'rx.bytes',
            'rx.reordered.bytes',
            'rx.reordered.packets',
            'tx.bytes',
            'tx.packets',
            'tx.dropped.bytes',
            'tx.dropped.packets',
        ]:
            self.assertIn('fastd.0.{}'.format(key), update)

        self.assertEqual(update['fastd.0.peers.count'], 5)
        self.assertEqual(update['fastd.0.peers.online'], 2)
        self.assertEqual(update['fastd.0.rx.packets'], 36226127)
        self.assertEqual(update['fastd.0.rx.bytes'], 7220993395)
        self.assertEqual(update['fastd.0.tx.packets'], 49408918)
        self.assertEqual(update['fastd.0.tx.bytes'], 29046160174)
        self.assertEqual(update['fastd.0.tx.dropped.bytes'], 0)
        self.assertEqual(update['fastd.0.tx.dropped.packets'], 0)
        self.assertEqual(update['fastd.0.rx.reordered.bytes'], 15372313)
        self.assertEqual(update['fastd.0.rx.reordered.packets'], 90699)


class TestGraphite(TestCase):
    def test_write_to_graphite(self):
        update = dict(foo=123)

        def fake_hostname():
            return 'ranzhost.baz'

        class FakeSocket:
            send_data = ''

            def sendall(self, data):
                self.send_data += data.decode('latin-1')

            def __getattr__(self, item):
                def foo(*args, **kwargs):
                    pass

                return foo

        socket = FakeSocket()

        def fake_socket():
            return socket

        with unittest.mock.patch('freifunk_telemetry.util.socket.socket', fake_socket):
            with unittest.mock.patch('freifunk_telemetry.graphite.socket.gethostname', fake_hostname):
                with unittest.mock.patch('freifunk_telemetry.graphite.time.time', lambda: 123.12345):
                    write_to_graphite(update)

        self.assertTrue(socket.send_data.endswith('\n'))
        parts = socket.send_data.strip().split(' ')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], 'freifunk.ranzhost.foo')
        self.assertEqual(parts[1], '123')
        self.assertEqual(parts[2], '123.12345')
        self.assertGreater(len(socket.send_data), 0)


class TestDHCP(TestCase):
    def test_read_dhcp_leases(self):
        update = {}

        with mock_open_read({'/var/lib/dhcp/dhcpd.leases': read_test_data('dhcpd.leases')}):
            read_dhcp_leases(update)

        self.assertIn('dhcpd.count', update)
        self.assertIn('dhcpd.active', update)
        self.assertIn('dhcpd.valid', update)
        self.assertIn('dhcpd.current', update)

        self.assertEqual(update['dhcpd.count'], 5)
        self.assertEqual(update['dhcpd.active'], 0)
        self.assertEqual(update['dhcpd.valid'], 0)
        self.assertEqual(update['dhcpd.current'], 0)


class TestNeigh(TestCase):
    _if_nameindex = {
        0: 'lo',
        1: 'en0',
        2: 'wl0'
    }

    def test_neighbour_table_size(self):
        def fake_if_nameindex():
            return self._if_nameindex.items()

        class FakeIPRoute:
            def get_neighbours(_, family, ifindex, **kwargs):
                self.assertIn(family, [socket.AF_INET, socket.AF_INET6])
                self.assertLessEqual(ifindex, len(self._if_nameindex))

                return [0]*(4 if family == socket.AF_INET else 6)

        update = {}

        with unittest.mock.patch('freifunk_telemetry.network.socket.if_nameindex', fake_if_nameindex):
            with unittest.mock.patch('freifunk_telemetry.network.pyroute2.IPRoute', FakeIPRoute):
                read_neigh(update)

        for idx, ifname in fake_if_nameindex():
            self.assertIn('ipv4.neigh.%s.count' % ifname, update)
            self.assertIn('ipv6.neigh.%s.count' % ifname, update)
            self.assertEqual(update['ipv4.neigh.%s.count' % ifname], 4)
            self.assertEqual(update['ipv6.neigh.%s.count' % ifname], 6)

        for proto in ['ipv4', 'ipv6']:
            self.assertIsInstance(int(update['%s.neigh.gc_thresh1' % proto]), int)
            self.assertIsInstance(int(update['%s.neigh.gc_thresh2' % proto]), int)
            self.assertIsInstance(int(update['%s.neigh.gc_thresh3' % proto]), int)
