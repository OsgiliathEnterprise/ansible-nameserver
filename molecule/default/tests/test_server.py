"""Role testing files using testinfra."""
import os
import subprocess

testinfra_hosts = ["idm.osgiliath.test"]

# Mirrors the role's ``nameserver_reverse_zone_prefix`` default (24). Set the
# environment variable when a scenario overrides the prefix in its converge.
REVERSE_ZONE_PREFIX = int(os.environ.get("NAMESERVER_REVERSE_ZONE_PREFIX", "24"))


def _kinit():
    return "set -o pipefail && echo '123ADMin' | kinit admin > /dev/null && "


def _client_host(host):
    return host.get_host(
        "ansible://client.osgiliath.test?ansible_inventory="
        + os.environ["MOLECULE_INVENTORY_FILE"]
    )


def _client_ip(client_host):
    return client_host.run(
        "ip route get 8.8.8.8 | grep -oP 'src \\K[0-9.]+' | head -1"
    ).stdout.strip()


def _zone_name(ip, prefix=REVERSE_ZONE_PREFIX):
    octets = ip.split(".")
    n = prefix // 8
    return ".".join(octets[:n][::-1]) + ".in-addr.arpa"


def _ptr_name(ip, prefix=REVERSE_ZONE_PREFIX):
    octets = ip.split(".")
    n = prefix // 8
    return ".".join(octets[n:][::-1])


def _a_record_all(host):
    command = (
        _kinit()
        + 'ipa dnsrecord-find osgiliath.test --name="client" | '
        "grep 'A record:' | cut -d ':' -f2 | tr -d '[[:space:]]'"
    )
    with host.sudo():
        return host.run(command).stdout


def _client_record_ip(host):
    values = _a_record_all(host).split()
    return values[0] if values else ""


def test_ipa_zone_is_created(host):
    command = r"""set -o pipefail && echo '123ADMin'| \
    kinit admin > /dev/null && \
    ipa dnszone-find --pkey-only | \
    egrep -c '[0-9]{1,3}\.in-addr\.arpa\.'"""
    with host.sudo():
        cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_dns_entry_is_created(host):
    command = r"""set -o pipefail && echo '123ADMin' | \
    kinit admin > /dev/null && \
    ipa dnsrecord-find osgiliath.test --name="client" | \
    grep -c 'Number of entries returned 1'"""
    with host.sudo():
        cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_rev_dns_entry_is_created(host):
    zone = _zone_name(_client_record_ip(host))
    command = (
        _kinit()
        + "ipa dnsrecord-find "
        + zone
        + ' | grep -c '
        "'PTR record: client'"
    )
    with host.sudo():
        cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_forward_zone_allow_sync_ptr(host):
    command = (
        _kinit()
        + "ipa dnszone-find --all osgiliath.test"
        " | grep -i 'allow ptr sync' | grep -ci 'true'"
    )
    with host.sudo():
        cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_client_reverse_zone_exists(host):
    zone = _zone_name(_client_record_ip(host))
    command = (
        _kinit()
        + "ipa dnszone-find "
        + zone
        + " | grep -c "
        + "'Zone name:'"
    )
    with host.sudo():
        cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_ptr_record_named_by_zone_octets(host):
    client_ip = _client_record_ip(host)
    zone = _zone_name(client_ip)
    ptr_name = _ptr_name(client_ip)
    command = (
        _kinit()
        + "ipa dnsrecord-find "
        + zone
        + ' --name="'
        + ptr_name
        + '" | grep -c '
        "'PTR record: client'"
    )
    with host.sudo():
        cmd = host.run(command)
    assert int(cmd.stdout) >= 1


def test_a_record_matches_client_ip(host):
    client_host = _client_host(host)
    client_ip = _client_ip(client_host)
    values = _a_record_all(host).split()
    assert client_ip in values, (
        "A record values {!r} do not contain the client default-route IP "
        "{!r}".format(values, client_ip)
    )


def test_stale_ptr_self_healing(host):
    scenario_dir = os.environ["MOLECULE_SCENARIO_DIRECTORY"]
    inventory = os.environ["MOLECULE_INVENTORY_FILE"]
    project_dir = os.environ["MOLECULE_PROJECT_DIRECTORY"]
    roles_path = os.environ.get(
        "ANSIBLE_ROLES_PATH",
        os.pathsep.join(
            [
                os.path.join(project_dir, "..", "community"),
                os.path.join(project_dir, "..", "oss"),
                os.path.join(project_dir, ".."),
            ]
        ),
    )
    collections_path = os.environ.get(
        "ANSIBLE_COLLECTIONS_PATH",
        os.pathsep.join(
            [
                os.path.join(project_dir, "..", "community-collections"),
                os.path.join(
                    os.path.expanduser("~"), ".ansible", "collections"
                ),
            ]
        ),
    )
    env = dict(os.environ)
    env["ANSIBLE_CONFIG"] = os.path.join(scenario_dir, "ansible.cfg")
    env["ANSIBLE_ROLES_PATH"] = roles_path
    env["ANSIBLE_COLLECTIONS_PATH"] = collections_path

    client_host = _client_host(host)
    current_ip = _client_ip(client_host)
    octets = current_ip.split(".")
    current_last = int(octets[3])
    stale_last = current_last + 1 if current_last < 254 else current_last - 1
    stale_ip = ".".join(octets[:3] + [str(stale_last)])
    reverse_zone = _zone_name(current_ip)
    stale_ptr_name = _ptr_name(stale_ip)
    client_fqdn = "client.osgiliath.test"

    try:
        # setup: drift the client's A record to a stale IP (same zone) and
        # add a stale PTR for it. ``dnsrecord-mod`` sets the A value to the
        # stale IP so the role's delete task (which targets the stale IP's
        # PTR name) picks up the stale PTR.
        with host.sudo():
            host.run(
                _kinit()
                + "ipa dnsrecord-mod osgiliath.test client A="
                + stale_ip
            )
            host.run(
                _kinit()
                + "ipa dnsrecord-add "
                + reverse_zone
                + " "
                + stale_ptr_name
                + " PTR="
                + client_fqdn
            )

        # act: re-run the scenario's converge playbook
        subprocess.run(
            [
                "ansible-playbook",
                os.path.join(scenario_dir, "converge.yml"),
                "-i",
                inventory,
            ],
            env=env,
            check=True,
        )

        # assert: the stale PTR was deleted
        with host.sudo():
            stale_ptr_count = host.run(
                _kinit()
                + "ipa dnsrecord-find "
                + reverse_zone
                + " --name="
                + stale_ptr_name
                + " | grep -c 'PTR record:'"
            ).stdout.strip()
        assert int(stale_ptr_count) == 0, (
            "stale PTR still present (count=" + stale_ptr_count + ")"
        )

        # assert: the A record contains the client's current IP
        assert current_ip in _a_record_all(host), (
            "A record does not contain the client's current IP " + current_ip
        )
    finally:
        # teardown: restore the A record to the client's current IP and remove
        # any stale PTR the test created, leaving the environment clean
        # (a no-op for the PTR delete if the converge already removed it)
        with host.sudo():
            host.run(_kinit() + "ipa dnsrecord-del osgiliath.test client")
            host.run(
                _kinit()
                + "ipa dnsrecord-add osgiliath.test client A=" + current_ip
            )
            host.run(
                _kinit()
                + "ipa dnsrecord-del "
                + reverse_zone
                + " "
                + stale_ptr_name
            )
