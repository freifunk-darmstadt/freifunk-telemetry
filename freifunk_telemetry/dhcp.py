import isc_dhcp_filter


def read_dhcp_leases(update):
    try:
        leases = isc_dhcp_filter.parse('/var/lib/dhcp/dhcpd.leases')
    except FileNotFoundError:
        return
    else:
        update['dhcpd.count'] = len(list(leases))
        update['dhcpd.active'] = len(list(leases.active))
        update['dhcpd.valid'] = len(list(leases.valid))
        update['dhcpd.current'] = len(list(leases.current))
