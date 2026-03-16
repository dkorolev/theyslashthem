#!/usr/bin/env python3
"""
theyslashthem — slice a repo by profile (directories + GitHub gates).
Version 0.1, really alpha. MacOS only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

VERSION = "0.1"
GITIGNORE_ENTRY = "_tst/"
GITIGNORE_COMMENT = "# Added by theyslashthem, `tst.py`."


def load_profiles(repo_root: Path) -> dict:
    tst_yaml = repo_root / "tst.yml"
    if not tst_yaml.exists():
        print("tst.yml not found in repo root.", file=sys.stderr)
        sys.exit(1)
    r = subprocess.run(
        ["yq", "-o=json", ".theyslashthem_profiles", str(tst_yaml)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"Failed to parse tst.yml: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(r.stdout)
    return data if isinstance(data, dict) else {}


def main() -> int:
    print(f"theyslashthem, v{VERSION} (really alpha, MacOS only)")

    if subprocess.run(["git", "filter-repo", "--version"], capture_output=True).returncode != 0:
        print("git-filter-repo is not installed. Install it with:\n  pip install git-filter-repo", file=sys.stderr)
        return 1

    repo_root = find_repo_root(Path.cwd())
    if not repo_root:
        print("Not inside a git repository.", file=sys.stderr)
        return 1

    profiles = load_profiles(repo_root)

    if len(sys.argv) != 2:
        print("Usage: ./tst.py <profile>", file=sys.stderr)
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

    # Ensure _tst/ is gitignored in the child repo so done.sh stays untracked
    ensure_gitignore(out_dir)
    if run_git(out_dir, ["status", "--porcelain"]).stdout.strip():
        run_git(out_dir, ["add", ".gitignore"])
        run_git(out_dir, ["commit", "-m", "Add _tst/ to .gitignore"])

    # Record the current HEAD as "root" so `git log root..HEAD` shows only new work
    root_hash = run_git(out_dir, ["rev-parse", "HEAD"]).stdout.strip()
    run_git(out_dir, ["branch", "root", root_hash])

    create_done_script(out_dir, repo_root)

    print("done")

    if tmp_repo:
        print(f"added 'tmp' upstream: {tmp_repo}")
    else:
        print("set TMP_GIT_REPO to add a 'tmp' upstream to the clone")

    shell = os.environ.get("SHELL", "/bin/bash")
    os.chdir(out_dir)
    shell_args = setup_shell_prompt(shell, profile_name)
    os.execv(shell, shell_args)


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
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(1)
    return r


DONE_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

DONE_DIR="$(pwd)"

# Must have a clean tree before preparing
if [ -n "$(git status --porcelain)" ]; then
    echo "Git tree is not clean. Commit or stash your changes first." >&2
    exit 1
fi

# Detect clipboard command
if command -v pbcopy &>/dev/null; then
    CLIP=pbcopy
elif command -v xclip &>/dev/null; then
    CLIP="xclip -selection clipboard"
elif command -v xsel &>/dev/null; then
    CLIP="xsel --clipboard"
else
    echo "No clipboard command found (pbcopy, xclip, or xsel)." >&2
    exit 1
fi

commits=$(git rev-list --reverse root..HEAD)

if [ -z "$commits" ]; then
    echo "No new commits on top of root."
    exit 0
fi

{
    echo "Apply the following commits to this repository, one at a time, in order."
    echo "The oldest commits come first."
    echo "Resolve any merge conflicts carefully."
    echo "If a file does not end with a newline, add one."
    echo ""
    for commit in $commits; do
        echo "~~~"
        echo ""
        echo "Commit:"
        echo ""
        echo '```'
        git log -1 --format='%B' "$commit"
        echo '```'
        echo ""
        echo '```'
        git diff "$commit"^ "$commit"
        echo '```'
        echo ""
        echo "~~~"
        echo ""
    done
} | $CLIP

count=$(echo "$commits" | wc -l | tr -d ' ')
echo "Copied $count commit diff(s) to clipboard (root..$(git rev-parse --short HEAD))."

RELATIVE_CLONE="${DONE_DIR#REPO_ROOT_PLACEHOLDER/}"
echo "Exit this shell to return to the parent repo."
echo "To return to clone:"
echo "cd $RELATIVE_CLONE"
""".lstrip()


def create_done_script(clone_dir: Path, repo_root: Path) -> None:
    tst_dir = clone_dir / "_tst"
    tst_dir.mkdir(parents=True, exist_ok=True)
    script = tst_dir / "done.sh"
    script.write_text(DONE_SCRIPT.replace("REPO_ROOT_PLACEHOLDER", str(repo_root.resolve())))
    script.chmod(0o755)


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
