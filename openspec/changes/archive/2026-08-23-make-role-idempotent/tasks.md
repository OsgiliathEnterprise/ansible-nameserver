# Tasks: Make the role idempotent

## 1. Audit baseline

- [x] 1.1 Inventory every `changed_when` / `failed_when` usage under `tasks/` and classify each task as read-only or state-changing; record the classification in `openspec/changes/make-role-idempotent/audit-note.md` (verify: the note lists every usage with file:line, module/command, classification, and the action taken)
- [x] 1.2 Confirm the two read-only tasks keep `changed_when: false` — `facts.yml` `hostname` lookup and the `kinit` + `ipa dnsrecord-find` query in `delete-outdated-ptr.yml` (verify: both tasks still carry `changed_when: false` with a short read-only comment; no other read-only usage exists)

## 2. Fix ipa_server.yml (design D2)

- [x] 2.1 Remove the blanket `failed_when: False` and its "too lazy" TODO comment from the reverse-zone `ipadnszone` task (verify: the task has no `failed_when`; `ansible-lint` passes; a second converge reports the task as `ok`/`changed: false` — if a specific benign error reproduces, replace the blanket suppression with an exact `failed_when` matching that one understood error plus an explanatory comment)

## 3. Fix ipa_dns_client.yml (design D3, D4)

- [x] 3.1 Add a delegated `ipadnszone` task at the top of `ipa_dns_client.yml` ensuring the client's own reverse zone (`name_from_ip: \"{{ nameserver_current_host_ip | ansible.utils.ipsubnet(nameserver_reverse_zone_prefix) }}\"`, `state: present`, delegated to `{{ groups[idm_group][0] }}`), placed before the A-record task; the zone size is controlled by the new `nameserver_reverse_zone_prefix` default variable (default `24`) (verify: on a fresh converge the client's reverse zone exists; on a re-converge the task reports `changed: false`)
- [x] 3.2 Remove the blanket `failed_when: False` and its "sh****tty error" comment from the A-record `ipadnsrecord` task (verify: the task has no `failed_when`; a second converge reports it as `ok`/`changed: false`)
- [x] 3.3 Remove the blanket `failed_when: False` and its "May have been created above" comment from the PTR `ipadnsrecord` task (verify: the task has no `failed_when`; a second converge reports it as `ok`/`changed: false`, proving the find-before-act module handles the already-created PTR idempotently)
- [x] 3.4 Add a `nameserver_reverse_zone_prefix` default variable (value `24`) to `defaults/main.yml` so the reverse-zone size is configurable; the zone-ensure (3.1), PTR-creation, and PTR-deletion tasks all derive the zone from `nameserver_current_host_ip` using this prefix instead of a hardcoded `/24` (verify: `defaults/main.yml` defines `nameserver_reverse_zone_prefix: 24`; no hardcoded `24`/`16` prefix remains in `tasks/`)

## 4. Rewrite delete-outdated-ptr.yml (design D5)

