# Proposal: Make the role idempotent

## Why

Re-running `tcharl.ansible_nameserver` on an already-configured host cannot be proven idempotent because state-changing behavior is masked by blanket shortcuts: `failed_when: False` on the reverse-zone `ipadnszone` task ("TODO too lazy to find a good regex") and on both `ipadnsrecord` tasks ("don't know from where comes this sh****tty error"), plus fragile gates in `delete-outdated-ptr.yml` (a `rc != 1` check, a PTR record name computed from `outdated_record_ip.msg` — undefined on success —, a hardcoded `client` record name, and a reverse-zone expression that disagrees with the creation task). These shortcuts hide real drift, make stale-PTR cleanup unreliable, and block molecule's `idempotence` action — currently commented out in all three scenarios.

## What Changes

- Audit every `changed_when` / `failed_when` usage under `tasks/`; classify each task as read-only or state-changing, and keep `changed_when: false` only where the task is genuinely read-only (`facts.yml` `hostname`).
- Remove the blanket `failed_when: False` suppressions from the `ipadnszone` (reverse zone) and `ipadnsrecord` (A record + PTR) tasks. The freeipa collection modules are idempotent by design (find-before-act), so re-run failures indicate real issues to fix precisely — with an exact `failed_when` condition or a proper pre-gate — not blanket suppression.
- Rewrite `delete-outdated-ptr.yml` exactly: query the DNS record name computed from host facts instead of the hardcoded `client`; gate the delete on an exact `rc == 0` + non-empty-stdout check; fix the PTR record name (last octet of the outdated IP, matching the creation task); align the reverse-zone expression with `ipa_dns_client.yml`.
- Enable the molecule `idempotence` action in all three scenario `test_sequence`s (`default`, `kvm`, `parallels`).
- Extend the molecule testinfra suite with feature-coverage tests: forward-zone `allow_sync_ptr`, client /24 reverse zone, PTR naming/target, A-record IP match, reverse-DNS lookup from the client, and a stale-PTR self-healing test (drift a record, re-converge, assert repair); replace the diverged `molecule/kvm/tests/` copy with a symlink to `molecule/default/tests`, matching the `parallels` scenario.
- Verify end-to-end: lint plus full molecule cycle (destroy → converge-monorepo → verify-monorepo) plus the idempotence check on the `parallels` scenario (macOS host), iterating until a second converge reports zero changed tasks.

## Capabilities

### New Capabilities

- `role-idempotence`: re-running the role against an already-configured host performs no state changes and reports zero changed tasks; every task's change/failure reporting reflects what actually happened (no blanket suppression on state-changing tasks); molecule scenarios enforce this via the `idempotence` action.

### Modified Capabilities

(none — this role has no existing specs)

## Impact

- **Code**: `tasks/ipa_server.yml`, `tasks/ipa_dns_client.yml`, `tasks/delete-outdated-ptr.yml` (exact change/failure reporting, fixed gates and expressions); `molecule/{default,kvm,parallels}/molecule.yml` (enable `idempotence` in `test_sequence`).
- **Behavior**: first-run end state is unchanged (reverse zone, A record, PTR record, stale-PTR cleanup). Re-runs become genuine no-ops. Stale-PTR cleanup targets the correct record name and the correct zone, so it actually works on hosts whose name is not `client`.
- **Testing**: molecule `idempotence` action becomes part of every scenario's test sequence; the testinfra suite gains feature-coverage tests over the DNS end-state and stale-PTR self-healing; `molecule/kvm/tests/` becomes a symlink to the shared `molecule/default/tests/` (as `parallels` already is).
- **Out of scope**: the external roles included by `molecule/*/prepare.yml` (`tcharl.freeipa_server`, `tcharl.ansible_securehost`) — they are not part of the converge playbook that the idempotence action re-runs, and any idempotency work in them belongs to their own repos (monorepo rule 4).
