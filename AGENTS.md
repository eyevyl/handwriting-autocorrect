# AGENTS.md

## Project Overview

This repository contains a research/engineering project for **context-aware personalized handwriting synthesis**.

The long-term goal is to build a handwriting autocorrection system that can replace a handwritten word while making the correction look as though it was originally written in that exact location.

The key hypothesis is:

> A person's handwriting is not adequately represented by one fixed writer style. Local handwriting context—such as neatness, slant, spacing, size, density, and writing mode—contains information that can improve personalized handwriting synthesis.

Read `docs/PROJECT_SPEC.md` before making major architectural, data-modeling, or ML decisions.

---

## Current Development Priorities

Work incrementally.

The intended development sequence is:

1. Validate `.goodnotes` extraction.
2. Define a canonical stroke representation.
3. Re-render extracted strokes faithfully.
4. Segment pages into lines and words.
5. Associate handwriting with text labels.
6. Build reproducible training datasets.
7. Implement simple baselines.
8. Implement handwriting generation models.
9. Add writer conditioning.
10. Add local-context conditioning.
11. Evaluate the central research hypothesis.
12. Build an interactive autocorrection demo.

Do not jump directly to a large generative model before the data pipeline and evaluation setup are validated.

---

## Repository Architecture

Keep the project modular.

Expected major areas are:

```text
src/handwriting/
    goodnotes/       # Parsing and rendering native Goodnotes ink
    dataset/         # Segmentation, labeling, preprocessing, splits
    models/          # ML model definitions
    training/        # Training loops, losses, configs
    evaluation/      # Quantitative and qualitative evaluation
    visualization/   # Stroke/page/model-output visualization
```

Command-line entry points and one-off workflows should live under:

```text
scripts/
```

Research documentation should live under:

```text
docs/
```

Experiment configurations should live under:

```text
configs/
```

Do not couple the Goodnotes parser to PyTorch or to any specific model architecture.

The data pipeline should produce a stable representation that multiple models can consume.

---

## Data Privacy

The user's handwritten notes are private data.

Rules:

- Never commit raw `.goodnotes` notebooks.
- Never commit exported PDFs containing personal notes.
- Never modify original Goodnotes exports.
- Keep raw and derived personal handwriting data in ignored directories.
- Do not upload personal handwriting data to third-party services unless explicitly requested.
- Use synthetic or intentionally selected non-sensitive fixtures for committed tests where possible.

Expected ignored locations include:

```text
data/raw/
data/interim/
data/processed/
outputs/
```

---

## Goodnotes Data

Prefer native `.goodnotes` data over rasterized exports whenever practical.

The first milestone is to determine exactly which fields can be reliably extracted from real exports.

Potentially recoverable stroke information may include:

- ordered x/y points
- stroke boundaries
- rendered stroke width
- color
- page coordinates

Do not assume that:

- stroke width is raw Apple Pencil pressure
- timestamps are available
- true pen velocity can be reconstructed
- tilt or azimuth are available

Document discovered format behavior in `docs/DATA_FORMAT.md`.

Unsupported objects must be reported clearly rather than silently discarded.

---

## Canonical Stroke Representation

Prefer a representation independent of the original file format.

Where appropriate, model a stroke using ordered points such as:

```text
(x, y, width)
```

and represent stroke boundaries explicitly.

For ML preprocessing, consider relative coordinates:

```text
dx_t = x_t - x_(t-1)
dy_t = y_t - y_(t-1)
```

but preserve enough metadata to map normalized/model-generated strokes back into original page coordinates.

Coordinate transformations should be invertible where practical.

---

## ML Research Objective

The primary experimental comparison is:

```text
writer-only conditioning
vs.
writer + local handwriting context
```

The core question is whether nearby handwriting improves how naturally a synthesized correction fits into its surrounding line.

Potential conditioning levels include:

- no handwriting reference
- generic writer embedding
- random references from the same writer
- references from the same document
- references from the same page
- immediate neighboring words or line context

A secondary research direction is few-shot adaptation:

> How much handwriting from a writer is required before a system can imitate them convincingly?

An especially important comparison is:

