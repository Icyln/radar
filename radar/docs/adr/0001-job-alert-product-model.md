# ADR 0001: Present one Job Alert concept

**Status:** Accepted  
**Release:** 0.8.0

## Context

Radar internally supports broad search and followed-company-only matching. Exposing these as separate profile types forced users to understand implementation concepts before creating a useful search.

## Decision

Keep the existing database/API coverage modes for compatibility, but present a single **Job Alert** concept in the UI.

- Broad search is the default.
- **Only search companies I follow** is an advanced checkbox.
- Technical source/discovery language is restricted to Admin pages.

## Consequences

- No coverage-mode data migration is required.
- Existing alerts continue working.
- The public/user-facing product becomes easier to explain.
- Backend tests can continue validating both matching modes independently.
