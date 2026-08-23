# Context-Aware Personalized Handwriting Autocorrection

## 1. Project Summary

This project explores whether personalized handwriting generation can be improved by conditioning not only on a writer's overall handwriting identity, but also on the **local handwriting context surrounding a correction**.

The eventual application is handwritten-note autocorrection.

A user may write:

```text
gradient decent converges quickly
         ^^^^^^
```

and correct `decent` to `descent`.

Instead of inserting a generic handwritten rendering that approximately resembles the user, the system should generate a replacement that looks as though the user wrote `descent` naturally at that exact location.

The intended output should match nearby handwriting in properties such as:

- letter size
- slant
- spacing
- baseline
- stroke thickness
- connectedness
- neatness
- writing density
- local writing mode

The project therefore combines:

- handwriting data extraction
- computer vision
- sequence modeling
- representation learning
- personalized generation
- few-shot learning
- experimental ML evaluation

---

# 2. Motivation

Generic handwriting generation is already a well-studied problem.

A system capable only of:

> Generate arbitrary text in approximately this person's handwriting.

would therefore have limited research novelty.

The motivating observation for this project is more specific.

Commercial handwritten autocorrection systems can produce replacements that resemble a user's handwriting globally while still looking unnatural in context.

A possible explanation is that handwriting style is not stationary.

The same person may write very differently depending on:

- whether they are rushing
- whether they are writing carefully
- available horizontal space
- whether the text is a heading or body text
- whether they are taking lecture notes
- whether they are annotating something
- whether they are writing equations
- fatigue
- page density
- surrounding letter shapes
- writing instrument settings

Therefore, modeling a writer using only one global style representation may average over several distinct handwriting states.

---

# 3. Primary Research Question

The central question is:

> **Does conditioning personalized handwriting synthesis on nearby handwriting produce corrections that are more locally consistent than conditioning only on writer identity?**

Formally, a conventional personalized generator might approximate:

```text
p(strokes | desired text, writer)
```

This project instead investigates:

```text
p(strokes | desired text, writer, local handwriting context)
```

where local handwriting context may contain immediately neighboring handwritten words, lines, or page regions.

---

# 4. Secondary Research Question: Few-Shot Personalization

A second important question is:

> **How much handwriting is needed to adapt a model to a new writer?**

Possible adaptation budgets include:

```text
1 word
3 words
5 words
10 words
25 words
1 sentence
1 paragraph
1 page
multiple pages
```

An especially interesting comparison is:

> Can a very small amount of nearby handwriting context outperform a larger quantity of randomly selected handwriting from the same writer?

For example:

```text
3 neighboring words
vs.
20 random words from the same writer
```

If nearby examples outperform larger random samples, this would support the hypothesis that temporary/local handwriting state contains information distinct from stable writer identity.

---

# 5. Available Data

The primary source of personal handwriting data will be historical Goodnotes notebooks.

The preferred export format is:

```text
.goodnotes
```

rather than flattened images or PDFs.

Existing reverse-engineering work suggests that `.goodnotes` files may preserve native handwriting stroke information.

Potentially recoverable data includes:

```text
Stroke
    ordered points:
        x
        y
        rendered width
    color
```

Exact availability must be verified against real exports.

Important unknowns include:

- whether original timing information is available
- whether Apple Pencil pressure is stored directly
- whether tilt or azimuth are stored
- how erasing is represented
- how different Goodnotes pen types are represented
- whether stroke ordering is globally reliable
- how page transformations are encoded

The first engineering milestone is therefore a format-validation experiment.

---

# 6. Milestone 1: Validate Goodnotes Stroke Extraction

Take one representative `.goodnotes` notebook and build:

```text
.goodnotes
    ↓
parser
    ↓
structured strokes
    ↓
custom renderer
    ↓
reconstructed page image
```

Success criteria:

- handwriting strokes can be extracted
- stroke boundaries are preserved
- stroke coordinates are usable
- rendered stroke widths are available or recoverable
- page-level placement is retained
- re-rendered handwriting visually matches the source page sufficiently well

The original export must remain unchanged.

Document recovered and unavailable fields in:

```text
docs/DATA_FORMAT.md
```

This milestone is a go/no-go gate for stroke-native modeling.

---

# 7. Fallback Data Strategy

If native Goodnotes stroke extraction proves inadequate, possible fallback representations are:

