"""Role testing files using testinfra."""


def test_hosts_file(host):
    """Validate /etc/hosts file."""
    f = host.file("/etc/hosts")

    assert f.exists
    assert f.user == "root"
    assert f.group == "root"


def test_hosts_file_contains_the_new_entry(host):
    command = r"""cat /etc/hosts | \
    egrep -c '127\.0\.0\.1\sdummy.dum.com\s'"""
    cmd = host.run(command)
    assert '1' in cmd.stdout


def test_hosts_file_contains_the_new_ip6_entry(host):
    command = r"""cat /etc/hosts | \
    egrep -c '::1\sdummy.dum.com\s'"""
    cmd = host.run(command)
    assert '1' in cmd.stdout


def test_hostname_is_updated(host):
    """Validate /etc/hosts file."""
    command = r"""hostname | \
    egrep -c '^dummy.dum.com$'"""
    cmd = host.run(command)
    assert '1' in cmd.stdout
