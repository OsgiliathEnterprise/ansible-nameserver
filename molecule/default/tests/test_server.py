"""Role testing files using testinfra."""
testinfra_hosts = ["idm.osgiliath.test"]


def test_ipa_zone_is_created(host):
    command = r"""set -o pipefail && echo '123ADMin'| \
    kinit admin > /dev/null && \
    ipa dnszone-find --pkey-only | \
    egrep -c '[0-9]{1,3}\.in-addr\.arpa\.'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_dns_entry_is_created(host):
    command = r"""set -o pipefail && echo '123ADMin' | \
    kinit admin > /dev/null && \
    ipa dnsrecord-find osgiliath.test --name="client" | \
    grep -c 'Number of entries returned 1'"""
    cmd = host.run(command)
    assert int(cmd.stdout) >= 1
