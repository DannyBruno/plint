---
name: Propose a new rule
about: Suggest a new lint rule (with a source!)
title: "[rule] "
labels: new-rule
---

**Layer:** prompt / skill / tool / cross-layer / runtime

**What the rule should catch**

<!-- One-sentence statement of the smell. Example: "Tool description encodes a multi-step workflow rather than a single capability." -->

**Source**

<!--
plint rules are sourced. Link to one of:
  - Anthropic official docs (skills, prompting, agent SDK)
  - Anthropic financial-services repo
  - OpenAI prompt guidance
  - mgechev/skills-best-practices
  - towards AI / well-cited blog posts
  - A specific paper or eval
Tell us where this belief comes from.
-->

**Example that should trigger it**

```text
<!-- Paste a snippet that the rule should flag. -->
```

**Example that should NOT trigger it**

```text
<!-- Paste a close-but-fine snippet. False positives are the main risk. -->
```

**Severity + emphasis**

- Default severity: info / warn / error
- Should any model families re-grade or suppress this rule? (e.g. off for `gpt-5-mini`)