1. Editable PDF vector paths.
2. Rasterized handwriting images.
3. A hybrid representation combining image context with extracted partial vector information.

Stroke-native data remains strongly preferred because:

- it preserves editable handwriting structure
- generation can directly output strokes
- geometric/style features are easier to inspect
- the output can potentially be inserted back into handwriting systems more naturally
- it avoids committing too early to image generation

---

# 8. Canonical Stroke Representation

The internal dataset representation should not depend directly on Goodnotes internals.

A possible point structure is:

```text
Point:
    x
    y
    width
```

A stroke is:

```text
Stroke:
    [Point_1, Point_2, ..., Point_N]
```

For ML input/output, relative coordinates may be preferable:

```text
dx_t = x_t - x_(t-1)
dy_t = y_t - y_(t-1)
```

An ML sequence might look conceptually like:

```text
START_STROKE
dx dy width
dx dy width
dx dy width
END_STROKE
START_STROKE
...
END_STROKE
```

Other representations may be explored based on model behavior.

Normalization should account for:

- translation
- page position
- scale
- line height

but preserve enough information to restore generated strokes to the appropriate page coordinates.

---

# 9. Dataset Construction

The project should not require a dataset of real spelling mistakes.

Existing correctly written handwriting provides self-supervised training targets.

Suppose the notes contain:

```text
gradient descent converges
```

Create a training example by masking the handwritten target word:

```text
gradient [MASK] converges
```

The model receives:

```text
desired text:
"descent"

left context:
handwritten "gradient"

right context:
handwritten "converges"
```

and predicts:

```text
the original stroke sequence for "descent"
```

Every correctly written word can potentially become a training example.

---

# 10. Required Dataset Pipeline

The long-term data pipeline is:

```text
Goodnotes notebook
      ↓
stroke extraction
      ↓
page reconstruction
      ↓
line segmentation
      ↓
word segmentation
      ↓
text alignment / labeling
      ↓
canonical normalization
      ↓
context-window generation
      ↓
train / validation / test splits
```

Each stage should be modular and independently testable.

---

# 11. Word and Line Segmentation

Handwritten pages need to be divided into useful regions.

Potential techniques include:

- spatial clustering
- connected stroke grouping
- vertical overlap
- baseline estimation
- inter-stroke distance
- temporal/stroke ordering if usable

Do not assume that each stroke corresponds to a letter or word.

Segmentation should eventually produce structures conceptually similar to:

```text
Line
    Word 1
        strokes [...]
    Word 2
        strokes [...]
    Word 3
        strokes [...]
```

Segmentation quality should be inspected visually.

---

# 12. Text Labeling

Training requires mapping stroke groups to their intended textual content.

Possible approaches include:

- Goodnotes-recognized text if accessible
- handwriting OCR/HTR
- alignment between OCR text and geometric word regions
- manual correction for a high-quality subset

A practical initial strategy may be:

```text
OCR prediction
      ↓
confidence filtering
      ↓
automatic high-confidence labels
      ↓
manual correction of evaluation subset
```

Label noise should be measured rather than ignored.

---

# 13. External Datasets

Personal notes are useful for same-writer experiments but insufficient for studying adaptation to unseen writers.

Eventually consider public online-handwriting or handwritten-text datasets containing multiple writers.

External datasets would enable:

```text
train writers
    !=
test writers
```

for few-shot personalization experiments.

Do not make external-dataset integration a prerequisite for the first prototype.

---

# 14. Baseline Models

The project should begin with simple baselines.

## Baseline A: Retrieval

Retrieve visually or structurally similar examples from existing handwriting.

Possible strategies:

- retrieve the same word if previously written
- retrieve matching characters or substrings
- adapt retrieved geometry to the target location

This establishes how far simple reuse can go.

---

## Baseline B: Unconditioned Text-to-Stroke

Generate handwriting from desired text without personalized style context.

Conceptually:

```text
text encoder
    ↓
stroke decoder
    ↓
generated handwriting
```

This tests whether the basic generation problem is working.

---

## Baseline C: Writer-Conditioned Generation

Condition generation on a stable writer representation.

```text
desired text
    +
writer embedding
    ↓
stroke generator
```

This is the main baseline against which local-context conditioning should be evaluated.

---

# 15. Context-Conditioned Model

