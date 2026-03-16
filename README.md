# `theyslashthem`

A tool to slice and dice repositories so AI agents work on a narrow, relevant subset. Fewer tokens, less context exhaustion, better results, faster.

## Problem

In a mono-repo or otherwise large codebase, AI-assisted work often goes sideways: the model touches files and areas that have nothing to do with the task. That means:

- **Higher token usage** — more files and context in every turn.
- **Faster context exhaustion** — the window fills with irrelevant code.
- **Longer runs** — more edits, more back-and-forth.
- **Less correct behavior** — the agent wanders into code it shouldn’t change.

You want to give the agent *only* the slice of the repo that matters for the job.

## Solution

Design your project so you can **deliberately cut away** directories, CI gates, and tests, and hand the agent a **sliced (shallow) clone** of the repo. The agent works in that smaller world; when you’re done, you apply the resulting commits back into the full repo in a controlled way.

The agent will still run tests.

If and when there are isolated Github gates, they will still be run if you push the repo into some Github destination — I often use `dkorolev/tmp` for this.

Finally, the localized changes are presented in a way that makes them easy to incorporate into the broader, "outer", code base.

## Implementation

1. **Define “slices” of your repo**  
   You declare named parts of the repository: which directories belong to each slice and which GitHub (or other) check gates apply. Each slice is a self-contained view: some dirs in, some dirs out. This also has to do with Github gates.

2. **Shallow clone a slice**  
   The script performs a shallow clone and **removes** everything that isn’t in the chosen slice—directories, gates, tests, etc. You get a small repo where an AI agent can work without ever seeing or touching the rest of the codebase. The history and the commits are all there. 

3. **Apply changes back to the full repo**  
   After you finish work in the shallow repo, you run **one command** from inside it. That command produces a **prompt instructions and per-commit diffs** that you run in the **outer**, full, repository. You then run an AI agent in the outer repo with this copy-pasted prompt, to apply those commits intelligently and to resolve merge conflicts carefully.

### Example

Imagine one part of the project **generates** intermediate outputs and another **operates** on them. You then can:

- Put the generator in one slice and the processor in another.  
- Develop each slice with its own shallow clone and its own AI agent.  
- The agent on the generator never sees the processor; the agent on the processor never sees the generator.  
- **They never conflict** — and you merge back in a controlled way when you’re ready.

## Profiles

Profiles are defined in `tst.yml` at the repo root. Each profile lists:

- **`dirs`** — directories and files to keep in the sliced repo (everything else is removed from history).
- **`github_actions`** — GitHub Actions workflow filenames to keep (so only the relevant CI gates run).

All root-level files (LICENSE, README, etc.) are always kept.

Example `tst.yml`:

```yaml
theyslashthem_profiles:
  generator:
    dirs:
      - example/generator
      - example/input
      - example/intermediate
      - example/shared
    github_actions:
      - generator.yml
  analyzer:
    dirs:
      - example/analyzer
      - example/intermediate
      - example/shared
    github_actions:
      - analyzer.yml
```

To slice the repo for a profile, run:

```bash
./tst.py <profile>
```

It creates a clone under `_tst/yyyymmdd_hhmmss_<profile>` and **spawns a subshell** with that directory as the current working directory — you are now inside the sliced clone. Set `TMP_GIT_REPO` to add a `tmp` remote for pushing.

To see lines-of-code counts for the entire repository and each profile:

```bash
./tst.py --cloc
```

It runs `cloc` to print a summary table per profile, so you can see at a glance how large each slice is.

To run GitHub Actions locally with [act](https://github.com/nektos/act) for the entire repository and each profile:

```bash
./tst.py --act
```

It clones the repo, runs `act` on all workflows, then runs each profile's workflows individually, printing how long each run took.

When you're done working in the sliced repo, run **`_tst/done.sh`** from inside the clone. It checks for a clean git tree, then builds a single prompt (instructions plus per-commit diffs, oldest first) and **copies it to your clipboard**. It does not exit the shell: it prints the path of the clone and tells you to **exit the shell** (e.g. type `exit`) to return to the original repo. You can then paste the prompt in the outer repo and run an agent there to apply the commits.

## Summary

| You define | What the script does |
|-|-|
| Named slices (directories + gates/tests) | Shallow clone with everything else removed |
| Work in the shallow repo | One command → prompt + div for the outer repo |
| Outer repo runs that prompt | Applies commits and handles merge conflicts with your main agent |

Fewer irrelevant files, smaller context, and clearer boundaries for AI-assisted work.
