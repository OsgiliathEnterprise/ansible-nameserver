"""Role testing files using testinfra."""


def test_hosts_file_contains_the_new_entry(host):
    command = r"""cat /etc/hosts | \
    egrep -c '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\sdummy.dum.com'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_hosts_file_contains_the_new_ip6_entry(host):
    command = r"""cat /etc/hosts | \
    egrep -c \
    '\w{0,4}:\w{0,4}:\w{0,4}:\w{0,4}:\w{0,4}:\w{0,4}\sdummy.dum.com'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_hostname_is_updated(host):
    command = r"""hostname | \
    egrep -c '^dummy.dum.com$'"""
    cmd = host.run(command)
    assert '1' in cmd.stdout


def test_resolv_conf_updated(host):
    command = r"""cat /etc/resolv.conf | grep -c nameserver"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 2


def test_lookup_resolves_google(host):
    command = r"""nslookup google.fr 127.0.0.1 | \
        grep -Pzoc 'Non-authoritative answer:\nName:\s+google.fr'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_lookup_resolves_node_as_client(host):
    command = r"""nslookup node0.osgiliath.net | \
    grep -c '192.168.1.1'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_lookup_resolves_reverse(host):
    command = r"""nslookup 192.169.0.2 | \
    grep -c 'node0.osgiliath.net.169.192.in-addr.arpa'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1
