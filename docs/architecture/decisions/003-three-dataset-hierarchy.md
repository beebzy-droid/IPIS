# ADR 003 — Three-Dataset Hierarchy with Distinct Validation Roles

**Status:** Accepted
**Date:** 2026-05-28
**Decision owner:** Bien Busico

## Context

Module 1 needs validation data. Three options:

1. Single primary dataset (e.g., Debutanizer only)
2. Two datasets for validation
3. Three datasets, each with a distinct role

## Decision

**Use three datasets, each playing a distinct validation role:**

| Role | Dataset | Question it answers |
|---|---|---|
| Primary (development) | Debutanizer Column | Does the hybrid architecture beat baselines? |
| Secondary (transfer) | Tennessee Eastman | Does the architecture transfer across topologies? |
| Supplementary (stress test) | SECOM Semiconductor | Does it survive a different industry? |

## Rationale

### Why three roles, not three alternatives

Most published soft sensor papers use one dataset. A few use two. None systematically use three datasets in distinct validation roles addressing distinct gaps in the literature.

- **Debutanizer answers "does it work?"** — established benchmark, real refinery data, sufficient for baseline comparisons
- **Tennessee Eastman answers "does it transfer?"** — different topology, different industry, 21 documented disturbance modes for stress testing
- **SECOM answers "does it generalize beyond process?"** — 590 features, semiconductor industry, very different data shape

### Why this combination is publishable

- Combination novelty: no prior work uses all three for a single soft sensor architecture study
- Each dataset has well-known published baselines to compare against
- Cross-process transfer (Debutanizer → TEP) is identified in the literature as an open problem
- SECOM result documents framework limits honestly — a credibility signal reviewers reward

### What we explicitly do NOT claim

- Universal cross-process transfer (only two source-target pairs)
- That SECOM is a "natural" target for the framework — it's a stress test, not a validation
- That benchmark performance equals real-plant performance

## Consequences

### Positive

- Three credible validation tiers in one project
- Each phase produces a standalone publishable result
- Forces dataset mastery — the engineer learns each dataset's quirks before integration

### Negative

- Longer development time (4–6 weeks added vs. single-dataset version)
- More code to maintain (three data loaders, three preprocessing pipelines)
- Risk of "SECOM doesn't fit and damages the narrative" — mitigated by reframing SECOM as honest stress test

### Neutral

- If industrial partner data (e.g., Coca-Cola carbonation) becomes available, it slots in as a fourth tier with minimal architectural impact

## Implementation notes

- All three datasets are loaded through a common `DatasetLoader` interface (`src/ipis/module1_soft_sensor/data/loaders.py`)
- Each dataset has its own config in `configs/dataset/`
- Preprocessing pipelines are dataset-specific but share interface contracts
- Evaluation harness runs the same metrics on all three for direct comparability

## Revisit triggers

- If SECOM results are uninterpretable, drop to two-dataset hierarchy and reframe paper
- If Coca-Cola data arrives in time, expand to four-dataset hierarchy
- If transfer Debutanizer → TEP shows no improvement at all, reframe paper as "characterization of transfer limits" rather than dropping the dataset

## References

- Fortuna et al. (2007), "Soft Sensors for Monitoring and Control of Industrial Processes" — Debutanizer dataset origin
- Downs & Vogel (1993), "A plant-wide industrial process control problem" — Tennessee Eastman
- UCI ML Repository — SECOM dataset documentation
- Kadlec, Gabrys & Strandt (2009), "Data-driven soft sensors in the process industry" — multi-process benchmarking
