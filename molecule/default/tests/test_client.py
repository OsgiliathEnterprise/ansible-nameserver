"""Role testing files using testinfra."""
testinfra_hosts = ["client.osgiliath.test"]


def test_resolv_conf_updated(host):
    command = r"""cat /etc/systemd/resolved.conf.d/head.conf | \
    grep -c 'Domains=~osgiliath.test'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


# TODO test client registration & reverse dns lookup
