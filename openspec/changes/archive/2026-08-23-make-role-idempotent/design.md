# Design: Make the role idempotent

## Context

See proposal.md for motivation. The role's tasks live in `tasks/assert.yml`, `tasks/facts.yml`, `tasks/prereq.yml`, `tasks/ipa_server.yml`, `tasks/ipa_dns_client.yml`, and `tasks/delete-outdated-ptr.yml`; molecule scenarios are under `molecule/{default,kvm,parallels}/` (all three converge the same role on two hosts: an IPA server in group `ipaservers` and a client in group `ipaclients`). Current shortcuts:

- `facts.yml:6` — `command: hostname` → `changed_when: false` (read-only).
- `ipa_server.yml:10` — `ipadnszone` creating the reverse zone (`name_from_ip`) → blanket `failed_when: False` with comment "TODO too lazy to find a good regex that" — suppresses every failure.
- `ipa_server.yml:24` — `ipadnszone` setting `allow_sync_ptr` → no shortcut; the module is idempotent by design.
- `ipa_dns_client.yml:21` — `ipadnsrecord` creating the A record with `create_reverse: yes` → blanket `failed_when: False` with comment "don't know from where comes this sh****tty error, still, it works, even with a timeout as a response".
- `ipa_dns_client.yml:34` — `ipadnsrecord` creating the PTR record → blanket `failed_when: False` with comment "May have been created above".
- `delete-outdated-ptr.yml:8` — `shell` running `kinit admin` + `ipa dnsrecord-find <domain> client | grep 'A record:'` → `changed_when: False` + `failed_when: False`; the record name `client` is **hardcoded** instead of being derived from host facts.
- `delete-outdated-ptr.yml:18` — `ipadnsrecord state: absent` (delete the stale PTR) → gated on `outdated_record_ip.rc != 1` (fragile: `rc == 1` only happens when `grep` finds nothing under `pipefail`), and its `name` is computed from `outdated_record_ip.msg` — a variable that is **undefined on successful** shell results, so the delete task would error if it ever runs; its `zone_name` expression (`ipsubnet(24) | replace('.0/24','')`) disagrees with the PTR-creation task's expression (`ipsubnet(24) | ipaddr('revdns') | ...`); and the computed PTR name (a `/8`-style expression yielding e.g. `192`) does not match the creation task's `split('.')[-1]` naming.

