# plint

[![CI](https://github.com/DannyBruno/plint/actions/workflows/plint.yml/badge.svg)](https://github.com/DannyBruno/plint/actions/workflows/plint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#status)

A linter for LLM agent code. Two modes: static analysis of your prompts, skills, and tool definitions, and a runtime wrapper that records SDK calls and flags patterns that suggest the model is confused.

If your prompts are getting long, your tool descriptions are growing into mini-workflows, or your agent keeps looping on tool calls, plint might help. Works with Anthropic, OpenAI, and OpenRouter, and adjusts rule severity based on the target model.

```bash
pip install plint
plint analyze ./path/to/your/agent/
```

To see plint output without cloning, open the [latest CI run](https://github.com/DannyBruno/plint/actions). Every push runs plint against [examples/good_agent](examples/good_agent) (expected clean) and [examples/bad_agent](examples/bad_agent), which renders every finding into the Actions step summary.

## What it's for

Agent code tends to split across three layers: prompts, skills, and tool definitions. Knowing what belongs where is more art than science right now. It's easy to end up with procedures buried in a prompt, workflows hidden in a tool description, or skills that read like prompts. plint flags those cases so they're easier to spot.

Every rule traces back to a public source. If a rule fires and you disagree, you can argue with the source.

If you're a coding agent reading this on behalf of a developer, see [AGENTS.md](AGENTS.md).

## Where the rules come from

- **Anthropic, _The Complete Guide to Building Skills for Claude_** (official skills PDF / docs). Frontmatter requirements, progressive disclosure, SKILL.md size and structure, security restrictions on angle brackets, reserved name prefixes.
- **Anthropic, [_Prompting best practices_](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices).** Role and persona, XML structuring, few-shot examples, long-context ordering, "tell Claude what to do, not what not to do", and the recent advice to dial back aggressive `MUST` / `CRITICAL` emphasis on 4.6+ models.
- **Anthropic, [`anthropics/financial-services`](https://github.com/anthropics/financial-services)** (summarised in [_Structuring Agents, Skills, and MCPs_](https://medium.com/intuitionmachine/structuring-agents-skills-and-mcps-best-practices-from-anthropic-9312849ccea6)). Separation of concerns across prompt, skill, and tool layers. Deterministic ops belong in tools. Cross-layer duplication smells.
- **[`mgechev/skills-best-practices`](https://github.com/mgechev/skills-best-practices).** Community-stricter skill conventions: kebab-case names, single-level subdirs, 500-line body cap, lean scripts. Ships behind the opt-in `--strict` flag.
- **[_Writing tools for your agents_](https://pub.towardsai.net/writing-tools-for-your-agents-a-complete-guide-cbfccbaf097d).** Tool description quality, example invocations, parameter documentation, atomic vs workflow granularity.
- **OpenAI, [_Prompt guidance_](https://developers.openai.com/api/docs/guides/prompt-guidance).** Corroborates several Anthropic recommendations, especially the warning against absolute language like `MUST` / `NEVER` for judgment calls (PROMPT005). Adds outcome-first, stopping-condition, and output-contract guidance. One disagreement worth knowing: OpenAI doesn't require XML structuring, so if you're targeting OpenAI models you may want to suppress PROMPT008 in `.plint.toml`.
- **More to come.** Open an issue to suggest a source.

## Two modes

**plint Static.** Heuristic rules over a project directory, with an optional LLM-as-judge pass for cross-layer issues. Catches prompts that encode procedures, tools that encode workflows, skills that read like prompts, instructions duplicated across layers, and deterministic operations narrated in prose instead of exposed as tools.

**plint Runtime.** A decorator around your existing Anthropic, OpenAI, or OpenRouter client calls. Records each call into a trace, then flags patterns that suggest the model is confused: tool-call loops, oscillation between two tools, calls whose results never get read back, repeated calls with drifting arguments, hedging language, skills loaded but never referenced. Optional LLM-as-judge pass for systemic issues.

Neither mode requires changes to your existing client code.

---

## Install

```bash
pip install plint                # static mode only
pip install 'plint[anthropic]'   # + Anthropic runtime wrapper
pip install 'plint[openai]'      # + OpenAI / OpenRouter runtime wrapper
pip install 'plint[all]'         # everything
```

Python 3.10+.

`plint[openai]` covers OpenRouter because OpenRouter is wire-compatible with the OpenAI SDK. You talk to it via `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)`, and plint detects OpenRouter from the client's `base_url`. The Anthropic and OpenAI wrappers are independent. Install only what you use.

## plint Static

Point plint at the directory containing your prompts, `SKILL.md` files, and tool JSON.

```bash
plint analyze ./agents/sales/

# Heuristics only (fast, deterministic, good for CI)
plint analyze . --no-judge

# Heuristics plus LLM-as-judge cross-layer audit
ANTHROPIC_API_KEY=sk-... plint analyze .

# Opinionated stricter rules
plint analyze . --strict

# Machine-readable output
plint analyze . --format json --output plint.json
plint analyze . --format sarif --output plint.sarif

# List all available rules
plint rules
```

### Model-aware policy

Most of the sources are model-specific. Anthropic's prompting guide says aggressive emphasis (`MUST`, `CRITICAL`, `ALWAYS`) overtriggers on Claude 4.6+. OpenAI says the same of GPT-5.5. Smaller models like gpt-5-mini actually benefit from the same scaffolding plint flags as a smell on bigger models. So plint detects the target model and adjusts severity per family on top of the base rules.

Detection precedence:

1. `target_model` in `.plint.toml`, or `--model claude-opus-4-7` on the CLI.
2. `target_model:` (or `model:`) in a prompt's YAML frontmatter.
3. Inferred from your tool definitions. OpenAI-shape tools imply `gpt-5.5`, Anthropic-shape imply `claude-opus-4-7`.
4. None. Generic best practices, no overrides.

plint prints the detected target at the top of the text report. The JSON and SARIF reports include the full overrides map under `summary.policy`.

Current per-family policy:

| Family | Rule | Default | Adjusted | Why |
|---|---|---|---|---|
| `claude-4.6+` | `PROMPT005` (MUST/CRITICAL emphasis) | INFO | **WARN** | Anthropic prompting guide |
| `claude-4.6+` | `PROMPT008` (no XML on long prompts) | INFO | **WARN** | Anthropic prompting guide |
| `claude-legacy` (pre-4.6) | `PROMPT005` | INFO | **off** | Aggressive emphasis historically tolerated |
| `gpt-5.5` | `PROMPT005` | INFO | **WARN** | OpenAI prompt guidance |
| `gpt-5.5` | `PROMPT008` (XML) | INFO | **off** | OpenAI doesn't require XML structuring |
| `gpt-5.5` | `PROMPT003` (procedural language) | WARN | **WARN** + emphasised | OpenAI emphasises outcome-first |
| `gpt-5-mini` / `gpt-5-nano` | `PROMPT005` | INFO | **off** | Small models need explicit emphasis |
| `gpt-5-mini` / `gpt-5-nano` | `PROMPT003` | WARN | **off** | Literal models need step-by-step scaffolding |
| `gpt-codex` | `PROMPT003` | WARN | **WARN** | Codex guide: no upfront plans or preambles |
| `gpt-codex` | `PROMPT008` | INFO | **off** | Plain text is fine |

This is the v1 table. It'll grow alongside the sources list.

### What it catches

Default rules (sourced to Anthropic's official skills and prompting guides where applicable):

| Rule | Layer | What it flags |
|---|---|---|
| `PROMPT001` | Prompt | Prompt exceeds a length threshold (default warn 200, error 500 lines) |
| `PROMPT002` | Prompt | Near-duplicate instructions inside the same prompt |
| `PROMPT003` | Prompt | Multi-step procedural language ("first / then / next…") that belongs in a skill |
| `PROMPT004` | Prompt | Emphasis cargo-culting: swear words, ALL-CAPS runs, `!!!` |
| `PROMPT005` | Prompt | Soft override emphasis inline (`MUST`, `CRITICAL`, `ALWAYS`, `NEVER`). Overtriggers on 4.6+ models |
| `PROMPT006` | Prompt | Predominantly negative phrasing. Prefer "do X" over "don't do Y" |
| `PROMPT007` | Prompt | System prompt with no role or persona ("You are…") |
| `PROMPT008` | Prompt | Long prompt with no XML structuring tags (`<instructions>`, `<context>`, etc) |
| `PROMPT009` | Prompt | Long prompt with no few-shot examples |
| `PROMPT010` | Prompt | Long-context prompt where the question appears at the top, not the end |
| `TOOL001` | Tool | Tool description encodes a multi-step workflow |
| `TOOL002` | Tool | Vague verbs, very short descriptions, no required-arg list |
| `TOOL003` | Tool | Description has no example invocation (`tool_name(arg='…')`) |
| `TOOL004` | Tool | Description doesn't say *when* to call the tool |
| `TOOL005` | Tool | Parameters missing or with very short `description` fields |
| `TOOL006` | Tool | Parameters missing a concrete JSON Schema type |
| `SKILL001` | Skill | Missing frontmatter `name` or `description` |
| `SKILL002` | Skill | Description doesn't say *when* to use the skill |
| `SKILL003` | Skill | Body has no procedural structure (reads like a prompt in disguise) |
| `SKILL004` | Skill | `name` frontmatter doesn't match folder name |
| `SKILL005` | Skill | Description exceeds Anthropic's 1024-char cap |
| `SKILL006` | Skill | Name uses reserved prefix `claude` or `anthropic` |
| `SKILL007` | Skill | Frontmatter contains `<` or `>` (Anthropic security restriction) |
| `SKILL008` | Skill | `README.md` / `CHANGELOG.md` / `INSTALLATION_GUIDE.md` inside the skill folder |
| `SKILL009` | Skill | Name isn't kebab-case |
| `SKILL010` | Skill | SKILL.md body too large (default warn 500 lines, error 5000 words) |
| `SKILL011` | Skill | Description has no negative trigger ("Do NOT use for…") |
| `XLAYER001` | Cross | Same instruction in two layers (prompt + skill, prompt + tool) |
| `XLAYER002` | Cross | Prompt or skill narrates a deterministic op that should be a tool |
| `JUDGE*` | Cross | LLM-judge findings on misplaced logic (optional, requires API key) |

Strict-mode rules (opt-in via `--strict` or `[tool.plint] strict = true`, from mgechev/skills-best-practices):

| Rule | Layer | What it flags |
|---|---|---|
| `SKILL101` | Skill | Subdirectories deeper than one level under a skill folder |
| `SKILL102` | Skill | Scripts in `scripts/` exceed 200 lines |
| `SKILL103` | Skill | Scripts in `scripts/` import non-stdlib packages |

### Discovery and config

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

# Model-aware policy (autodetected from frontmatter or tool format if omitted)
target_model    = "claude-opus-4-7"
target_provider = "anthropic"

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

# Option A: one-shot decorator
@plint.watch
def run_agent(task):
    client = Anthropic()
    return client.messages.create(...)

run_agent({"type": "onboarding"})
# Prints a runtime report to your terminal on exit.

# Option B: explicit session
client = Anthropic()
with plint.session(name="onboarding") as s:
    client.messages.create(...)
print(s.report().to_dict())

# Option C: instrument once, leave it on
plint.instrument()
client = Anthropic()
client.messages.create(...)   # traced automatically
plint.uninstrument()
```

OpenAI and OpenRouter work the same way (OpenRouter is auto-detected from the client's `base_url`):

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
| `RUNTIME001` | Same tool called with same args N or more times in a window (loop) |
| `RUNTIME002` | A → B → A → B oscillation between two tools |
| `RUNTIME003` | Tool call has no matching `tool_result` in the next turn (output dropped) |
| `RUNTIME004` | Same tool called repeatedly with small arg perturbations (flailing) |
| `RUNTIME005` | Hedging language ("I'll assume…", "could you clarify…") suggesting underspecified context |
| `RUNTIME006` | Skill loaded into context but never referenced by the assistant |
| `RUNTIME-JUDGE-*` | LLM-judge findings on systemic confusion across the trace (optional) |

## GitHub Action

This repo's own [.github/workflows/plint.yml](.github/workflows/plint.yml) is a live demo. Every push runs plint against both example agents. The `bad_agent` job renders every finding into the Actions step summary, so you can click into a recent run to see what plint actually surfaces.

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

A composite action is included at `.github/actions/plint/action.yml` if you want to drop the whole thing in as a single step.

## Examples

```
examples/
├── good_agent/         # clean three-layer separation, expected clean
├── bad_agent/          # every smell the rules catch, should light up
└── runtime_demo.py     # build a synthetic trace and run the detectors
```

```bash
plint analyze examples/good_agent --no-judge --strict   # ✓ No findings
plint analyze examples/bad_agent --no-judge --strict    # 25 findings across all rule families
python examples/runtime_demo.py                         # runtime detectors on a synthetic trace
```

To see plint output without cloning, every commit to `main` runs [the workflow](.github/workflows/plint.yml) against both example agents. Open the [latest Actions run](https://github.com/DannyBruno/plint/actions) and look at the `examples/bad_agent` job summary for a rendered table of every finding.

## Roadmap

Things on the list (PRs and rule proposals welcome, see [the issue templates](.github/ISSUE_TEMPLATE/)):

- More rules grounded in community sources, aiming for around 50 default rules.
- Runtime mode model-aware policy. The static side is policy-aware now. Runtime detectors still fire identically across models.
- Auto-fix suggestions for the simpler rules (SKILL004, SKILL009, TOOL005).
- An eval-harness sibling: an autoresearch-style hill-climber for prompts, skills, and tools against a held-out test set.
- More provider wrappers (LiteLLM, AWS Bedrock, Vertex AI).
- pre-commit hook.

## Status

Alpha. The heuristics are intentionally simple and tunable. The goal is to surface likely issues, not be precision-perfect. False positives are expected. Suppress noisy rules in `.plint.toml`.

## Contributing

Open an issue (the templates ask for the source backing your proposal so rules stay grounded), or send a PR. The rule registry lives in [src/plint/static/heuristics/__init__.py](src/plint/static/heuristics/__init__.py). Each rule is a small module in the same directory. The model policy table is in [src/plint/core/policy.py](src/plint/core/policy.py).

## License

[MIT](LICENSE).
