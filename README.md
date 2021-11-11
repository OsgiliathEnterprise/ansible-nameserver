Nameserver
=========

* Galaxy: [![Ansible Galaxy](https://img.shields.io/badge/galaxy-tcharl.ansible_nameserver-660198.svg?style=flat)](https://galaxy.ansible.com/tcharl/ansible_nameserver)
* Lint,  & requirements: ![Molecule](https://github.com/OsgiliathEnterprise/ansible-nameserver/workflows/Molecule/badge.svg)
* Tests: [![Build Status](https://travis-ci.com/OsgiliathEnterprise/ansible-nameserver.svg?branch=master)](https://travis-ci.com/OsgiliathEnterprise/ansible-nameserver)
* Chat: [![Join the chat at https://gitter.im/OsgiliathEnterprise/platform](https://badges.gitter.im/OsgiliathEnterprise/platform.svg)](https://gitter.im/OsgiliathEnterprise/platform?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

This role configures the hostname of the machine and add the entry in /etc/hosts.
It is also able to setup a dns/reverse dns on a docker container, being the docker equivalent of [mrlesmithjr/bind](https://github.com/mrlesmithjr/ansible-bind) role

Requirements
------------

Unix machine :-)
* [ansible-containerization](https://galaxy.ansible.com/tcharl/ansible_containerization)
=> Can be installed using `molecule dependency`or  

Role Variables
--------------

### Configuring Host and hostname
```
hostname: "{{ inventory_hostname }}" # default
hosts_entries: # entries to add to /etc/hosts
  - name: idm.osgiliath.net
    ip: 192.168.122.1
  - name: infra.osgiliath.net
    ip: 192.168.122.2
```

### Configuring DNS (triggered when your host is in the 'bindmasters' ansible group, can also configure slaves with the 'bindslaves' group)

```
    bind_acls: # first way of configuring ACLs
      - name: lan
        networks:
         - 171.0.0.0/24
    bind_config: true
    company_domain: "osgiliath.test"
    bind_forward_zones: # configure DNS zone
      - zone: "{{ company_domain }}"
        expire: 2419200
        hostmaster: "hostmaster.{{ company_domain }}"
        masters: []
        nameservers:
         - "node0.{{ company_domain }}"
        records:
         - name: node0
           address: 192.168.1.1
           type: A
        soa: "host.{{ company_domain }}"
        refresh: 604800
        retry: 86400
        neg_cache_ttl: 604800
        ttl: 32
        slaves: []
    bind_forwarding_server: true # configures DNS forwarding
    bind_forwarders:
      - 8.8.8.8
    bind_manage_zones: true
    bind_reverse_zones:  # configures reverse DNS (192.168.0.2)
      - zone: "169.192"
        refresh: 604800
        retry: 86400
        ttl: 32
        soa: "{{ ansible_hostname }}.{{ company_domain }}"
        expire: 2419200
        hostmaster: "hostmaster.{{ company_domain }}"
        masters: []
        nameservers:
          - "node0.{{ company_domain }}"
        neg_cache_ttl: 604800
        slaves: []
        records:
          - name: "node0.{{ company_domain }}"
            address: "2.0"
```

### Adding the master DNS into a consumer resolv.conf (triggered when your host is in the 'bindclients' ansible group)

```
    bind_clients: bindclient # Will also add a master DNS reference within the client's resolv.conf entries
```

### Configuring DNS reverse zone and DNS record for freeipa (triggered when your host is in the 'ipaclients' ansible group) and ensure that there is a dns entry for the hostname, but be sure that ipa is correctly configured before (for example using the tcharl.securehost role)

```
preferred_nic: eth0 # optional, to compute ip, otherwise will take the default_ipv4
company_realm_password: admin123 # Freeipa admin password
company_domain: osgiliath.test
```

Dependencies
------------

see [requirements file](./requirements.yml) and [requirement collection file](./requirements-collections.yml)

License
-------


[Apache-2](https://www.apache.org/licenses/LICENSE-2.0)

Author Information
------------------

* Twitter [@tcharl](https://twitter.com/Tcharl)
* Github [@tcharl](https://github.com/Tcharl)
* LinkedIn [Charlie Mordant](https://www.linkedin.com/in/charlie-mordant-51796a97/)
