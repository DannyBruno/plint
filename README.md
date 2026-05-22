# plint

A linter for agent **prompts**, **skills**, and **tool definitions**, plus a runtime
wrapper that inspects how a model actually uses them.

> Want to see what plint actually outputs before reading further? Open the latest run on the
> [Actions tab](https://github.com/DannyBruno/plint/actions) — every push runs plint against
> [examples/good_agent](examples/good_agent) (expected clean) and [examples/bad_agent](examples/bad_agent)
> (renders every finding into the Actions step summary).

## Where the rules come from

- **Anthropic, _The Complete Guide to Building Skills for Claude_** (official skills PDF / docs) — frontmatter requirements, progressive disclosure, SKILL.md size and structure, security restrictions on angle brackets, reserved name prefixes.
- **Anthropic, [_Prompting best practices_](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)** — role/persona, XML structuring, few-shot examples, long-context ordering, "tell Claude what to do, not what not to do", and the recent advice to dial back aggressive `MUST`/`CRITICAL` emphasis on 4.6+ models.
- **Anthropic, [`anthropics/financial-services`](https://github.com/anthropics/financial-services)** (summarised in [_Structuring Agents, Skills, and MCPs_](https://medium.com/intuitionmachine/structuring-agents-skills-and-mcps-best-practices-from-anthropic-9312849ccea6)) — separation of concerns across prompt / skill / tool layers, deterministic ops belong in tools, and the cross-layer duplication smells.
- **[`mgechev/skills-best-practices`](https://github.com/mgechev/skills-best-practices)** — community-stricter skill conventions: kebab-case names, single-level subdirs, ≤500-line bodies, lean scripts. Ships behind the opt-in `--strict` flag.
- **[_Writing tools for your agents — a complete guide_](https://pub.towardsai.net/writing-tools-for-your-agents-a-complete-guide-cbfccbaf097d)** — tool description quality, example invocations, parameter documentation, atomic-vs-workflow granularity.
- **More to come** — this list will grow as new prompt/skill/tool guidance lands and as community best practices stabilise. Suggest a source by opening an issue.

## Two modes

**plint Static** — run over a project directory. Heuristic rules + an optional LLM-as-judge
cross-layer audit catch the common misplacements: prompts that encode procedures, tools
that encode workflows, skills that read like prompts, instructions duplicated across layers,
deterministic operations narrated in text instead of exposed as tools.

**plint Runtime** — wrap your existing Anthropic / OpenAI / OpenRouter client calls with a
one-line decorator. plint records every call into a trace, then surfaces patterns that indicate
the model is confused: tool-call loops, A↔B tool oscillation, calls whose results are
never read back, repeated calls with drifting arguments, hedging language that signals
underspecified context, skills loaded but never referenced. An optional confusion-judge
pass uses an LLM to spot subtler systemic issues.

Neither mode requires you to rip out existing code.

---

## Install

```bash
pip install plint                # static mode only
pip install 'plint[anthropic]'   # + Anthropic runtime wrapper
pip install 'plint[openai]'      # + OpenAI / OpenRouter runtime wrapper
pip install 'plint[all]'         # everything
```

Python 3.10+.

> Why `plint[openai]` covers OpenRouter: OpenRouter is wire-compatible with the OpenAI SDK
> (you talk to it via `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=…)`), so there
> is no separate OpenRouter package to install. plint detects OpenRouter automatically from
> the client's `base_url`. Install only the extras for providers you actually use — Anthropic
> and OpenAI are independent wrappers.

## plint Static

Point plint at the directory containing your prompts, `SKILL.md` files, and tool JSON.

```bash
plint analyze ./agents/sales/

# Heuristics only (free, fast, deterministic — good for CI)
plint analyze . --no-judge

# Heuristics + LLM-as-judge cross-layer audit
ANTHROPIC_API_KEY=sk-... plint analyze .

# Opinionated stricter rules (mgechev-style)
plint analyze . --strict

# Machine-readable output
plint analyze . --format json --output plint.json
plint analyze . --format sarif --output plint.sarif

# List all available rules
plint rules
```

### What it catches

Default rules (all sourced to Anthropic's official skills + prompting guides where applicable):

| Rule | Layer | What it flags |
|---|---|---|
| `PROMPT001` | Prompt | Prompt exceeds a length threshold (default warn 200, error 500 lines) |
| `PROMPT002` | Prompt | Near-duplicate instructions inside the same prompt |
| `PROMPT003` | Prompt | Multi-step procedural language ("first/then/next…") that belongs in a skill |
| `PROMPT004` | Prompt | Emphasis cargo-culting: swear words, ALL-CAPS runs, `!!!` |
| `PROMPT005` | Prompt | Soft override emphasis inline ("MUST", "CRITICAL", "ALWAYS", "NEVER") — overtriggers on 4.6+ models |
| `PROMPT006` | Prompt | Predominantly negative phrasing — prefer "do X" over "don't do Y" |
| `PROMPT007` | Prompt | System prompt with no role/persona ("You are…") |
| `PROMPT008` | Prompt | Long prompt with no XML structuring tags (`<instructions>`, `<context>`, etc) |
| `PROMPT009` | Prompt | Long prompt with no few-shot examples |
| `PROMPT010` | Prompt | Long-context prompt where the question appears at the top, not the end |
| `TOOL001` | Tool | Tool description encodes a multi-step workflow |
| `TOOL002` | Tool | Vague verbs, very short descriptions, no required-arg list |
| `TOOL003` | Tool | Description has no example invocation (`tool_name(arg='…')`) |
| `TOOL004` | Tool | Description doesn't say *when* to call the tool |
| `TOOL005` | Tool | Parameters missing or with very short `description` fields |
| `TOOL006` | Tool | Parameters missing a concrete JSON Schema type |
| `SKILL001` | Skill | Missing frontmatter `name` / `description` |
| `SKILL002` | Skill | Description doesn't say *when* to use the skill |
| `SKILL003` | Skill | Body has no procedural structure — a prompt in disguise |
| `SKILL004` | Skill | `name` frontmatter doesn't match folder name |
| `SKILL005` | Skill | Description exceeds Anthropic's 1024-char cap |
| `SKILL006` | Skill | Name uses reserved prefix `claude` / `anthropic` |
| `SKILL007` | Skill | Frontmatter contains `<` or `>` (Anthropic security restriction) |
| `SKILL008` | Skill | `README.md` / `CHANGELOG.md` / `INSTALLATION_GUIDE.md` inside the skill folder |
| `SKILL009` | Skill | Name isn't kebab-case |
| `SKILL010` | Skill | SKILL.md body too large (default warn 500 lines, error 5000 words) |
| `SKILL011` | Skill | Description has no negative trigger ("Do NOT use for…") |
| `XLAYER001` | Cross | Same instruction in two layers (prompt + skill, prompt + tool) |
| `XLAYER002` | Cross | Prompt/skill narrates a deterministic op that should be a tool |
| `JUDGE*` | Cross | LLM-judge findings on misplaced logic (optional, requires API key) |

Strict-mode rules (opt-in via `--strict` or `[tool.plint] strict = true`, from mgechev/skills-best-practices):

| Rule | Layer | What it flags |
|---|---|---|
| `SKILL101` | Skill | Subdirectories deeper than one level under a skill folder |
| `SKILL102` | Skill | Scripts in `scripts/` exceed 200 lines |
| `SKILL103` | Skill | Scripts in `scripts/` import non-stdlib packages |

### Discovery & config

By default plint looks for:
- prompts at `**/prompts/**/*.{md,txt}`, `**/*.prompt`, `**/*.prompt.md`
- skills at `**/SKILL.md` and `**/skills/**/*.md`
- tools at `**/tools/**/*.json`

Override any of this in `.plint.toml` (or `[tool.plint]` in `pyproject.toml`):

```toml
[tool.plint]
prompt_globs = ["app/agents/**/*.prompt.md"]
skill_globs  = ["app/agents/**/SKILL.md"]
tool_globs   = ["app/agents/**/tools/*.json"]
prompt_warn_lines  = 150
prompt_error_lines = 400

judge_enabled = true
judge_model   = "claude-sonnet-4-6"   # auto-detected from env if omitted

[tool.plint.rules.PROMPT004]
enabled = false                       # disable a specific rule
```

## plint Runtime

plint wraps the SDK clients you're already using. You don't change your model calls.

```python
import plint
from anthropic import Anthropic

# Option A — one-shot decorator
@plint.watch
def run_agent(task):
    client = Anthropic()
    return client.messages.create(...)

run_agent({"type": "onboarding"})
# → on exit, prints a runtime report to your terminal

# Option B — explicit session
client = Anthropic()
with plint.session(name="onboarding") as s:
    client.messages.create(...)
print(s.report().to_dict())

# Option C — instrument once, leave it on
plint.instrument()
client = Anthropic()
client.messages.create(...)   # transparently traced
plint.uninstrument()
```

OpenAI and OpenRouter work the same way (OpenRouter is auto-detected from the client's
`base_url`):

```python
from openai import OpenAI

@plint.watch(name="lead-triage", use_judge=True)
def run():
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)
    return client.chat.completions.create(...)
```

### What runtime mode catches

| Rule | What it flags |
|---|---|
| `RUNTIME001` | Same tool called with same args ≥ N times in a window (loop) |
| `RUNTIME002` | A→B→A→B oscillation between two tools |
| `RUNTIME003` | Tool call has no matching `tool_result` in the next turn — output dropped |
| `RUNTIME004` | Same tool called repeatedly with small arg perturbations — flailing |
| `RUNTIME005` | Hedging language ("I'll assume…", "could you clarify…") — context likely underspecified |
| `RUNTIME006` | Skill loaded into context but never referenced by the assistant |
| `RUNTIME-JUDGE-*` | LLM-judge findings on systemic confusion across the trace (optional) |

## GitHub Action

This repo's own [.github/workflows/plint.yml](.github/workflows/plint.yml) is a live demo — every push runs plint against both example agents. The `bad_agent` job renders every finding into the Actions step summary, so you can click into a recent run to see what plint actually surfaces.

For your own project, drop this into `.github/workflows/plint.yml`:

```yaml
name: plint
on: pull_request
jobs:
  plint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install plint
      - run: plint analyze . --no-judge --format sarif --output plint.sarif --fail-on warn
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: { sarif_file: plint.sarif, category: plint }
```

Findings show up as PR annotations in the GitHub code-scanning UI.

A composite action is included at `.github/actions/plint/action.yml` if you want to drop
the whole thing in as a single step.

## Examples

```
examples/
├── good_agent/         # clean three-layer separation — should pass clean
├── bad_agent/          # every smell the rules catch — should light up
└── runtime_demo.py     # build a synthetic trace and run the detectors
```

```bash
plint analyze examples/good_agent --no-judge --strict   # ✓ No findings
plint analyze examples/bad_agent --no-judge --strict    # 25 findings across all rule families
python examples/runtime_demo.py                         # runtime detectors on synthetic trace
```

You don't have to clone the repo to see what plint outputs — every commit to `main` runs
[the workflow](.github/workflows/plint.yml) against both example agents. Open the
[latest Actions run](https://github.com/DannyBruno/plint/actions) and look at the
`examples/bad_agent — showcases what plint catches` job summary for a rendered table of
every finding.

## Status

Alpha. The rule heuristics are intentionally simple and tunable — the goal is to surface
likely issues, not to be precision-perfect. False positives are expected; suppress noisy
rules in `.plint.toml`.

## License

MIT.
