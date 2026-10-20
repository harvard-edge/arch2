# Architecture 2.0 Design-Loop Card

**Card ID:**

**Profiles:** context / inspectability / replay / independent review / disclosure / decision-right completeness

**Partial-profile gaps:**

## Intent

**Objective:**

**Constraints:**

**Non-goals:**

**Risks (optional):**

**Deployment assumptions (optional):**

## Task

**Open task kind:**

**Bounded task description:**

## Design Space

**Legal choices:**

**Invalid choices:**

**Deferred choices:**

## Representation

**State schema and abstraction:**

**Reads, writes, and uncertainties:**

## Environment

**Allowed and invalid actions:**

**Observations, fidelity, and blast-radius limit:**

## Method Role

**Actors, roles, reads, writes, and limitations:**

## Feedback Budget

**Evaluation count, latency, tool or compute cost, human review, and fidelity:**

## Evidence

For each record, name the producer, kind, evidence status, tool and version,
input and output artifacts, scope, uncertainty or limitation, and content hashes.

## Failed Runs / Rejected Alternatives

Distinguish environment failures, invalid candidates, rejected alternatives,
failed rejection checks, and superseded records.

## Rejection Checks and Authority (`gates` and `decision_rights` in the Machine Schema)

Each entry is one predeclared pass/fail check that may reject a candidate or
block a claim. Record its category, criterion, result, authority, waiver rule,
evidence links, and disposition. Do not use this field for workflow stages,
design changes, reviewers, or general quality goals.

Name who may propose, execute, reject, waive, recommend, and commit, including
the scope and conditions of each right.

## Evidence-Supported Claim Boundary (`claims` in the Machine Schema)

For each architectural or AI-contribution claim, record its ID, type, statement,
baseline or comparator, outcome, scope, non-claims, status, and evidence links.

## Accountable Decision

Record status, holder, action, rationale, claim links, authorized scope,
timestamp when decided, and conditions that would reopen the decision. The
machine schema stores this record under `accountable_decision`.

## Replay / Independent Review / Disclosure

Complete only the profile blocks actually supported by existing records. A
complete replay profile requires commands, an environment binding, hashed
inputs and outputs, expected and observed status, and a verified result.
