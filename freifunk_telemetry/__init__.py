#!/usr/bin/env python3
import logging
import pprint

from freifunk_telemetry.fastd import read_from_fastd_socket, get_fastd_process_stats, read_fastd
from freifunk_telemetry.graphite import write_to_graphite
from freifunk_telemetry.network import read_interface_counters, read_snmp, read_snmp6, read_conntrack
from freifunk_telemetry.system import read_context_switches, read_load

logger = logging.getLogger(__name__)


def main():
    update = {}

    read_interface_counters(update)
    read_load(update)
    read_conntrack(update)
    read_snmp(update)
    read_snmp6(update)
    read_context_switches(update)
    read_fastd(update)

    pprint.pprint(update)
    #write_to_graphite(update)


if __name__ == "__main__":
    main()