- [x] 4.1 Replace the hardcoded `client` record name in the `ipa dnsrecord-find` command with the record name derived from host facts (`{{ nameserver_current_host | replace('.' + company_domain, '') }}`) (verify: the command template renders the client's actual short hostname; a grep against `molecule/*/converge.yml` hostnames confirms the rendered value)
- [x] 4.2 Replace the fragile `when: outdated_record_ip.rc != 1` deletion gate with the exact gate `outdated_record_ip.rc == 0 and outdated_record_ip.stdout != '' and nameserver_current_host_ip != outdated_record_ip.stdout` (verify: on a re-converge with matching IPs the delete task is skipped; the old `rc != 1` condition is gone)
- [x] 4.3 Fix the delete task's `name` to `{{ outdated_record_ip.stdout.split()[nameserver_reverse_zone_prefix // 8:][::-1] | join('.') }}` (the stale IP's octets beyond the zone prefix, reversed — matching the creation task's naming for any prefix) and remove the broken `outdated_record_ip.msg`-based expression (verify: the task no longer references `outdated_record_ip.msg`; the rendered name equals the PTR name derived from the found IP for the configured prefix)
- [x] 4.4 Align the delete task's `zone_name` with the PTR-creation expression (`{{ nameserver_current_host_ip.split('.')[:nameserver_reverse_zone_prefix // 8][::-1] | join('.') }}.in-addr.arpa`), both derived from `nameserver_reverse_zone_prefix` (verify: the two zone expressions in `tasks/` are identical)
- [x] 4.5 Keep `changed_when: false` on the read-only query task and `failed_when: false` solely as a skip mechanism when the query cannot run (verify: the query task carries both with a short comment; the deletion gate in 4.2 makes a failed query skip the delete rather than fail the play)

## 5. Enable molecule idempotence (design D6)

- [x] 5.1 Enable `- idempotence` in `molecule/default/molecule.yml` `test_sequence` between `converge` and `side_effect` (verify: the `test_sequence` lists `idempotence` uncommented in that position)
- [x] 5.2 Enable `- idempotence` in `molecule/kvm/molecule.yml` `test_sequence` (verify: same as 5.1 for the kvm scenario)
- [x] 5.3 Enable `- idempotence` in `molecule/parallels/molecule.yml` `test_sequence` (verify: same as 5.1 for the parallels scenario)

## 6. Add feature coverage tests (spec: Feature coverage tests)

- [x] 6.1 Add `test_forward_zone_allow_sync_ptr` to `molecule/default/tests/test_server.py`: assert the `company_domain` forward zone reports `sync_ptr: TRUE` via `ipa dnszone-find` (verify: the test passes under `tox -e verify-monorepo -- --scenario-name=parallels`)
- [x] 6.2 Add `test_client_reverse_zone_exists` to `molecule/default/tests/test_server.py`: derive the client's reverse zone from the client's A-record IP using the configured `nameserver_reverse_zone_prefix` (the zone's octets, `prefix // 8` of them, reversed + `.in-addr.arpa`), and assert the zone exists in `ipa dnszone-find` (verify: the test passes under verify)
- [x] 6.3 Add `test_ptr_record_named_by_zone_octets` to `molecule/default/tests/test_server.py`: assert that in the zone from 6.2, the record named by the client IP's octets beyond the zone prefix (reversed) carries a PTR value equal to the client's FQDN (verify: the test passes under verify)
- [x] 6.4 Add `test_a_record_matches_client_ip` to `molecule/default/tests/test_server.py`: assert the client's A-record value equals the client's actual current IP, read from the client host's default-route source IP via `host.get_host` (verify: the test passes under verify)
- [x] 6.5 Add `test_reverse_dns_lookup` to `molecule/default/tests/test_client.py` (replacing the existing TODO comment): from the client, a reverse-DNS lookup of the client's FQDN resolves to the client's current IP (verify: the test passes under verify)
- [x] 6.6 Add `test_stale_ptr_self_healing` to `molecule/default/tests/test_server.py`: setup — `ipa dnsrecord-mod` the client's A record to a stale IP within the same reverse zone (same `nameserver_reverse_zone_prefix` network) and `ipa dnsrecord-add` a stale PTR for it; act — re-run the scenario's converge playbook via `subprocess` with the molecule environment (`ANSIBLE_CONFIG` = `$MOLECULE_SCENARIO_DIRECTORY/ansible.cfg`, inventory `$MOLECULE_INVENTORY_FILE`, `ANSIBLE_ROLES_PATH`/`ANSIBLE_COLLECTIONS_PATH` taken from the environment or derived from `$MOLECULE_PROJECT_DIRECTORY`); assert the stale PTR is deleted and the A record contains the client's current IP; teardown — restore the A record to the client's current IP (verify: the test passes under verify and leaves the A record restored)
- [x] 6.7 Replace the stale `molecule/kvm/tests/` directory (a diverged copy of the default tests, with tests commented out and missing `host.sudo()`) with a symlink to `../default/tests`, matching the `parallels` scenario, so every scenario runs the same suite (verify: `molecule/kvm/tests` is a symlink and `ls` lists the shared files)

## 7. Verify everything works (design D7)

- [x] 7.1 Run `tox -e lint` and fix any findings (verify: yamllint, flake8, and ansible-lint all pass)
- [x] 7.2 Run the full molecule cycle on the `parallels` scenario: `tox -e destroy -- --scenario-name=parallels` → `tox -e converge-monorepo -- --scenario-name=parallels` → `tox -e verify-monorepo -- --scenario-name=parallels` (verify: converge is green — the new zone-ensure task and all DNS tasks report correctly — and verify is green, including the new feature-coverage tests from group 6)
- [x] 7.3 Run a double converge (`tox -e converge-monorepo -- --scenario-name=parallels` twice, verbose) with the suppressions removed to empirically confirm what the previously-masked failures were; if a specific benign no-op error reproduces, encode it as an exact `failed_when` per task 2.1 (verify: the second converge lists zero changed tasks from this role's tasks and no masked-failure surprises remain; the observation is recorded in `audit-note.md`)
- [x] 7.4 Run `tox -e idempotence-monorepo -- --scenario-name=parallels` and iterate on any task it flags until the idempotence action passes with zero changed tasks (verify: the action reports success; the self-healing test's internal converge re-run happens during verify — after this action — and its teardown restores the A record, so it does not affect this action; if a residual originates in an external collection, apply the design D6 fallback — `molecule-idempotence-notest` tag + TODO — and document it in `audit-note.md`)
- [x] 7.5 Re-run `tox -e verify-monorepo -- --scenario-name=parallels` after the idempotence pass to confirm no regression (verify: testinfra tests, including the feature-coverage tests from group 6, still pass)