```text
many random samples from the writer
vs.
fewer samples from the immediate local context
```

---

## Model Development

Start with simple baselines.

Suggested progression:

1. Retrieval/geometric baseline.
2. Simple text-to-stroke model.
3. Writer-conditioned generator.
4. Context-conditioned generator.
5. More sophisticated sequence or diffusion models only if justified.

Potential model families may include:

- autoregressive stroke Transformers
- GRU/LSTM stroke generators
- CNN/ViT style encoders
- contrastive handwriting encoders
- conditional diffusion models
- LoRA/adapters for few-shot personalization

Do not introduce architectural complexity unless it tests a clear hypothesis or addresses an observed limitation.

---

## Evaluation

Do not evaluate the project only through attractive examples.

Separate at least these dimensions:

### Text correctness

Does the generated handwriting represent the requested word?

Possible measures:

- OCR/HTR character error rate
- word recognition accuracy

### Writer similarity

Does the generated sample resemble handwriting from the target writer?

Possible measures:

- writer-identification embeddings
- learned style embeddings
- human judgments

### Local-context compatibility

Does the generated word look natural beside the handwriting immediately around it?

This is the most important project-specific measure.

Possible evaluations include:

- a learned context-compatibility model
- same-writer/different-context hard negatives
- human A/B preference tests
- synthetic-word detection tests

---

## Experimental Discipline

For every meaningful experiment:

1. State the hypothesis.
2. Define the baseline.
3. Define the dataset split.
4. Change as few variables as possible.
5. Record the configuration.
6. Record random seeds.
7. Save quantitative results.
8. Save representative qualitative outputs.
9. Consider possible dataset leakage or shortcuts.
10. Document conclusions, including negative results.

Do not claim novelty, superiority, or state-of-the-art performance without evidence.

---

## Dataset Splits

Avoid leakage between training and evaluation.

Do not randomly distribute strokes from the same word/page across train and test.

Potential evaluation splits include:

- held-out pages from the same writer
- held-out note types or handwriting contexts
- unseen words from the same writer
- unseen writers for few-shot adaptation experiments

When evaluating new-writer adaptation, test writers must not appear in model training.

---

## Coding Standards

Preferred language and ecosystem:

- Python
- PyTorch
- CUDA on the NVIDIA GPU
- pytest
- configuration-driven experiments

General requirements:

- Add type hints to public interfaces.
- Keep modules focused.
- Prefer deterministic preprocessing.
- Avoid hard-coded absolute paths.
- Use `pathlib` for filesystem paths.
- Keep exploratory notebook logic out of production modules.
- Refactor useful notebook code into reusable modules.
- Add tests for nontrivial parsing and coordinate transformations.
- Write docstrings where behavior is not obvious.
- Fail loudly when assumptions about input data are violated.

---

## Dependencies

Keep dependencies minimal.

Do not add a package simply because it may be useful later.

When adding a dependency:

- verify that it is actually needed
- add it through the project dependency configuration
- avoid overlapping libraries that solve the same problem

Prefer stable, commonly used PyTorch/Python libraries.

---

## Testing

Before finishing an engineering task:

- run relevant unit tests
- run relevant lightweight integration tests
- inspect rendered outputs for visual processing changes
- verify that private data remains ignored by Git

For parsing/rendering changes, successful execution alone is insufficient. Inspect at least one reconstructed output.

---

## Working With Codex

When a task is ambiguous, inspect existing code and documentation before making assumptions.

Prefer scoped changes over broad rewrites.

Do not perform unrelated refactors while implementing a requested feature.

Before major changes:

- read the relevant documentation
- identify affected interfaces
- preserve existing working behavior unless intentionally changing it

At the end of a task, summarize:

- what changed
- what was tested
- assumptions made
- known limitations
- suggested next step

---

## Research Philosophy

This project is intended to teach modern ML research practice, not merely produce a polished application.

Prioritize:

- clear hypotheses
- reproducibility
- strong baselines
- careful evaluation
- understanding failure modes
- data quality
- generalization

A negative experimental result is valuable if it is measured carefully and teaches something meaningful about personalized handwriting generation.