The primary target model should approximately follow:

```text
desired text ──────────────► text encoder ───────┐
                                                 │
nearby handwriting ────────► context encoder ───┼─► generator
                                                 │
writer reference ──────────► writer encoder ─────┘
```

Potential decoder output:

```text
(dx, dy, width, pen_state)
```

Possible generator architectures include:

- Transformer decoder
- GRU/LSTM decoder
- diffusion over stroke sequences
- other sequence-generation approaches

Architecture choice should follow empirical needs rather than novelty for its own sake.

---

# 16. Context Levels to Compare

Important experimental conditions include:

## Condition 1: No personalization

```text
desired text only
```

## Condition 2: Writer identity

```text
desired text
+
global writer representation
```

## Condition 3: Random same-writer references

```text
desired text
+
random handwriting samples from same writer
```

## Condition 4: Same-document references

```text
desired text
+
handwriting from the same note/document
```

## Condition 5: Same-page references

```text
desired text
+
handwriting from the same page
```

## Condition 6: Immediate local context

```text
desired text
+
neighboring words / same line
```

The central hypothesis predicts improving local-context compatibility as context becomes more relevant to the target's immediate writing state.

---

# 17. Local Style Representation

A longer-term objective is to learn a representation of temporary handwriting state.

Possible latent factors may correspond to:

- neatness
- slant
- character size
- spacing
- stroke thickness
- connectedness
- density
- compression
- writing mode

These factors should not initially require manual labels.

One possible self-supervised assumption is:

> Handwriting written near each other on a page is more likely to share local style than handwriting written far apart.

A contrastive model might use:

```text
positive:
nearby snippets

hard negative:
same writer, distant context

negative:
different writer
```

This could help separate:

```text
writer identity
```

from:

```text
temporary writing state
```

---

# 18. Evaluation Framework

Evaluation should measure different dimensions independently.

## 18.1 Content Accuracy

Does the generated handwriting say the requested text?

Potential metrics:

- Character Error Rate
- Word Error Rate
- handwriting-recognition confidence

A visually realistic sample that spells the wrong word is not successful.

---

## 18.2 Writer Similarity

Does the output resemble handwriting from the intended writer?

Potential approaches:

- writer-classification embeddings
- handwriting style embeddings
- verification accuracy
- human preference evaluation

---

## 18.3 Local-Context Compatibility

Does the generated correction look natural beside the surrounding handwriting?

This is the project's most important custom evaluation problem.

Potential approaches include training a discriminator or compatibility encoder on:

```text
positive:
real word + true neighboring context

hard negative:
real word from same writer + mismatched context

negative:
different writer + context
```

A generated word can then be evaluated according to how compatible it is with its local surroundings.

---

# 19. Human Evaluation

Automated metrics will likely be insufficient.

Potential human studies include:

## A/B preference

Show two corrections and ask:

> Which correction looks more natural in this sentence?

Compare:

- global writer-conditioned generation
- context-conditioned generation

---

## Synthetic-word detection

Show a handwritten line where one word is generated.

Ask:

> Which word was synthetically inserted?

If participants struggle to identify the generated word, the local integration is convincing.

---

## Commercial baseline comparison

When appropriate, compare:

- Goodnotes-generated correction
- project baseline
- context-aware model

The evaluation should focus on visual integration rather than only global writer resemblance.

---

# 20. Few-Shot Experimental Design

For unseen writers, vary available reference data.

Possible budgets:

```text
1 word
3 words
5 words
10 words
25 words
1 sentence
1 paragraph
1 page
```

Plot generation quality as a function of adaptation data.

Potential measurements:

```text
writer similarity vs. reference count
context compatibility vs. reference count
legibility vs. reference count
```

Another experiment should compare local relevance against sample quantity.

Example:

```text
3 immediate neighboring words
vs.
10 random writer examples
vs.
25 random writer examples
```

---

# 21. Dataset Splits

Evaluation must avoid leakage.

Potential splits:

## Same-writer unseen-page split

Train on one set of pages and evaluate on different pages from the same writer.

## Same-writer unseen-context split

Hold out specific note types, writing modes, or documents.

## Unseen-word evaluation

Evaluate text not seen in identical handwritten form during training.

## Unseen-writer few-shot split

Train on one set of writers.

Evaluate adaptation on entirely unseen writers.

