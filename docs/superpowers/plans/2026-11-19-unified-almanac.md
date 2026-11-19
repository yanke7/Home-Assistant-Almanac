# Unified Almanac Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** Deliver and migrate to one Almanac integration with sensors and dashboard.
**Architecture:** Standard config entry and minute coordinator, pure Python astronomy, bundled frontend with authenticated snapshots. One home location from HA settings.
**Tech Stack:** Python standard library, Home Assistant APIs, plain JavaScript.
**Spec:** docs/superpowers/specs/2026-11-19-unified-almanac.md

## Global Constraints
- Keep custom:almanac-sky-card and current dashboard configuration.
- No external APIs or runtime astronomy dependencies.
- UTC-aware sensor timestamps, missing events unknown.
- Preserve old resources until the new integration is verified.

## Review Focus
- Polar day/night and absent crossings: no fabricated event times.
- DST transitions and offset time zones: real local day length.
- Setup/unload and duplicate entry/resource handling.
- Backend unavailable/reconnect: clear fallback and recoverable refresh.
- Marketplace category conversion and rollback to 1.0.3.

### Task 1: Backend astronomy
Files: custom_components/almanac/astronomy.py; tests/test_astronomy.py; tests/parity.cjs.
Interface: snapshot(now, latitude, longitude, time_zone) -> JSON-compatible dict with ms timestamps, sun/moon/illumination, four daily charts, sensor values.
- [ ] Write and run failing tests for DST, polar day/night, next events, and JavaScript parity.
- [ ] Implement port with bounded cached daily sampling and accurate day boundaries.
- [ ] Run Python and existing JavaScript regression tests; commit.

### Task 2: Integration and card
Files: __init__.py, const.py, coordinator.py, config_flow.py, sensor.py, binary_sensor.py, strings.json, translations/en.json, manifest.json, www/almanac-sky-card.js; tests/test_integration.py.
Interfaces: entry.runtime_data coordinator; almanac/snapshot authenticated WS response; frontend read-only polling.
- [ ] Write lifecycle/config-flow/entity/snapshot tests and observe failures.
- [ ] Implement backend entities, frontend registration and snapshot consumption, preserving local demo and scrubbing.
- [ ] Test setup/unload, duplicate flow, values, fallback and parity; commit.

### Task 3: Package and migrate
Files: hacs.json, workflows, README.md, migration docs, bundled brand assets.
- [ ] Update packaging to integration and include GPL license.
- [ ] Run tests, HACS validation and hassfest, obtain independent review and resolve important findings.
- [ ] Publish 2.0.0 and update existing catalog submission to integration.
- [ ] Save current dashboard/resources, install integration, set up config flow, verify sensors and card.
- [ ] Switch Marketplace category/resource without editing dashboard config; verify and record recovery steps.
