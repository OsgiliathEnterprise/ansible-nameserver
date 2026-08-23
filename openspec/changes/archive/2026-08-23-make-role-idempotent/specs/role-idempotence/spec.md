# role-idempotence Specification

## Purpose

Defines that the `tcharl.ansible_nameserver` role converges idempotently and reports changes and failures truthfully: re-running it against an already-configured host makes no changes, every task's change status reflects whether it actually modified system state, module failures are handled exactly instead of blanket-suppressed, and the molecule suite enforces this with a passing `idempotence` action and feature-coverage tests over the DNS end-state.

## ADDED Requirements

### Requirement: Idempotent re-execution
Running the role when the target host's state already matches the desired state SHALL report zero changed tasks; no task SHALL be reported as changed on a run that makes no effective modification to the system.

#### Scenario: Second converge on an already-configured host
- **WHEN** the role is converged a second time against hosts whose reverse DNS zone, A record, and PTR record are already in the desired state
- **THEN** the run reports zero changed tasks

#### Scenario: First converge performs setup
- **WHEN** the role is converged for the first time on hosts without the desired DNS state
- **THEN** the tasks that create the reverse zone, A record, and PTR record report changed, and a subsequent re-run reports no changes

### Requirement: Accurate change reporting
Each task's reported change status SHALL reflect whether it actually modified system state in this run. A blanket `changed_when: false` SHALL NOT be used on any task capable of modifying state; such suppression is permitted only for tasks that are strictly read-only (no persistent side effects).

#### Scenario: Read-only task reports no change
- **WHEN** a strictly read-only task runs (e.g. retrieving the current hostname)
- **THEN** it is reported as not changed, and this reporting is accurate because the task has no persistent side effects

#### Scenario: State-changing task reports changed only when it modifies state
- **WHEN** a task capable of modifying DNS state runs but finds the DNS already in the desired state
- **THEN** it is reported as not changed, and it is reported as changed only on the run that actually performs the modification

### Requirement: Exact failure handling on state-changing tasks
State-changing tasks SHALL NOT blanket-suppress module failures (e.g. `failed_when: false` with a "too lazy" comment). A task that fails on a no-op re-run SHALL be fixed so the re-run succeeds, or its failure SHALL be matched by an exact `failed_when` condition tied to a specific, understood error — never a catch-all suppression.

#### Scenario: Re-run of an idempotent DNS module task succeeds
- **WHEN** the role is converged a second time and a freeipa DNS module task (zone or record) runs against an already-existing zone/record
- **THEN** the task succeeds without any blanket failure suppression and reports no change

#### Scenario: Genuine failure is still a failure
- **WHEN** a DNS module task fails for a reason other than the specific, understood no-op error (e.g. missing reverse zone, authentication error)
- **THEN** the task fails and the play reports the failure

### Requirement: Targeted stale PTR cleanup
The stale-PTR cleanup SHALL query the DNS record whose name is derived from the host's own facts (not a hardcoded name), SHALL locate the reverse zone with the same expression as the PTR creation task, SHALL compute the PTR record name as the outdated record's IP octets beyond the configured reverse-zone prefix (reversed, matching the creation task), and SHALL delete the record only when the record's IP differs from the host's current IP. The reverse-zone size SHALL be controlled by the `nameserver_reverse_zone_prefix` default variable (default `24`) rather than a hardcoded prefix.

#### Scenario: Current IP matches the record
- **WHEN** the role runs and the host's A record already points to its current IP
- **THEN** no PTR record is deleted and no change is reported by the cleanup

#### Scenario: Record points to a stale IP
- **WHEN** the role runs and the host's A record points to an IP different from the host's current IP
- **THEN** the PTR record for that stale IP (named by its octets beyond the configured reverse-zone prefix, in the zone computed by the same expression as the creation task) is deleted and the deletion is reported as changed

#### Scenario: No record exists yet
- **WHEN** the role runs on a host that has no A record yet
- **THEN** the cleanup deletes nothing and reports no change, without failing

### Requirement: Molecule idempotence enforcement
The molecule test suite SHALL include an `idempotence` action in the test sequence of every scenario, and that action SHALL pass by confirming a second converge reports zero changed tasks.

#### Scenario: Idempotence action present and passing
- **WHEN** `molecule test` (or the equivalent tox idempotence environment) is run for any scenario (`default`, `kvm`, or `parallels`)
- **THEN** the `idempotence` action executes and passes, with the second converge reporting no changes

### Requirement: Feature coverage tests
The molecule test suite SHALL include testinfra tests covering the role's DNS features in addition to the idempotence action: the forward zone's `allow_sync_ptr` setting, the existence of the client's reverse zone (derived from the configured `nameserver_reverse_zone_prefix`), the PTR record's name (the client IP's octets beyond the prefix, reversed) and target, the A record matching the client's current IP, a reverse-DNS lookup performed from the client, and stale-PTR self-healing (a drifted A record and a stale PTR repaired by re-running the converge). The tests SHALL derive the zone and PTR name from the configured prefix (read from the `NAMESERVER_REVERSE_ZONE_PREFIX` environment variable, defaulting to `24`) rather than a hardcoded `/24`.

#### Scenario: Feature tests pass after converge
- **WHEN** the molecule verify action runs against a successfully converged environment
- **THEN** the feature-coverage tests pass: the forward zone has `allow_sync_ptr` enabled, the client's reverse zone (derived from the configured prefix) exists, the PTR record named by the client IP's octets beyond the prefix points to the client's FQDN, the A record matches the client's current IP, and a reverse-DNS lookup from the client resolves the client's FQDN to the client's IP

#### Scenario: Stale PTR self-healing
- **WHEN** the client's A record is pointed at a stale IP within the same reverse zone (same `nameserver_reverse_zone_prefix` network) and a stale PTR record is added, and then the scenario's converge playbook is re-run
- **THEN** the stale PTR record is deleted, the A record contains the client's current IP, and the test restores the A record to the client's current IP before finishing