Do not randomly split strokes belonging to the same local writing sample across train and test.

---

# 22. Hardware Constraints

Available hardware includes:

- 64 GB system RAM
- NVIDIA RTX 3000 Ada GPU
- Intel Arc Pro GPU

Use the NVIDIA GPU as the primary PyTorch training device.

The project should remain practical on local hardware.

Suitable model classes include:

- small/medium Transformers
- GRUs/LSTMs
- CNN encoders
- small ViTs
- contrastive encoders
- lightweight conditional diffusion
- LoRA/adapters

Avoid making full training of large foundation models a project dependency.

---

# 23. Experiment Tracking

Every serious training run should retain:

```text
experiment name
git commit
dataset version
train/validation/test split
model architecture
configuration
random seed
optimizer
learning rate
training duration
checkpoint
evaluation metrics
qualitative samples
```

A lightweight experiment-management system is acceptable initially.

Do not create complicated infrastructure before it is needed.

---

# 24. Reproducibility

The repository should support workflows conceptually like:

```bash
python scripts/build_dataset.py --config configs/dataset.yaml

python scripts/train_model.py --config configs/writer_baseline.yaml

python scripts/evaluate_model.py \
    --checkpoint outputs/checkpoints/example.pt \
    --config configs/evaluation.yaml
```

Exact commands may evolve.

Avoid workflows that require manually editing source code to change experiment settings.

---

# 25. Initial Milestones

## Milestone 1 — Goodnotes Validation

Deliver:

- `.goodnotes` inspection
- stroke extraction
- canonical internal representation
- page renderer
- documentation of available fields

Success:

> A page reconstructed from extracted strokes closely matches the source handwriting.

---

## Milestone 2 — Segmentation

Deliver:

```text
page
→ lines
→ candidate words
```

Include visual debugging output.

---

## Milestone 3 — Text Alignment

Deliver word-level examples containing:

```text
target text
target strokes
left context
right context
page/document metadata
```

---

## Milestone 4 — Dataset Builder

Automatically generate train/validation/test examples from notebooks.

---

## Milestone 5 — Simple Baseline

Produce recognizable generated handwriting using the simplest reasonable model.

Do not optimize for realism yet.

---

## Milestone 6 — Personalized Baseline

Add writer conditioning.

---

## Milestone 7 — Local Context

Add context conditioning and test the primary hypothesis.

---

## Milestone 8 — Few-Shot Adaptation

Measure how personalization quality changes with available writer examples.

---

## Milestone 9 — Interactive Demo

Build a minimal workflow:

```text
handwritten line
      ↓
select existing word
      ↓
provide corrected text
      ↓
generate replacement strokes
      ↓
render corrected line
```

The demo should consume trained models; application code should remain separate from training code.

---

# 26. What Is Out of Scope Initially

Do not prioritize these during the first phase:

- building a polished Goodnotes plugin
- real-time synchronization with Goodnotes
- unrestricted handwriting OCR from scratch
- training very large diffusion models
- supporting every Goodnotes pen/object type
- multilingual handwriting
- exact reproduction of Apple Pencil physics
- production deployment

These may become later extensions.

---

# 27. Success Criteria

A successful research result does not require perfect handwriting generation.

The project is successful if it can rigorously answer questions such as:

> Does local handwriting context improve visual consistency?

> How much local context is useful?

> How many writer examples are needed for personalization?

> Is nearby handwriting more informative than larger amounts of randomly selected handwriting?

> Which components of handwriting style vary locally versus globally?

A carefully measured negative answer is also valuable.

---

# 28. Desired Final Portfolio Story

The project should eventually be explainable approximately as:

> Existing handwriting autocorrection systems can imitate a writer's general style but often generate corrections that look unnatural in the surrounding line. I hypothesized that handwriting contains a rapidly changing local style state rather than one fixed writer representation. I extracted native vector strokes from historical handwritten notes, built a stroke-level generative model, and compared global writer conditioning with immediate local-context conditioning. I also measured how many handwriting examples were required for few-shot personalization and evaluated legibility, writer similarity, and local visual consistency.

This narrative should guide project decisions.

The goal is not simply to build a handwriting generator.

The goal is to use a practical handwriting-autocorrection application to investigate **personalization, local context, representation learning, and few-shot generative modeling** in a rigorous way.