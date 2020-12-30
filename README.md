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
ns_hostname: "{{ inventory_hostname }}" # default
```

### Configuring DNS
```
    bind_acls: # first way of configuring ACLs
      - name: lan
        networks:
         - 171.0.0.0/24
    bind_clients: bindclient # Second way: adding hosts to these groups
    bind_config: true
    bind_pri_domain_name: "osgiliath.net"
    bind_forward_zones: # configure DNS zone
      - zone: "{{ bind_pri_domain_name }}"
        expire: 2419200
        hostmaster: "hostmaster.{{ bind_pri_domain_name }}"
        masters: []
        nameservers:
         - "node0.{{ bind_pri_domain_name }}"
        records:
         - name: node0
           address: 192.168.1.1
           type: A
        soa: "host.{{ bind_pri_domain_name }}"
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
        soa: "{{ ansible_hostname }}.{{ bind_pri_domain_name }}"
        expire: 2419200
        hostmaster: "hostmaster.{{ bind_pri_domain_name }}"
        masters: []
        nameservers:
          - "node0.{{ bind_pri_domain_name }}"
        neg_cache_ttl: 604800
        slaves: []
        records:
          - name: "node0.{{ bind_pri_domain_name }}"
            address: "2.0"
```

### Adding the master DNS into a consumer resolv.conf 

```
    bind_clients: bindclient # Will also add a master DNS reference within the client's resolv.conf entries
```


Dependencies
------------

  - name: tcharl.hostname
  - name: tcharl.containerization
  - name: robertdebock.reboot
  - name: robertdebock.bootstrap
  - name: robertdebock.core_dependencies

License
-------


[Apache-2](https://www.apache.org/licenses/LICENSE-2.0)

Author Information
------------------

* Twitter [@tcharl](https://twitter.com/Tcharl)
* Github [@tcharl](https://github.com/Tcharl)
* LinkedIn [Charlie Mordant](https://www.linkedin.com/in/charlie-mordant-51796a97/)
