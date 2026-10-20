# Design-Loop Card Contract

`design-loop-card.v2.schema.json` is the canonical machine contract for new
Architecture 2.0 design-loop cards. Version 2.0 replaces the cumulative v1.1
level ladder with independent review profiles and makes claims, evidence,
rejection checks, replay, decision rights, and decision ownership separately
checkable.

The document-level `schema_version` and card-level `card_id` are metadata. The
human review form still has twelve fields; the machine schema separates typed
records where one prose field would otherwise conflate evidence and authority.

## Version 2.0 Semantics

- `claims` requires at least one typed architectural claim. Every claim carries
  a statement, baseline or comparator, outcome, scope, non-claims, status, and
  evidence links. `ai_contribution` is a separate claim type from
  `architecture_outcome`.
- Every evidence record identifies its producer, kind, evidence status, tool
  and version, inputs, outputs, scope, limitations, and content integrity. The
  released evidence statuses are `measured`, `computed`, `digitized`,
  `illustrative`, and `author-judgment`.
- The machine key `gates` has one narrow meaning. Each entry is a predeclared
  pass/fail rejection check with a category, criterion, result, authority,
  waiver rule, evidence links, and disposition. A workflow stage, design
  change, reviewer, or general quality goal is not a gate.
- A complete decision-right profile assigns scoped holders for `propose`,
  `execute`, `reject`, `waive`, `recommend`, and `commit`.
- `accountable_decision` replaces the human-versus-machine binary with a named
  commit-right holder, bounded action, rationale, claim links, authorized
  scope, and reopen conditions.
- A complete replay profile requires commands, an environment binding, hashed
  inputs and outputs, expected and observed status, and a verified validation
  result. The validator checks hashes for local card-relative artifacts.
- `task.kind` is open, and experimental fields use namespaced `x-...` keys.

## Independent Profiles

Every v2 card records six profiles as `complete`, `partial`, or `not_claimed`.
The context profile is always complete. A partial profile lists its missing
bindings under `profile_gaps`.

| Profile | Complete binding |
| --- | --- |
| Context | Intent, task, design space, typed claims, and a pending or recorded decision |
| Inspectability | Representation, environment, method roles, feedback budget, evidence, failure or rejection records, and predeclared rejection checks |
| Replay | Commands, environment, hashed inputs and outputs, expected and observed status, and verified validation |
| Independent review | Reviewer, independence basis, shared dependencies, conflicts, result, and claim and evidence links |
| Disclosure | Data classes, redactions, reviewer roles, and release or compliance boundary |
| Decision rights | Scoped holders for all six decision actions |

Profiles are non-ordinal. Replay does not imply independent review; public
disclosure does not imply replay; independent review may occur under restricted
disclosure.

## Compatibility and Migration

Schemas 1.0 and 1.1 remain readable for one public compatibility release.
Their cumulative levels and keys are frozen. New cards should emit
`schema_version: "2.0"`.

Create a deterministic v1.1 migration draft from the repository root.

```console
./arch2 migrate card old-card.yaml --output old-card.v2-migration-draft.yaml
```

The converter maps only fields with a direct v2 meaning. It never invents claim
status, evidence status, a decision right, or a replay result. Its output is
therefore a migration draft, not a valid v2 card, until an author
resolves every `missing_semantics` entry.

A new core field, status, required property, or validation rule requires a new
schema version and compatibility note. Documentation-only corrections may
clarify descriptions and examples without changing accepted documents.
Validators reject unknown versions rather than guessing.

Validate a YAML or JSON card from the repository root.

```console
./arch2 validate card path/to/card.yaml
```
