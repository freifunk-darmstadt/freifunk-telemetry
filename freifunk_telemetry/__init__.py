#!/usr/bin/env python3
import argparse
import logging
import pprint

from freifunk_telemetry.dhcp import read_dhcp_leases
from freifunk_telemetry.fastd import read_from_fastd_socket, get_fastd_process_stats, read_fastd
from freifunk_telemetry.graphite import write_to_graphite
from freifunk_telemetry.network import read_interface_counters, read_snmp, read_snmp6, read_conntrack, read_neigh
from freifunk_telemetry.system import read_context_switches, read_load

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', dest='test', action='store_true', default=False,
                        help='run in test mode (echoes output)')

    args = parser.parse_args()

    update = {}

    for plugin in [read_interface_counters,
                   read_load,
                   read_neigh,
                   read_conntrack,
                   read_snmp,
                   read_snmp6,
                   read_context_switches,
                   read_fastd,
                   read_dhcp_leases]:
        try:
            plugin(update)
        except Exception as e:
            logger.exception(e)

    if args.test:
        pprint.pprint(update)
    else:
        write_to_graphite(update)


if __name__ == "__main__":
    main()
