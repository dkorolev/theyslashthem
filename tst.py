#!/usr/bin/env python3
# This code is MIT-licensed, and the latest version is https://github.com/dkorolev/theyslashthem
"""
theyslashthem — slice a repo by profile (directories + GitHub gates).
Version 0.1, really alpha. MacOS only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

VERSION = "0.1"

BOLD_WHITE = "\033[1;37m"
BOLD_GREEN = "\033[1;32m"
BOLD_BLUE = "\033[1;34m"
BOLD_RED = "\033[1;31m"
RESET = "\033[0m"
GITIGNORE_ENTRY = "_tst/"
GITIGNORE_COMMENT = "# Added by theyslashthem, `tst.py`."


def load_profiles(repo_root: Path) -> dict:
    tst_yaml = repo_root / "tst.yml"
    if not tst_yaml.exists():
        print("tst.yml not found in repo root.", file=sys.stderr)
        sys.exit(1)
    yq_cmd = ["yq", "-o=json", ".theyslashthem_profiles", str(tst_yaml)]
    r = subprocess.run(yq_cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"command failed (exit {r.returncode}): {' '.join(yq_cmd)}", file=sys.stderr)
        if r.stderr.strip():
            print(f"  stderr: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        print(f"Failed to parse yq JSON output: {e}", file=sys.stderr)
        print(f"  raw output: {r.stdout[:500]}", file=sys.stderr)
        sys.exit(1)
    return data if isinstance(data, dict) else {}


def loc(repo_root: Path, profiles: dict) -> int:
    """Count lines of code using cloc against a fresh clone."""
    clone_dir = repo_root / "_tst" / "cloc_tmp"
    try:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        run_git(repo_root, ["clone", "--no-hardlinks", str(repo_root), str(clone_dir)])

        print(f"\n{BOLD_WHITE}Profile: {BOLD_BLUE}the entire repo{RESET}\n", flush=True)
        r = subprocess.run(
            "cloc --quiet . | grep -v 'github.com/AlDanial'",
            shell=True, cwd=clone_dir,
        )
        if r.returncode != 0:
            return 1

        for name, profile in profiles.items():
            dirs = profile.get("dirs", [])
            if not dirs:
                continue
            print(f"\n{BOLD_WHITE}Profile: {BOLD_GREEN}{name}{RESET}\n", flush=True)
            dir_args = " ".join(str(clone_dir / d) for d in dirs)
            subprocess.run(
                f"cloc --quiet {dir_args} | grep -v 'github.com/AlDanial'",
                shell=True,
            )
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

    return 0


def act_check(repo_root: Path, profiles: dict) -> int:
    """Run GitHub Actions locally using act against a fresh clone."""
    if not shutil.which("act"):
        print("act is not installed.", file=sys.stderr)
        return 1

    clone_dir = repo_root / "_tst" / "act_tmp"
    # results: list of (label, passed)
    results: list[tuple[str, bool]] = []

    try:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        run_git(repo_root, ["clone", "--no-hardlinks", str(repo_root), str(clone_dir)])

        # --- global: the entire repo ---
        print(f"\n{BOLD_WHITE}Profile: {BOLD_BLUE}the entire repo{RESET}\n", flush=True)
        t0 = time.monotonic()
        r = subprocess.run(["act"], cwd=clone_dir)
        elapsed = time.monotonic() - t0
        print(f"\nact ran for {elapsed:.1f} seconds\n", flush=True)
        results.append(("the entire repo", r.returncode == 0))

        # --- per-profile ---
        for name, profile in profiles.items():
            actions = profile.get("github_actions", [])
            if not actions:
                continue
            print(f"\n{BOLD_WHITE}Profile: {BOLD_GREEN}{name}{RESET}\n", flush=True)
            t0 = time.monotonic()
            profile_ok = True
            for wf in actions:
                r = subprocess.run(
                    ["act", "-W", f".github/workflows/{wf}"],
                    cwd=clone_dir,
                )
                if r.returncode != 0:
                    profile_ok = False
            elapsed = time.monotonic() - t0
            print(f"\nact ran for {elapsed:.1f} seconds\n", flush=True)
            results.append((name, profile_ok))
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

    # --- summary ---
    print(f"\n{BOLD_WHITE}Results:{RESET}\n", flush=True)
    any_failed = False
    for label, passed in results:
        if passed:
            status = f"{BOLD_GREEN}pass{RESET}"
        else:
            status = f"{BOLD_RED}FAIL{RESET}"
            any_failed = True
        print(f"  {label}: {status}")

    return 1 if any_failed else 0


def main() -> int:
    print(f"theyslashthem, v{VERSION} (really alpha, MacOS only)")

    repo_root = find_repo_root(Path.cwd())
    if not repo_root:
        print("Not inside a git repository.", file=sys.stderr)
        return 1

    profiles = load_profiles(repo_root)

    if len(sys.argv) == 2 and sys.argv[1] == "--cloc":
        return loc(repo_root, profiles)

    if len(sys.argv) == 2 and sys.argv[1] == "--act":
        return act_check(repo_root, profiles)

    fr = subprocess.run(["git", "filter-repo", "--version"], capture_output=True, text=True)
    if fr.returncode != 0:
        print("git-filter-repo is not installed. Install it with:\n  pip install git-filter-repo", file=sys.stderr)
        if fr.stderr.strip():
            print(f"  stderr: {fr.stderr.strip()}", file=sys.stderr)
        return 1

    if len(sys.argv) != 2:
        print("Usage: ./tst.py <profile>", file=sys.stderr)
        print("       ./tst.py --cloc", file=sys.stderr)
        print("       ./tst.py --act", file=sys.stderr)
        print(f"Profiles: {', '.join(profiles)}", file=sys.stderr)
        return 1

    profile_name = sys.argv[1]
    if profile_name not in profiles:
        print(f"Unknown profile: {profile_name}. Known: {', '.join(profiles)}", file=sys.stderr)
        return 1

    print(f"preparing profile {profile_name} ... ", end="", flush=True)

    ensure_gitignore(repo_root)

    profile = profiles[profile_name]
    keep_paths = list(profile.get("dirs", []))
    keep_paths.extend(f".github/workflows/{w}" for w in profile.get("github_actions", []))

    # Keep all root-level files; only subdirectories are filtered by profile
    for item in repo_root.iterdir():
        if item.is_file():
            keep_paths.append(item.name)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = repo_root / "_tst" / f"{stamp}_{profile_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    run_git(repo_root, ["clone", "--no-hardlinks", str(repo_root), str(out_dir)])

    tmp_repo = os.environ.get("TMP_GIT_REPO")
    if tmp_repo:
        run_git(out_dir, ["remote", "add", "tmp", tmp_repo])

    filter_to_paths(out_dir, keep_paths)

    # Copy pre-made stubs for excluded dirs.
    stubs = profile.get("stubs", {})
    stub_dirs: list[str] = []
    if stubs:
        stub_dirs = install_stubs(out_dir, repo_root, stubs)

    ensure_gitignore(out_dir)
    porcelain = run_git(out_dir, ["status", "--porcelain"]).stdout.strip()
    tracked_changes = [l for l in porcelain.splitlines() if not l.startswith("??")]
    if tracked_changes:
        run_git(out_dir, ["add", "-u"])
        run_git(out_dir, ["commit", "-m", "tst: profile setup"])

    # Commit stub .gitignore files so they become part of the baseline
    if stub_dirs:
        for d in stub_dirs:
            run_git(out_dir, ["add", f"{d}/.gitignore"])
        run_git(out_dir, ["commit", "-m", "tst: stub gitignores"])

    # Record the current HEAD as "root" so `git log root..HEAD` shows only new work
    root_hash = run_git(out_dir, ["rev-parse", "HEAD"]).stdout.strip()
    run_git(out_dir, ["branch", "root", root_hash])

    print("done")

    if tmp_repo:
        print(f"added 'tmp' upstream: {tmp_repo}")
    else:
        print("set TMP_GIT_REPO to add a 'tmp' upstream to the clone")

    shell = os.environ.get("SHELL", "/bin/bash")
    shell_args = setup_shell_prompt(shell, profile_name)
    subprocess.run(shell_args, cwd=out_dir)

    return handle_post_exit(out_dir, repo_root)


def find_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def ensure_gitignore(repo_root: Path) -> None:
    gitignore = repo_root / ".gitignore"
    content = gitignore.read_text() if gitignore.exists() else ""
    if GITIGNORE_ENTRY not in content:
        sep = "\n" if content and not content.endswith("\n") else ""
        with open(gitignore, "a") as f:
            f.write(f"{sep}{GITIGNORE_COMMENT}\n{GITIGNORE_ENTRY}\n")


def run_git(cwd: Path, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["git"] + args
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"command failed (exit {r.returncode}): {' '.join(cmd)}", file=sys.stderr)
        print(f"  cwd: {cwd}", file=sys.stderr)
        if r.stdout.strip():
            print(f"  stdout: {r.stdout.strip()}", file=sys.stderr)
        if r.stderr.strip():
            print(f"  stderr: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return r


def handle_post_exit(clone_dir: Path, repo_root: Path) -> int:
    """Check repo state after subshell exit and offer to copy commits to clipboard."""
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=clone_dir, capture_output=True, text=True,
    )
    if status.stdout.strip():
        print("Repo is not clean. Commit or stash your changes first.")
        print(f"To return to clone: cd {clone_dir.relative_to(repo_root)}")
        return 1

    commits_out = subprocess.run(
        ["git", "rev-list", "--reverse", "root..HEAD"],
        cwd=clone_dir, capture_output=True, text=True,
    )
    commits = commits_out.stdout.strip()
    if not commits:
        print("No new commits.")
        return 0

    commit_list = commits.splitlines()
    try:
        answer = input(f"Copy {len(commit_list)} commit diff(s) to clipboard? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0
    if answer not in ("", "y", "yes"):
        return 0

    return copy_commits_to_clipboard(clone_dir, commit_list)


def copy_commits_to_clipboard(clone_dir: Path, commits: list[str]) -> int:
    """Generate commit diffs and copy to clipboard."""
    clip_cmd: list[str] | None = None
    for cmd, args in [
        ("pbcopy", []),
        ("xclip", ["-selection", "clipboard"]),
        ("xsel", ["--clipboard"]),
    ]:
        if shutil.which(cmd):
            clip_cmd = [cmd] + args
            break
    if not clip_cmd:
        print("No clipboard command found (pbcopy, xclip, or xsel).", file=sys.stderr)
        return 1

    lines: list[str] = [
        "Apply the following commits to this repository, one at a time, in order.",
        "The oldest commits come first.",
        "Resolve any merge conflicts carefully.",
        "If a file does not end with a newline, add one.",
        "",
    ]
    for commit in commits:
        msg = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit],
            cwd=clone_dir, capture_output=True, text=True,
        ).stdout.rstrip()
        diff = subprocess.run(
            ["git", "diff", f"{commit}^", commit],
            cwd=clone_dir, capture_output=True, text=True,
        ).stdout.rstrip()
        lines += ["~~~", "", "Commit:", "", "```", msg, "```", "", "```", diff, "```", "", "~~~", ""]

    content = "\n".join(lines) + "\n"
    proc = subprocess.run(clip_cmd, input=content, text=True)
    if proc.returncode != 0:
        print("Failed to copy to clipboard.", file=sys.stderr)
        return 1

    head_short = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=clone_dir, capture_output=True, text=True,
    ).stdout.strip()
    print(f"Copied {len(commits)} commit diff(s) to clipboard (root..{head_short}).")
    return 0


def install_stubs(clone_dir: Path, repo_root: Path, stubs: dict) -> list[str]:
    """Copy pre-made stub directories into the clone for dirs that need a replacement.
    stubs maps dir name -> path (relative to repo root) of the replacement.
    Each installed stub gets a .gitignore that ignores everything except itself.
    Returns list of installed directory names."""
    installed = []
    for dir_name, stub_path in stubs.items():
        stub_src = repo_root / stub_path
        if not stub_src.is_dir():
            print(f"Missing stub: {stub_path}", file=sys.stderr)
            sys.exit(1)
        dest = clone_dir / dir_name
        shutil.copytree(str(stub_src), str(dest))
        (dest / ".gitignore").write_text("*\n!.gitignore\n")
        installed.append(dir_name)
    return installed


def filter_to_paths(clone_dir: Path, keep_paths: list[str]) -> None:
    args = ["filter-repo", "--force", "--prune-empty", "always"]
    for p in keep_paths:
        args += ["--path", p]
    run_git(clone_dir, args)


def setup_shell_prompt(shell: str, profile_name: str) -> list[str]:
    """Configure the subshell prompt to show [tst: profile]. Returns exec args."""
    if "zsh" in shell:
        zdotdir = tempfile.mkdtemp(prefix="tst_")
        home = os.path.expanduser("~")
        for name in (".zshenv", ".zprofile", ".zlogin", ".zlogout"):
            src = os.path.join(home, name)
            if os.path.exists(src):
                os.symlink(src, os.path.join(zdotdir, name))
        with open(os.path.join(zdotdir, ".zshrc"), "w") as f:
            f.write('[[ -f "$HOME/.zshrc" ]] && source "$HOME/.zshrc"\n')
            f.write(
                f'PROMPT="[%F{{yellow}}tst: %F{{cyan}}{profile_name}%f] $PROMPT"\n'
            )
        os.environ["ZDOTDIR"] = zdotdir
        return [shell]
    if "bash" in shell:
        rcdir = tempfile.mkdtemp(prefix="tst_")
        rcfile = os.path.join(rcdir, ".bashrc")
        with open(rcfile, "w") as f:
            f.write('[[ -f "$HOME/.bashrc" ]] && source "$HOME/.bashrc"\n')
            f.write(
                f'PS1="[\\[\\033[33m\\]tst: \\[\\033[36m\\]{profile_name}\\[\\033[0m\\]] $PS1"\n'
            )
        return [shell, "--rcfile", rcfile]
    return [shell]


if __name__ == "__main__":
    sys.exit(main())
