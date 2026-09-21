"""Evidence helpers for Cassandra-driver coordinator selection."""

POLICY_NAME = "TokenAwarePolicy(DCAwareRoundRobinPolicy)"


def host_address(host):
    """Return a stable address string for a driver Host or test double."""
    address = getattr(host, "address", None)
    if address is not None:
        return str(address)
    return str(host).rsplit(":", 1)[0]


class DriverRoutingEvidence:
    """Record driver-visible hosts and the coordinator it actually selected.

    This class does not choose a host. TokenAwarePolicy and its
    DCAwareRoundRobinPolicy child own coordinator selection.
    """

    def __init__(self, address_to_node, local_dc):
        self.address_to_node = dict(address_to_node)
        self.local_dc = local_dc
        self.operation_index = 0

    def node_name(self, host):
        if host is None:
            return None
        address = host_address(host)
        return self.address_to_node.get(address, address)

    def begin(self, hosts):
        eligible = sorted(
            self.node_name(host)
            for host in hosts
            if getattr(host, "is_up", True) is not False
            and getattr(host, "datacenter", self.local_dc) == self.local_dc
        )
        route = {
            "policy": POLICY_NAME,
            "local_dc": self.local_dc,
            "operation_index": self.operation_index,
            "eligible_nodes": eligible,
        }
        self.operation_index += 1
        return route

    def finish(self, route, coordinator_host, attempted_hosts):
        route["selected_node"] = self.node_name(coordinator_host)
        route["attempted_nodes"] = [self.node_name(host) for host in attempted_hosts]
        return route
