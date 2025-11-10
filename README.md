Nameserver
=========

* Galaxy: [![Ansible Galaxy](https://img.shields.io/badge/galaxy-tcharl.ansible_nameserver-660198.svg?style=flat)](https://galaxy.ansible.com/tcharl/ansible_nameserver)
* Lint,  & requirements: ![Molecule](https://github.com/OsgiliathEnterprise/ansible-nameserver/workflows/Molecule/badge.svg)
* Tests: [![Build Status](https://travis-ci.com/OsgiliathEnterprise/ansible-nameserver.svg?branch=master)](https://travis-ci.com/OsgiliathEnterprise/ansible-nameserver)
* Chat: [![Join the chat at https://gitter.im/OsgiliathEnterprise/platform](https://badges.gitter.im/OsgiliathEnterprise/platform.svg)](https://gitter.im/OsgiliathEnterprise/platform?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Registers dns entries for client machine in freeipa

Requirements
------------

Unix machine :-)
A freeipa server running somewhere (using the freeipa_server role for example) and the securehost role to have the host joined to the freeipa domain
Look at [requirements.txt](./requirements.txt) and [requirements-dev.txt](./requirements-dev.txt)

Role Variables
--------------

Configuring DNS reverse zone and DNS record for freeipa (triggered when your host is in the 'ipaclients' ansible group) and ensure that there is a dns entry for the hostname, but be sure that ipa is correctly configured before (for example using the tcharl.securehost role)

```
preferred_nic: eth0 # optional, to compute ip, otherwise will take the default_ipv4
company_realm_password: admin123 # Freeipa admin password
company_domain: osgiliath.test
```

Dependencies
------------

see [requirements file](./requirements-standalone.yml) and [requirement collection file](./requirements-collections.yml)

License
-------

[Apache-2](https://www.apache.org/licenses/LICENSE-2.0)

Author Information
------------------

* Twitter [@tcharl](https://twitter.com/Tcharl)
* Github [@tcharl](https://github.com/Tcharl)
* LinkedIn [Charlie Mordant](https://www.linkedin.com/in/charlie-mordant-51796a97/)
