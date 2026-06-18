# Setup — PyCharm + Claude Code (macOS)

This is the one-time environment setup. Do it in order. Estimated 30–45 min.

---

## Should you use Claude Code for this thesis? — Yes, with guardrails.

**Recommendation: yes.** You already have a paid Claude plan (Claude Code is included), and a methods-heavy thesis like this benefits specifically from an agent that can read your whole repo, run code, and respect a written set of rules. The danger for a *thesis* is the opposite of the usual one: an over-eager agent that writes plausible-but-unverified code and confident prose. You neutralise that with a `CLAUDE.md` governance file (already in this repo) that hard-codes your anti-hallucination discipline, and by keeping the human (you) as the one who runs code and pastes back real output.

**Use it for:** scaffolding modules, writing tests, debugging tracebacks, refactoring, drafting docstrings, explaining unfamiliar econometrics libraries.
**Do NOT let it:** invent data, claim a model "works" without you running it, fabricate citations, or auto-generate the whole pipeline at once. The `CLAUDE.md` enforces this.

A no-Claude-Code fallback is fine too — everything in this repo runs as plain Python. Claude Code is an accelerator, not a dependency.

---

## 1. Command-line tools & Python

```bash
# Xcode CLT (git, compilers) — skip if already installed
xcode-select --install

# Homebrew — skip if you have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# A modern Python (3.11 is a safe choice for the ML stack you'll add later)
brew install python@3.11 git
```

## 2. Get the project & make a virtual environment

```bash
cd "/Users/mheravetisyan/Claude/Projects/Bachelor Thesis - ML Model/lng_freight_thesis"

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. API keys (free, instant)

```bash
cp .env.example .env
# then edit .env and paste your two keys:
#   EIA_API_KEY  -> https://www.eia.gov/opendata/register.php
#   FRED_API_KEY -> https://fred.stlouisfed.org/docs/api/api_key.html
```

## 4. Initialise git (recommended)

```bash
git init
git add .
git commit -m "Phase 1: data-foundation skeleton"
# Optional: create a private GitHub repo and push. Keep it PRIVATE - thesis work.
```
`.env` and bulk data are already git-ignored; the provenance log is kept.

## 5. PyCharm

1. **Open** PyCharm → *Open* → select the `lng_freight_thesis` folder (open the folder itself, so it is the project root).
2. **Interpreter:** Settings → *Project: lng_freight_thesis* → *Python Interpreter* → gear → *Add* → *Existing environment* → point at `lng_freight_thesis/.venv/bin/python`.
3. **Mark `src` as Sources Root:** right-click the `src` folder → *Mark Directory as* → *Sources Root*. (Lets `import lngfreight` resolve cleanly.)
4. **Run the smoke test:** open `scripts/fetch_baseline.py` → Run. With keys set you should see `OK henry_hub_spot ...`, `OK brent_spot ...`.
5. **Run the tests:** right-click `tests/` → *Run pytest in tests*. Four tests should pass with no network.

## 6. Claude Code inside PyCharm

```bash
# Install (Node 18+ required; brew install node if needed)
npm install -g @anthropic-ai/claude-code

# From the project root, in PyCharm's integrated terminal (View → Tool Windows → Terminal):
cd "/Users/mheravetisyan/Claude/Projects/Bachelor Thesis - ML Model/lng_freight_thesis"
claude
```
- First run prompts you to log in with your Claude account (uses your paid plan).
- Claude Code automatically reads the `CLAUDE.md` in the repo root — that file encodes the thesis rules, so the agent inherits your discipline every session.
- Keep using PyCharm to **read diffs and run code yourself**. Treat Claude Code's output as a draft to review, never as verified results.

> If `claude` isn't found after install, ensure npm's global bin is on PATH:
> `echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc`

---

## Working rhythm (what "professional" looks like here)

1. One phase at a time (see `README.md` roadmap). Don't jump ahead.
2. You run every script and **paste real output** back before anything is called "working".
3. Every external data pull goes through `registry.get_variable()` so provenance is logged. No ad-hoc `requests.get` in notebooks.
4. Commit at the end of each working session with a message naming the phase.
5. Verification is a step, not an afterthought: tests for code, two-source cross-checks for data, primary-source confirmation for every date and figure.
