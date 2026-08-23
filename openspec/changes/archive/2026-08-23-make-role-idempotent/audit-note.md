# Audit note: `changed_when` / `failed_when` under `tasks/`

Baseline inventory of every `changed_when` / `failed_when` usage in the role's
`tasks/` directory, with classification (read-only vs. state-changing) and the
action taken by this change. Line numbers are from the pre-change files.

## Baseline usage

| # | file:line | task / module | directive | classification | action taken |
|---|-----------|---------------|-----------|----------------|--------------|
| 1 | `tasks/facts.yml:6` | `Facts \| get current hostname` — `ansible.builtin.command: hostname` | `changed_when: false` | **read-only** (reads the hostname; no persistent side effect) | **keep** `changed_when: false`, add a short read-only comment (task 1.2) |
| 2 | `tasks/delete-outdated-ptr.yml:8` | `Delete outdated ptr \| find current PTR record...` — `ansible.builtin.shell` (`kinit admin` + `ipa dnsrecord-find <domain> <name> \| grep 'A record:'`) | `changed_when: False` | **read-only** (the query only reads DNS state; the Kerberos ticket-cache write is transient, not persistent system state — same rationale as the `tcharl.ansible_securehost` idempotency audit) | **keep** `changed_when: false`, add a short read-only comment (task 4.5) |
| 3 | `tasks/delete-outdated-ptr.yml:9` | same shell query task as #2 | `failed_when: False` | **read-only**, kept solely as a *skip mechanism*: when the query cannot run (e.g. IPA momentarily unreachable) the exact deletion gate (task 4.2) skips rather than failing the play | **keep** `failed_when: false`, add a short comment explaining the skip-mechanism purpose (task 4.5) |
| 4 | `tasks/ipa_server.yml:10` | `Ipa_server \| ensure reverse zone is created` — `freeipa.ansible_freeipa.ipadnszone` (`name_from_ip`) | `failed_when: False # TODO too lazy to find a good regex that` | **state-changing** | **remove** the blanket suppression (task 2.1, design D2) — the module is find-before-act; any surfaced error is a real issue |
| 5 | `tasks/ipa_dns_client.yml:21` | `Ipa_dns_client \| ensure dns entry is created` — `freeipa.ansible_freeipa.ipadnsrecord` (A record, `create_reverse: yes`) | `failed_when: False # don't know from where comes this sh****tty error...` | **state-changing** | **remove** the blanket suppression (task 3.2, design D3); the root cause (missing client /24 reverse zone for `create_reverse`) is fixed by the new delegated zone-ensure task (task 3.1) |
| 6 | `tasks/ipa_dns_client.yml:34` | `Ipa_dns_client \| ensure reverse dns entry is created` — `freeipa.ansible_freeipa.ipadnsrecord` (PTR record) | `failed_when: False # May have been created above` | **state-changing** | **remove** the blanket suppression (task 3.3, design D4) — "may have been created above" is exactly the case the find-before-act module handles idempotently |

## Classification summary

- **Read-only (keep `changed_when: false`, both tasks):** #1 (`facts.yml` hostname), #2 (`delete-outdated-ptr.yml` query).
- **Read-only, skip mechanism (keep `failed_when: false`):** #3 (query task — a failed query makes the deletion gate skip rather than fail the play; a genuinely-down IPA still fails loudly on the subsequent module tasks).
- **State-changing (remove blanket `failed_when: False`):** #4 (reverse-zone `ipadnszone`), #5 (A-record `ipadnsrecord`), #6 (PTR `ipadnsrecord`).

No other `changed_when` / `failed_when` usage exists under `tasks/` (verified by grep: exactly the six lines above).

## Double-converge observations (task 7.3)

Ran the `idempotence-monorepo` action (which runs converge twice internally) with all `failed_when: false` suppressions removed (per tasks 2.1, 3.2, 3.3). The second converge reported **zero changed tasks** on both hosts (`client.osgiliath.test` and `idm.osgiliath.test`, `changed=0` each). No masked-failure surprises remained: none of the previously-suppressed state-changing tasks (`ensure reverse zone`, `ensure dns entry`, `ensure reverse dns entry`) surfaced an error — they all reported `ok` (no change), confirming the `freeipa.ansible_freeipa` modules are find-before-act and idempotent once the missing-zone root cause is fixed by the new delegated zone-ensure task.

Task-level detail from the second converge (client host, the DNS-relevant tasks):
- `Delete outdated ptr | find current PTR record matching client` → `ok` (read-only query, `changed_when: false`).
- `Delete outdated ptr | debug exiting DNS record IP` → `ok` (reported the found record IP; matched the client's current IP after the rebuild).
- `Delete outdated ptr | delete existing PTR record if ip doesn't match with current` → `skipping` (the found record IP matched the client's current IP, so the `when` gate correctly skipped the deletion).
- `Ipa_dns_client | ensure dns entry is created` → `ok` (no change; the A record already existed).
- `Ipa_dns_client | ensure reverse dns entry is created` → `ok` (no change; the PTR record already existed).

No additional `failed_when` was needed: no benign no-op error reproduced, so no extra encoding was required (the blanket suppressions removed in tasks 2.1/3.2/3.3 were the only suppressions, and their removal surfaced no residual error).

## Idempotence residuals (task 7.4)

The `idempotence-monorepo` action reported **"Idempotence completed successfully."** / `idempotence-monorepo: OK`. The second converge had **zero changed tasks** on both hosts (`changed=0`). No residuals remained — no task from this role or an external collection reported a change on the second converge, so the D6 fallback (`molecule-idempotence-notest` tag) was **not** needed.

Note: the self-healing test's internal converge re-run (in `test_stale_ptr_self_healing`) occurs during `verify` (after the idempotence action) and its teardown restores the A record, so it did not affect the idempotence action's result.
