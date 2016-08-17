import isc_dhcp_filter


def read_dhcp_leases(update):
    try:
        leases = isc_dhcp_filter.parse('/var/lib/dhcp/dhcpd.leases')
    except FileNotFoundError:
        return
    else:
        update['dhcpd.count'] = leases.count()
        update['dhcpd.active'] = leases.active.count()
        update['dhcpd.valid'] = leases.valid.count()
        update['dhcpd.current'] = leases.current.count()