The freeipa collection in use (1.17.0, cached under `~/.ansible/collections`) implements `ipadnszone` and `ipadnsrecord` as find-before-act modules: `find_dnsrecord`/`get_zone` check current state and `define_commands_for_present_state`/`_absent_state` only emit commands for the missing/extra parts, so a re-run against an existing zone/record is expected to report `changed: false` without failing. The one caveat: `ipadnsrecord`'s `create_reverse` path looks up the reverse zone and errors if that zone does not exist — and the reverse zone created by `ipa_server.yml` is derived from the **IDM server's** /24, while the client's PTR zone (in `ipa_dns_client.yml`) is derived from the **client's** /24. In the molecule scenarios both VMs share one private network, so the zones coincide; in production (per the role header's "same /8 subnet" assumption) they may not.

Molecule's `idempotence` action re-runs only the converge playbook (i.e. `roles: tcharl.ansible_nameserver` on both hosts) and fails if any host reports `changed=[1-9]`; the external roles included by `prepare.yml` (`tcharl.freeipa_server`, `tcharl.ansible_securehost`) are therefore outside the check. In all three scenarios `test_sequence` has `- idempotence` commented out.

## Goals / Non-Goals

**Goals:**
- Zero changed tasks from this role's own tasks on a re-run against an already-configured host.
- Accurate change and failure reporting: state-changing tasks report `changed` exactly when they modify state and fail on genuine errors; read-only tasks keep `changed_when: false`.
- The stale-PTR cleanup is correct and targeted: right record name (from host facts), right zone (same expression as creation), right PTR name (last octet), deleted only when the IP actually differs.
- Molecule `idempotence` action enabled in all three scenarios and passing.
- Feature-coverage tests in the molecule suite for the role's DNS end-state: `allow_sync_ptr`, client /24 reverse zone, PTR naming/target, A-record IP match, reverse-DNS lookup from the client, and stale-PTR self-healing (a drifted A record + stale PTR repaired by a re-converge).

**Non-Goals:**
- Changing the first-run end state: same zone, A record, PTR record, and `resolved.conf` behavior (verified by the existing testinfra tests).
- Fixing the external roles included by `prepare.yml` — out of scope and, being outside the converge playbook, outside the idempotence check as well.
- Changing molecule platforms/boxes. (The testinfra test suite is extended with feature-coverage tests — see Goals — but existing tests keep their meaning; the stale `molecule/kvm/tests/` diverged copy is replaced by a symlink to `../default/tests`, matching the `parallels` scenario.)
- Fixing upstream `freeipa.ansible_freeipa` — if a residual non-idempotent behavior is found to originate there, it is documented as a known limitation (monorepo rule 4), not patched locally.

## Decisions

### D1: Classify every `changed_when` / `failed_when` before touching anything
- **Keep `changed_when: false`** on the two genuinely read-only tasks: `facts.yml` `hostname` lookup, and the `kinit` + `ipa dnsrecord-find` query in `delete-outdated-ptr.yml` (the query only reads DNS state; the Kerberos ticket-cache write is transient and not persistent system state — same rationale as the `tcharl.ansible_securehost` idempotency audit).
- **Remove all blanket `failed_when: False`** from the freeipa module tasks (`ipa_server.yml` reverse-zone, `ipa_dns_client.yml` A record + PTR). The modules are find-before-act, so re-runs are expected to be plain no-ops; any error that surfaces without the suppression is a real issue to fix (D2/D3), not suppress.
- **Keep `failed_when: false` on the read-only query task** in `delete-outdated-ptr.yml` — but only as a *skip mechanism*: when the query cannot run (e.g. IPA momentarily unreachable), the deletion gate (D5) skips and the subsequent module tasks fail loudly if IPA is genuinely down. That is accurate behavior, not a shortcut.
- Alternative considered: keep blanket `failed_when: False` everywhere. Rejected — it is precisely the shortcut being removed; it hides real drift and makes the idempotence check meaningless.

### D2: Reverse-zone task — drop the suppression, fix what the re-run actually does
Remove `failed_when: False` from the `ipadnszone` (`name_from_ip`) task in `ipa_server.yml` and run a double converge with verbose output to observe whether it fails at all. Expected outcome: the module is idempotent, so the second run reports `ok`/`changed: false`. If a specific benign error does reproduce (e.g. a version-specific "zone already exists" race), replace the blanket suppression with an exact `failed_when` matching that one understood error, with a comment explaining it — never a catch-all.
- Alternative considered: keep `failed_when: False` with a better comment. Rejected — same shortcut, still masks real failures.

### D3: A-record task — ensure the client's own reverse zone before `create_reverse`
The `ipadnsrecord` A-record task uses `create_reverse: yes`, whose reverse-zone lookup fails (or times out — matching the "timeout as a response" comment) when the client's /24 reverse zone does not exist. `ipa_server.yml` only creates the zone from the IDM's /24. Add a delegated `ipadnszone` task at the top of `ipa_dns_client.yml` that ensures the **client's** /24 reverse zone exists (`name_from_ip: <client ip> | ipsubnet(24)`, delegated to the IPA server, `state: present`) — the module's find-before-act makes it a no-op when the zone already exists (always in molecule, where both VMs share one /24). Then remove the blanket `failed_when: False` from the A-record task.
- Alternative considered: drop `create_reverse` and rely only on the explicit PTR task. Rejected — changes first-run behavior (the explicit PTR task is the only reverse mechanism left, and `create_reverse` also self-heals future PTR drift); the zone-ensure task is additive and no-op in the common case.
- Alternative considered: keep `failed_when: False`. Rejected — D1.

### D4: PTR-record task — drop the suppression
The explicit PTR `ipadnsrecord` task is find-before-act: "May have been created above" (by `create_reverse`) is exactly the case the module handles idempotently (existing record → no command → `changed: false`). Remove `failed_when: False`. Keep the task as the deterministic owner of the PTR name/zone.
- Alternative considered: delete this task because `create_reverse` already creates the PTR. Rejected — `create_reverse` has no removal equivalent and its behavior is less predictable; keeping the explicit task is the robust, testable owner of the PTR record.

### D5: Rewrite `delete-outdated-ptr.yml` exactly
- **Right record name**: replace the hardcoded `client` in the `ipa dnsrecord-find` command with the record name derived from host facts (`{{ nameserver_current_host | replace('.' + company_domain, '') }}`), consistent with the creation task.
- **Exact deletion gate**: replace `when: rc != 1` with `when: outdated_record_ip.rc == 0 and outdated_record_ip.stdout != '' and nameserver_current_host_ip != outdated_record_ip.stdout`. (`rc == 1` under `pipefail` only means `grep` found no `A record:` line; `rc == 0` + non-empty stdout means a record with an A value was found.)
- **Right PTR name**: compute the record to delete as `{{ outdated_record_ip.stdout.split('.')[-1] }}` (last octet of the stale IP — matching the creation task's naming) instead of the broken `outdated_record_ip.msg | revdns | ipsubnet(8)` chain (`msg` is undefined on successful results, so the task could never have run correctly).
- **Aligned zone**: use the same reverse-zone expression as `ipa_dns_client.yml`'s PTR task (`ipsubnet(24) | ipaddr('revdns') | regex_replace('^0\.', '') | regex_replace('\.$', '')`) instead of the divergent `ipsubnet(24) | replace('.0/24', '')` form.
- **Reporting**: the query task keeps `changed_when: false` (read-only, D1) and `failed_when: false` as a skip mechanism (D1); the `state: absent` delete task needs no `changed_when` — the module reports changed exactly when it deletes.
- Alternative considered: keep the `rc != 1` gate. Rejected — it is accidentally-correct at best (`kinit` failure with `rc == 1` would skip, but any other failure mode relies on the empty-stdout check anyway); the explicit `rc == 0` check is precise and readable.

### D6: Enable molecule `idempotence` in all three scenarios
Uncomment `- idempotence` in `test_sequence` of `molecule/{default,kvm,parallels}/molecule.yml`, between `converge` and `side_effect`. The action re-runs only the converge playbook, so the check covers exactly this role's tasks on both hosts.
- Alternative considered: enable only in `default`. Rejected — all three scenarios converge the same role; leaving two disabled hides regressions.
- Fallback (only if needed): if a residual changed task originates in an external collection and cannot be gated from this role, tag that specific include with `molecule-idempotence-notest` plus a TODO (monorepo precedent from `tcharl.ansible_securehost`) and document the residual — but the converge playbook runs only this role, so no external includes are in scope and no tagging should be needed.

### D7: Verification strategy
Per monorepo AGENTS.md (host OS = macOS → `parallels` scenario), run:
1. `tox -e lint` (yamllint, flake8, ansible-lint).
2. Full cycle: `destroy` → `converge-monorepo` → `verify-monorepo` on `parallels`.
3. Double-converge observation: run `converge-monorepo` twice in a row (verbose) with the suppressions removed, to empirically confirm what (if anything) the previously-masked failures were (backs D2/D3).
4. `idempotence-monorepo` on `parallels` — the action's failure output lists exactly which tasks reported changed; iterate until zero.
5. Re-run verify after the idempotence pass to confirm no regression.
- The `default`/`kvm` scenarios cannot be executed on this host (VirtualBox/libvirt not available); their `test_sequence` changes are verified by `tox -e lint` and the molecule syntax/sequence parsing, and the `parallels` run validates the shared converge playbook.

## Risks / Trade-offs

- [The previously-masked failures may have been environment-specific (stale LDAP from prior runs — a known issue documented in the role's AGENTS.md)] → Mitigation: the molecule prepare phase already cleans stale IPA state; the double-converge observation (D7.3) distinguishes real no-op errors from environmental ones before any exact `failed_when` is written.
- [`create_reverse` timeout on the A-record task has a different root cause than the missing reverse zone] → Mitigation: D7.3 observes the actual error with the suppression removed; D3's zone-ensure task is a no-op if the zone already exists, so it is safe to keep regardless.
- [The rewritten stale-PTR cleanup changes behavior for hosts whose name is not `client` (it now actually targets the right record — previously the find looked at the wrong name and the delete task was broken)] → Mitigation: this is a bug fix required by the spec's "Targeted stale PTR cleanup" requirement; molecule (host name `client`) exercises the same code path as before, so no test regression is expected.
- [Removing blanket `failed_when: False` turns previously-silent errors into play failures] → Mitigation: that is the intended behavior (spec: "Genuine failure is still a failure"); the verify tests confirm the end state is unchanged.
- [Molecule idempotence action flags a task missed by the static audit] → Mitigation: D7.4 iteration loop; any residual originating in an external collection would be documented as a known limitation per D6 fallback.

## Migration Plan

No data or state migration: first-run end state is unchanged (the only first-run additions are a no-op-in-molecule zone-ensure task and a corrected cleanup that targets the right record). Rollback = revert the affected files (task files + molecule configs are independent and trivially reversible). No version bump beyond the normal release process.

## Open Questions

- What error (if any) does the reverse-zone `ipadnszone` task raise on a no-op re-run — i.e., what was the "good regex" the original author couldn't find? (Answered empirically by D7.3; affects whether D2 needs an exact `failed_when` at all.)
- Does the A-record `create_reverse` timeout reproduce without the client /24 zone-ensure task (validating D3's root-cause hypothesis)? (Answered empirically by D7.3.)
