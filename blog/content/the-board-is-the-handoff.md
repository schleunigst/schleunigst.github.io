---
title: The Board Is the Handoff
dek: Taskwharf is a local-first, cross-project task board for coding agents — one SQLite file, a CLI, a local web board, and JSON everywhere. This is why it exists and how a session uses it.
author: Schleunigst
org: Schleunigst
status: Working notes
date: 2026-10-31
slug: the-board-is-the-handoff
draft: true
sections:
  - The session is not the plan | Chat history, TODO files, and hosted trackers each lose something an agent needs
  - One board, many repositories | Global task IDs and dependencies that cross project boundaries
  - What survives in the record | Claims, append-only notes, and an event history built for handoffs
  - The loop | next, claim, note, done — and the same state in a local browser
  - Local-first, not hosted | One SQLite file, no daemon, no account, and a deliberately small surface
  - What it refuses to do | The non-goals, the current limits, and the part that should stay boring
---

An agent session ends and takes the plan with it. The files remain, the tests still pass or fail, but the reason for the next change — what was tried, what is blocked, who owns it — lives in a transcript the next session will not read.

[Taskwharf](https://github.com/schleunigst/taskwharf) is a small attempt to make that reason durable. It is a local-first task board for coding agents: one SQLite database outside every repository, a CLI that returns JSON, a local web board, and an HTTP API over the same store. We built it while working on a Flutter camera package whose iOS half was waiting on hardware; the board held the package and the tooling, and its dependency edges made the blockers visible without a meeting.

## The session is not the plan

A context window is not a database. It is a working set that gets compacted, truncated, or simply left behind when the process exits. The usual places a plan can live all fail in different ways:

- **The chat transcript** records what happened, but not in a shape anything can query. It grows, gets summarized, and is not shared by two sessions working at once.
- **A `TODO.md` in the repository** survives resets and works offline, but it belongs to one repository. It also turns scratch planning into committed noise, or into an ignored file that never travels with the code.
- **GitHub Issues, Linear, or Jira** are good at shared, long-lived project management. They also require an account, a network, and a remote service for what may be a local agent's working set.

What we wanted was not another place to write TODOs. It was a small state machine that could answer four questions: what is next, who has it, what is it waiting on, and what did the last session learn? Those answers fit in one database, and they are useful to both a human reading a board and an agent reading JSON.

## One board, many repositories

Taskwharf has one global namespace. Every task is `TW-1`, `TW-2`, and so on, regardless of which project it belongs to. A handoff can say `TW-22` without also naming a repository, and a dependency can point across project boundaries.

A project is a registered repository or workspace. When an `origin` remote exists, its normalized URL is the identity, so different clones of the same repository resolve to the same project. Without a remote, the resolved path is the identity. That trade-off is explicit: move a path-only project and it becomes a new project. There is no guessing from directory names.

The important part is that tasks belong to one project, but dependencies do not. A release task can wait on a hardware-validation task; a publish task can wait on release verification; a blog draft can wait on a tool becoming public. The board shows the blocked chain, and `done` refuses to close a task while an unfinished dependency remains.

Nothing is written into the repositories to make this work. The plan lives outside the code, in one database that every project query can see. Tags carry the streams that do not deserve their own project: `ios`, `release`, `docs`, `hardware`.

## What survives in the record

A task is deliberately small: title, description, project, status, priority, tags, an optional branch and session, a claim, and timestamps for completion and archival. The statuses are `backlog`, `ready`, `in_progress`, `review`, and `done`. Claiming a task moves it to `in_progress` and records the actor, branch, and session. Releasing it, or moving it back to `ready` or `backlog`, clears the claim.

Claims are advisory, not locks. They do not stop another process from writing; they make ownership visible. When a claim outlives its session, `taskwharf stale` reports it so the next agent can decide whether to take over instead of silently duplicating the work.

Notes are the part that actually defeats context loss. A note is an immutable, authored, timestamped assertion: what was discovered, what changed, what was verified, what remains blocked. The event log records creation, moves, claims, edits, dependency changes, and archival. Nothing in that history is rewritten. A new session adds a note instead of editing the old one.

This is also why `done` checks dependencies. Completion is not a vibe; it is a state transition with a precondition. `--force` exists for the cases where the graph is wrong or the dependency is obsolete, but the normal path is truthful.

## The loop

The workflow is intentionally boring. Install the managed instructions block once, then let each session follow it:

```sh
taskwharf instructions --write AGENTS.md

taskwharf next --all --json
taskwharf claim TW-12 --by opencode --branch feat/preview --json
taskwharf note TW-12 "Dart tests pass; hardware check still pending." --json
taskwharf done TW-12 --json
```

`next` returns an unclaimed, unblocked task. `claim` takes it and records who is working on it. `note` leaves the durable part of the handoff. `done` closes it only when its dependencies allow it. Most commands accept `--json`; parse errors come back as JSON too, so a script or agent does not have to scrape prose.

The same state is available in a browser:

```sh
taskwharf serve --open
```

The web board is not a second system. It is another client over the same store: five status columns, project and text filters, task creation, drag-and-drop moves, claims, notes, dependencies, archive actions, and recent history. Close the server and the database is unchanged. If a shell is unavailable, the HTTP API exposes the same operations.

## Local-first, not hosted

Taskwharf is one Python package, one SQLite database, and one local HTTP server. The CLI is a short-lived process that opens the database, runs one command, and exits. `taskwharf serve` binds to loopback by default and runs only while the board is open. There is no background worker, no scheduler, no account system, and no telemetry.

SQLite is in WAL mode, so readers and one writer can coexist without a daemon. Every store operation opens its own connection, enables foreign keys, sets a busy timeout, commits, and closes. The schema is versioned with `PRAGMA user_version`; older databases are upgraded through forward-only migrations, and a database from a newer schema is rejected rather than silently modified.

Local-first here means the database on this machine is the source of truth, not a cache of a remote service. It does not mean multi-machine sync. That is future work, and the current export/import path moves state deliberately rather than pretending a conflict-free merge already exists.

The server is for a local tool, not an untrusted network. It rejects requests whose `Host` header is not the bound host or a loopback name, requires JSON for state-changing requests, sends a restrictive Content-Security-Policy, and renders task text with DOM text nodes. Those measures block common DNS-rebinding and cross-site form attacks. They are not authentication.

The runtime has no third-party dependencies and requires Python 3.10 or newer. For an agent tool, install friction is a reliability bug: a package that needs a dependency solver to start is a package that will fail in the middle of a handoff. The tests use the standard library too, including a real HTTP server on an ephemeral loopback port.

## What it refuses to do

Taskwharf is not a hosted multi-tenant project manager, and it is not trying to replace GitHub Issues, Linear, or Jira. It is for the working set on one machine: the tasks an agent needs before it can ask a human, and the state that should survive when the context window does not.

The current limits are real. It is alpha software and not on PyPI yet. There is no authentication, no multi-machine sync, no issue-tracker sync, and no OpenCode plugin. Claim leases with expiry are on the roadmap; today claims are advisory and the stale report is the safety net. Exposing the server to an untrusted network is not supported.

Those are acceptable constraints for a tool whose job is to be smaller than the work. Taskwharf does not make an agent smarter. It makes the handoff cheaper. The board is not the work; it is the part of the work that survives the session.
