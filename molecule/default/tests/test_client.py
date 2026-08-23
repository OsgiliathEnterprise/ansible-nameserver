"""Role testing files using testinfra."""

testinfra_hosts = ["client.osgiliath.test"]


def test_resolv_conf_updated(host):
    command = (
        "set -o pipefail && "
        "resolvectl status | grep -cE 'DNS Domain.*osgiliath\\.test'"
    )
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_reverse_dns_lookup(host):
    command = (
        "set -o pipefail && "
        "client_ip=$(ip route get 8.8.8.8 | grep -oP "
        "'src \\K[0-9.]+' | head -1) && "
        'getent hosts client.osgiliath.test | grep -c "$client_ip"'
    )
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1
