# Adaptive External Memory Frontier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Experiment 007: an adaptive, increasingly difficult external-memory benchmark that learns reusable macro-memory only from verified successful work, compares no-memory/full-memory/retrieved-memory arms, and stops only on a confirmed frontier or clean runtime boundary.

**Architecture:** One isolated experiment module owns the curriculum, append-only memory, verified macro promotion, packet rendering, live runner, frontier logic, and evidence. Reuse existing strict scoring and Ollama utilities. Experiment 006 stays unchanged.

**Tech Stack:** Python stdlib, existing `alien_lab` scoring/Ollama utilities, `unittest`, JSON/JSONL.

**Spec:** `docs/superpowers/specs/2026-08-28-adaptive-external-memory-frontier-design.md`

## Global Constraints

- Fixed model and inference controls within one run.
- Every model call is stateless; only experiment memory persists.
- Bootstrap with 12 sealed rules; then only correctly solved retrieved-memory tasks may create macro-memory.
- Failed tasks never teach memory.
- Same challenge packet and model seed across `NONE`, `FULL`, and `RETRIEVED`.
- Primary frontier threshold is 7/8.
- A fresh same-level confirmation must also fail before declaring a frontier.
- `UNSCORABLE` is never counted as wrong.
- No silent prompt truncation.
- Do not start a level unless runtime reserve covers a complete matched level.
- Experiment 006 files remain unchanged.

## Verification gate

- [ ] Run `python3 -m unittest tests.test_adaptive_memory_frontier -v`.
- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Run `python3 -m alien_lab.adaptive_memory_frontier --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json --preflight-only`.
- [ ] Start the long run only if all three commands exit 0.

## Implementation responsibilities

- [ ] Deterministic affine bootstrap memory and stable packet generation.
- [ ] Verified macro promotion that is mathematically equivalent to successful task composition.
- [ ] Failed-task non-promotion.
- [ ] Exact `NONE`/`FULL`/`RETRIEVED` prompt isolation.
- [ ] Eight-task matched packets with depth `level + 2`.
- [ ] Strict scoring and two-packet frontier confirmation.
- [ ] Conservative pre-call context guard and runtime reserve.
- [ ] Append-only evidence and explicit summary/report interpretations.
