#!/usr/bin/env python3
"""Find git worktrees that are safe to remove, and remove them with --apply.

Report-only by default. Anything uncertain is kept and reported. Works on
macOS and Linux with Python 3.9+ and the standard library.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
GIT_ROOT = HOME / "Git"
APP_DBS = {
    "Purpose OS": HOME / ".purpose-os/userdata/statev2.sqlite",
    "T3 Code": HOME / ".t3/userdata/statev2.sqlite",
}
APP_WORKTREE_ROOTS = [HOME / ".purpose-os/worktrees", HOME / ".t3/worktrees"]
SCRATCH_ROOTS = [HOME / ".purpose-os/scratch", HOME / ".t3/scratch"]
SKIP_DIRS = {"node_modules", ".pnpm", "Pods", "build", "dist", ".venv", "DerivedData"}
NOW = datetime.now(timezone.utc)
RECENT = timedelta(hours=24)
LEFTOVER_AGE = 12 * 3600
DEV_PROCESS = re.compile(
    r"(^|/)(metro|idevicesyslog|qemu-system\S*|emulator|uvicorn|gunicorn|px0|chrome-headless-shell|adb)( |$)|"
    r"expo start|expo run|react-native start|/vite( |$)|next dev|next-server|next start|webpack serve|storybook|"
    r"log stream|simctl spawn|opencode serve|docker compose|GradleDaemon|tsc .*--watch|"
    r"(pnpm|npm|bun|yarn)( run)? (dev|start)( |$)"
)


def run(cmd, cwd=None, env=None, timeout=120):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def git(repo, *args, timeout=120):
    return run(["git", "-C", str(repo), *args], timeout=timeout)


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def within(path, parent):
    path, parent = str(path).rstrip("/"), str(parent).rstrip("/")
    return path == parent or path.startswith(parent + "/")


def norm(path):
    return os.path.realpath(os.path.expanduser(path)) if path else ""


def fmt_gb(kb):
    return f"{kb / 1048576:.1f} GB" if kb >= 104858 else f"{kb / 1024:.0f} MB"


def du_kb(path, timeout=300):
    code, out, _ = run(["du", "-sk", str(path)], timeout=timeout)
    try:
        return int(out.split()[0])
    except (IndexError, ValueError):
        return 0


def free_kb():
    return shutil.disk_usage(str(HOME)).free // 1024


# ---------------------------------------------------------------- threads


@dataclass
class Thread:
    app: str
    id: str
    title: str
    worktree: str
    root_id: str | None
    payload: dict

    def state(self):
        p = self.payload
        if p.get("deletedAt"):
            return "deleted"
        snoozed = parse_time(p.get("snoozedUntil"))
        if snoozed and snoozed > NOW:
            return f"snoozed until {p['snoozedUntil'][:16]}"
        updated = parse_time(p.get("updatedAt"))
        if updated and NOW - updated < RECENT:
            return "updated <24h ago"
        settled = p.get("settledAt") or p.get("settledOverride") == "settled"
        if not settled and not p.get("archivedAt"):
            return "active"
        return "archived" if p.get("archivedAt") else "settled"


def load_threads():
    """Returns (threads, errors). A DB that exists but can't be read is an error, which blocks removal."""
    threads, errors = {}, []
    for app, db in APP_DBS.items():
        if not db.exists():
            continue
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
            rows = con.execute("select thread_id, title, payload_json from orchestration_v2_projection_threads").fetchall()
            con.close()
        except sqlite3.Error as e:
            errors.append(f"{app}: {e}")
            continue
        for tid, title, payload in rows:
            p = json.loads(payload)
            threads[(app, tid)] = Thread(app, tid, title or "", norm(p.get("worktreePath")), (p.get("lineage") or {}).get("rootThreadId"), p)
    return threads, errors


def protecting_threads(path, threads):
    """Non-deleted threads on this worktree (or their roots) that are active, snoozed or recent.

    Returns (reasons, orphaned). orphaned is True when the only protection is an idle
    subagent whose root thread was deleted: the apps don't always settle children when
    they delete a finished run. Those worktrees are still kept, but reported for review.
    """
    reasons, orphaned = set(), True
    for t in threads.values():
        if not t.worktree or not within(t.worktree, path) or t.state() == "deleted":
            continue
        root = threads.get((t.app, t.root_id)) if t.root_id and t.root_id != t.id else None
        for candidate in (t, root):
            if candidate and candidate.state() not in ("deleted", "archived", "settled"):
                is_orphan = (candidate is t and candidate.state() == "active" and root is not None
                             and root.state() == "deleted"
                             and (t.payload.get("lineage") or {}).get("relationshipToParent") == "subagent")
                orphaned = orphaned and is_orphan
                suffix = f", but its root thread was deleted (idle since {t.payload.get('updatedAt', '?')[:16]})" if is_orphan else ""
                reasons.add(f"{candidate.app} thread '{candidate.title[:50]}' {candidate.state()}{suffix}")
    return sorted(reasons), orphaned and bool(reasons)


def thread_summary(path, threads):
    states = sorted({t.state() for t in threads.values() if t.worktree and within(t.worktree, path)})
    return ", ".join(states) if states else "no app thread"


# -------------------------------------------------------------- processes


@dataclass
class Proc:
    pid: int
    ppid: int
    age: int
    rss_kb: int
    command: str
    cwd: str = ""


def parse_etime(value):
    days, _, rest = value.strip().rpartition("-")
    parts = [int(x) for x in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days) if days else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def list_processes():
    code, out, _ = run(["ps", "-A", "-o", "pid=,ppid=,uid=,etime=,rss=,command="])
    procs = {}
    for line in out.splitlines():
        f = line.split(None, 5)
        if len(f) < 6 or int(f[2]) != os.getuid():
            continue
        procs[int(f[0])] = Proc(int(f[0]), int(f[1]), parse_etime(f[3]), int(f[4]), f[5])
    if sys.platform == "darwin":
        _, out, _ = run(["lsof", "-a", "-d", "cwd", "-u", str(os.getuid()), "-Fpn"])
        pid = None
        for line in out.splitlines():
            if line.startswith("p"):
                pid = int(line[1:])
            elif line.startswith("n") and pid in procs:
                procs[pid].cwd = line[1:]
    else:
        for p in procs.values():
            try:
                p.cwd = os.readlink(f"/proc/{p.pid}/cwd").removesuffix(" (deleted)")
            except OSError:
                pass
    return procs


def fsmonitor_targets(procs):
    """Maps fsmonitor daemon pid -> watched worktree. git only runs this daemon on macOS and Windows."""
    targets = {}
    for p in procs.values():
        if "fsmonitor--daemon" not in p.command or sys.platform != "darwin":
            continue
        _, out, _ = run(["lsof", "-p", str(p.pid), "-Fn"])
        for line in out.splitlines():
            m = re.match(r"n(.+?)/\.git(?:/worktrees/([^/]+))?(?:/fsmonitor--daemon\.ipc)?$", line)
            if m:
                targets[p.pid] = f"{m.group(1)} (worktree {m.group(2)})" if m.group(2) else m.group(1)
                if m.group(2):
                    break
    return targets


# ---------------------------------------------------------------- repos


def find_repos():
    """Main checkouts under ~/Git, plus repos that own worktrees in the app folders."""
    repos = set()
    if GIT_ROOT.is_dir():
        for dirpath, dirnames, filenames in os.walk(GIT_ROOT):
            depth = len(Path(dirpath).relative_to(GIT_ROOT).parts)
            if ".git" in dirnames:
                repos.add(norm(dirpath))
            if ".git" in dirnames or ".git" in filenames or depth >= 4:
                dirnames[:] = []
            else:
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
    for root in APP_WORKTREE_ROOTS:
        for wt in root.glob("*/*"):
            gitfile = wt / ".git"
            if wt.is_symlink() or not gitfile.is_file():
                continue
            m = re.match(r"gitdir: (.+)/\.git/worktrees/[^/]+$", gitfile.read_text().strip())
            if m and Path(m.group(1), ".git").is_dir():
                repos.add(norm(m.group(1)))
    return sorted(repos)


def list_worktrees(repo):
    code, out, err = git(repo, "worktree", "list", "--porcelain")
    entries, cur = [], {}
    for line in out.splitlines() + [""]:
        if not line:
            if cur:
                entries.append(cur)
            cur = {}
            continue
        key, _, value = line.partition(" ")
        cur[key] = value or True
    return entries[1:]  # the first entry is the main checkout


def default_branch(repo):
    code, out, _ = git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    return out.strip() if code == 0 and out.strip() else None


def github_slug(repo):
    _, out, _ = git(repo, "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", out.strip())
    return m.group(1) if m else None


def gh_env(repo):
    """Lets the gh wrapper pick the account from the repo's `github.user`, as it would in a shell there."""
    env = dict(os.environ)
    _, user, _ = git(repo, "config", "--get", "github.user")
    if user.strip():
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
    return env


# ---------------------------------------------------------------- analysis


@dataclass
class Worktree:
    repo: str
    path: str
    branch: str | None
    head: str
    verdict: str = "keep"  # remove | keep-active | keep-needs-me
    why: str = ""
    details: list[str] = field(default_factory=list)
    threads: str = ""
    du_kb: int = 0
    freed_kb: int | None = None


def dirty_files(path):
    code, out, err = git(path, "status", "--porcelain=v1", "--untracked-files=all")
    if code != 0:
        return [f"git status failed: {err.strip()[:200]}"]
    return [line for line in out.splitlines() if line.strip()]


def merge_status(wt, default, slug, gh_cache):
    """Returns (merged, reason). merged is True, False, or None for unknown."""
    if default and git(wt.repo, "merge-base", "--is-ancestor", wt.head, default)[0] == 0:
        return True, f"HEAD is in {default}"
    if not wt.branch:
        return False, "detached HEAD not in the default branch"
    if not slug:
        return None, "origin is not a GitHub repo"
    key = (slug, wt.branch)
    if key not in gh_cache:
        code, out, err = run(
            ["gh", "pr", "list", "-R", slug, "--head", wt.branch, "--state", "all", "--limit", "20",
             "--json", "number,state,headRefOid,url"],
            cwd=wt.repo, env=gh_env(wt.repo), timeout=60)
        try:
            prs = json.loads(out) if code == 0 else None
        except ValueError:
            prs = None
        gh_cache[key] = (prs, err.strip().splitlines()[-1:] if err else [])
    prs, err = gh_cache[key]
    if prs is None:
        return None, f"gh unknown: {' '.join(err)[:160]}"
    if any(pr["state"] == "OPEN" for pr in prs):
        return False, "open PR #" + ", #".join(str(pr["number"]) for pr in prs if pr["state"] == "OPEN")
    merged = [pr for pr in prs if pr["state"] == "MERGED"]
    if not merged:
        return False, "no merged PR for the branch"
    for pr in merged:
        if pr["headRefOid"] == wt.head:
            return True, f"PR #{pr['number']} merged at this HEAD"
    if not default:
        return None, "no origin/HEAD to compare extra commits with"
    for pr in merged:
        oid = pr["headRefOid"]
        if git(wt.repo, "cat-file", "-e", f"{oid}^{{commit}}")[0] != 0:
            git(wt.repo, "fetch", "--quiet", "origin", f"refs/pull/{pr['number']}/head", timeout=120)
        if git(wt.repo, "merge-base", "--is-ancestor", oid, wt.head)[0] != 0:
            continue
        # Commits after the merged PR head count as merged only if each has an identical patch in the default branch.
        _, merges, _ = git(wt.repo, "rev-list", "--merges", f"{oid}..{wt.head}", f"^{default}")
        if merges.strip():
            return False, f"merge commits after PR #{pr['number']} head"
        _, cherry, _ = git(wt.repo, "cherry", default, wt.head, oid)
        extra = [line for line in cherry.splitlines() if line.startswith("+")]
        if extra:
            return False, f"{len(extra)} commit(s) after PR #{pr['number']} not in {default}"
        return True, f"PR #{pr['number']} merged; later commits have identical patches in {default}"
    return False, "commits not in the merged PR (PR head is not in this branch)"


def parent_gone(p, procs):
    """Orphans reparent to launchd/init (not ours) on macOS and to `systemd --user` on Linux."""
    parent = procs.get(p.ppid)
    return parent is None or "systemd --user" in parent.command


def busy_processes(path, procs):
    return [p for p in procs.values() if p.cwd and within(norm(p.cwd), path) and p.pid != os.getpid()]


def analyze(repos, threads, procs, fetch):
    worktrees, notes, gh_cache = [], [], {}
    for repo in repos:
        entries = list_worktrees(repo)
        if not entries:
            continue
        if fetch:
            code, _, err = git(repo, "fetch", "--quiet", "origin", timeout=300)
            if code != 0:
                notes.append(f"{repo}: git fetch failed ({err.strip()[:120]})")
        default, slug = default_branch(repo), github_slug(repo)
        if not default:
            notes.append(f"{repo}: no origin/HEAD; only merged PRs at HEAD count")
        for e in entries:
            path = e["worktree"]
            wt = Worktree(repo, path, (e.get("branch") or "").replace("refs/heads/", "") or None, e.get("HEAD", ""))
            worktrees.append(wt)
            wt.threads = thread_summary(path, threads)
            if e.get("prunable") or not os.path.isdir(path):
                wt.verdict, wt.why = "keep-needs-me", "registered but missing on disk (git worktree prune clears it)"
                continue
            if os.path.islink(path) or norm(path) == repo:
                wt.verdict, wt.why = "keep-needs-me", "path is a symlink or the main checkout"
                continue
            if e.get("locked"):
                wt.verdict, wt.why = "keep-needs-me", f"locked: {e['locked'] if e['locked'] is not True else ''}".strip()
                continue
            protected, orphaned = protecting_threads(path, threads)
            if protected:
                wt.verdict = "keep-needs-me" if orphaned else "keep-active"
                wt.why, wt.details = protected[0], protected[1:]
                continue
            # The HEAD reflog moves on commit, checkout and reset. The index is no use here:
            # apps polling `git status` rewrite it constantly.
            reflog = Path(git(path, "rev-parse", "--absolute-git-dir")[1].strip() or "/nonexistent", "logs/HEAD")
            if reflog.exists() and NOW - datetime.fromtimestamp(reflog.stat().st_mtime, timezone.utc) < RECENT:
                wt.verdict, wt.why = "keep-active", "HEAD moved <24h ago"
                continue
            dirty = dirty_files(path)
            if dirty:
                wt.verdict, wt.why, wt.details = "keep-needs-me", f"dirty ({len(dirty)} files)", dirty
                continue
            merged, reason = merge_status(wt, default, slug, gh_cache)
            if not merged:
                wt.verdict = "keep-needs-me"
                wt.why = ("unknown: " if merged is None else "unmerged: ") + reason
                continue
            owned = [p for p in busy_processes(path, procs) if not parent_gone(p, procs)]
            if owned:
                wt.verdict, wt.why = "keep-needs-me", f"merged ({reason}) but in use by a process with a live parent"
                wt.details = [f"pid {p.pid} (parent {p.ppid}): {p.command[:100]}" for p in owned]
                continue
            wt.verdict, wt.why = "remove", reason
    return worktrees, notes


def find_orphans(repos):
    """Folders in worktree roots that no repo's `git worktree list` knows about."""
    known = set()
    for repo in repos:
        known.update(norm(e["worktree"]) for e in list_worktrees(repo))
    roots = list(APP_WORKTREE_ROOTS) + [p for p in GIT_ROOT.glob("*/worktrees") if p.is_dir()]
    orphans = []
    for root in roots:
        for d in sorted(root.glob("*/*")):
            if d.name.startswith("."):
                continue
            if d.is_symlink():
                orphans.append((str(d), f"symlink to {os.readlink(d)}; never removed", 0))
            elif d.is_dir() and norm(d) not in known:
                orphans.append((str(d), "not a registered worktree", du_kb(d)))
    return orphans


# ---------------------------------------------------------------- removal


def stop(procs_inside, log):
    for p in procs_inside:
        log.append(f"stopping pid {p.pid} ({p.command[:80]}) cwd {p.cwd}")
        try:
            os.kill(p.pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    deadline = time.time() + 10
    while time.time() < deadline:
        alive = [p for p in procs_inside if pid_alive(p.pid)]
        if not alive:
            return []
        time.sleep(0.5)
    return [p for p in procs_inside if pid_alive(p.pid)]


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def remove(wt, only, log):
    if only and wt.path not in only:
        wt.verdict, wt.why = "keep-needs-me", f"not in --only list (was: {wt.why})"
        return
    # Re-check right before removing: HEAD and cleanliness can change between analysis and removal.
    _, head, _ = git(wt.path, "rev-parse", "HEAD")
    if head.strip() != wt.head or dirty_files(wt.path):
        wt.verdict, wt.why = "keep-needs-me", "changed since analysis"
        return
    still_running = stop(busy_processes(wt.path, list_processes()), log)
    if still_running:
        wt.verdict, wt.why = "keep-needs-me", f"process(es) did not stop: {[p.pid for p in still_running]}"
        return
    before = free_kb()
    code, _, err = git(wt.repo, "worktree", "remove", wt.path)
    if code != 0:
        wt.verdict, wt.why = "keep-needs-me", f"git worktree remove failed: {err.strip()[:200]}"
        return
    git(wt.repo, "worktree", "prune")
    wt.freed_kb = free_kb() - before
    log.append(f"removed {wt.path} ({wt.repo}, {wt.branch}); free space +{fmt_gb(max(wt.freed_kb, 0))}")


# ---------------------------------------------------------------- reporting


def leftover_report(procs, threads, removed_paths, fs_targets):
    active_paths = [t.worktree for t in threads.values() if t.worktree and t.state() not in ("deleted", "archived", "settled")]
    lines = []
    for p in sorted(procs.values(), key=lambda p: -p.rss_kb):
        if "fsmonitor--daemon" in p.command or not DEV_PROCESS.search(p.command):
            continue
        reasons = []
        if parent_gone(p, procs):
            reasons.append("parent gone")
        cwd = norm(p.cwd) if p.cwd else ""
        if cwd and (not os.path.isdir(cwd) or any(within(cwd, r) for r in removed_paths)):
            reasons.append("cwd missing/removed")
        if p.age > LEFTOVER_AGE and not any(within(cwd, a) for a in active_paths):
            reasons.append(f"running {p.age // 3600}h, no active thread")
        if reasons:
            lines.append(f"- pid {p.pid}, {p.age // 3600}h, {p.rss_kb // 1024} MB, cwd {p.cwd or '?'}: `{p.command[:110]}` ({'; '.join(reasons)})")
    by_target = {}
    for pid, target in fs_targets.items():
        by_target.setdefault(target, []).append(pid)
    fs = [p for p in procs.values() if "fsmonitor--daemon" in p.command]
    stale = [t for t in by_target if not os.path.isdir(t.split(" (worktree")[0])]
    dupes = {t: pids for t, pids in by_target.items() if len(pids) > 1}
    outside = [t for t in by_target if not within(t, GIT_ROOT) and not within(t, HOME / ".donnes")]
    summary = f"- fsmonitor daemons: {len(fs)} ({sum(p.rss_kb for p in fs) // 1024} MB RSS), {len(by_target)} distinct worktrees"
    if dupes:
        summary += "; duplicates: " + "; ".join(f"{t} pids {pids}" for t, pids in dupes.items())
    if stale:
        summary += "; watching missing paths: " + ", ".join(stale)
    if outside:
        summary += "; outside ~/Git: " + ", ".join(outside)
    lines.append(summary)
    lines.extend(container_report(removed_paths))
    return lines


def container_report(removed_paths):
    lines = []
    if shutil.which("docker"):
        fmt = '{{.Names}}\t{{.RunningFor}}\t{{.Label "com.docker.compose.project.working_dir"}}'
        code, out, _ = run(["docker", "ps", "--format", fmt], timeout=20)
        mem = dict(line.split("\t", 1) for line in run(["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}"], timeout=30)[1].splitlines() if "\t" in line)
        for line in out.splitlines() if code == 0 else []:
            name, age, workdir = (line.split("\t") + ["", ""])[:3]
            flag = " (compose dir missing/removed)" if workdir and (not os.path.isdir(workdir) or any(within(norm(workdir), r) for r in removed_paths)) else ""
            lines.append(f"- container {name}, up {age}, {mem.get(name, '?').split(' /')[0]}, from {workdir or '?'}{flag}")
    if sys.platform == "darwin" and shutil.which("xcrun"):
        _, out, _ = run(["xcrun", "simctl", "list", "devices", "booted"], timeout=30)
        lines.extend(f"- booted simulator: {line.strip()}" for line in out.splitlines() if "(Booted)" in line)
    return lines


def cache_report(repos):
    candidates = [
        ("pnpm stores", sorted((HOME / "Library/pnpm/store").glob("v*")) + sorted((HOME / ".local/share/pnpm/store").glob("v*"))),
        ("Gradle caches", [HOME / ".gradle/caches"]),
        ("Android AVDs", [HOME / ".android/avd"]),
        ("Android system images", [HOME / "Library/Android/sdk/system-images", HOME / "Android/Sdk/system-images"]),
        ("CoreSimulator devices", [HOME / "Library/Developer/CoreSimulator/Devices"]),
        ("Xcode DerivedData", [HOME / "Library/Developer/Xcode/DerivedData"]),
        ("CocoaPods cache", [HOME / "Library/Caches/CocoaPods"]),
        ("Scratch folders", SCRATCH_ROOTS),
        ("T3 build", [HOME / ".t3/build"]),
    ]
    pins = set()
    for repo in repos:
        try:
            pm = json.loads(Path(repo, "package.json").read_text()).get("packageManager", "")
        except (OSError, ValueError):
            continue
        if pm.startswith("pnpm@"):
            pins.add(pm.split("@")[1].split("+")[0])
    lines = []
    for label, paths in candidates:
        sizes = [(p, du_kb(p)) for p in paths if p.exists()]
        sizes = [(p, kb) for p, kb in sizes if kb > 512 * 1024]
        if sizes:
            lines.append(f"- {label}: " + ", ".join(f"{p.name if label == 'pnpm stores' else p} {fmt_gb(kb)}" for p, kb in sizes))
    if pins:
        lines.append(f"- pnpm versions pinned by repos: {', '.join(sorted(pins))} (store v3 = pnpm 7-9, v10 = pnpm 10, v11 = pnpm 11)")
    old_scratch = []
    for root in SCRATCH_ROOTS:
        for d in root.glob("*"):
            if d.is_dir() and time.time() - d.stat().st_mtime > 7 * 86400:
                kb = du_kb(d)
                if kb > 1048576:
                    old_scratch.append((kb, d))
    for kb, d in sorted(old_scratch, reverse=True):
        clones = [str(g.parent.relative_to(d)) for g in d.glob("*/.git") if g.is_dir()]
        lines.append(f"- old scratch: {d} {fmt_gb(kb)}" + (f", contains full clone(s): {', '.join(clones)}" if clones else ""))
    tmp = Path("/private/tmp" if sys.platform == "darwin" else "/tmp")
    for d in tmp.iterdir() if tmp.is_dir() else []:
        try:
            if d.owner() != HOME.name or time.time() - d.lstat().st_mtime < 86400:
                continue
        except (OSError, KeyError):
            continue
        kb = du_kb(d) if d.is_dir() and not d.is_symlink() else d.lstat().st_size // 1024
        if kb > 1048576:
            lines.append(f"- {d} {fmt_gb(kb)} (temp, older than a day)")
    if shutil.which("docker"):
        code, out, _ = run(["docker", "system", "df", "--format", "{{.Type}}: {{.Size}} ({{.Reclaimable}} reclaimable)"], timeout=20)
        if code == 0 and out.strip():
            lines.append("- Docker: " + "; ".join(out.strip().splitlines()))
    lines.append("- sizes above are `du`; pnpm on APFS/btrfs clones files, so real reclaimable space is lower")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="remove worktrees that pass every check")
    ap.add_argument("--only", action="append", default=[], help="with --apply, remove only these paths (repeatable)")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch (read-only audit)")
    ap.add_argument("--no-caches", action="store_true", help="skip the cache size report")
    args = ap.parse_args()

    if args.apply:
        lock = open(HOME / ".cache/clean-worktrees.lock" if (HOME / ".cache").is_dir() else "/tmp/clean-worktrees.lock", "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("another clean-worktrees --apply is running; nothing removed")

    threads, db_errors = load_threads()
    procs = list_processes()
    repos = find_repos()
    worktrees, notes = analyze(repos, threads, procs, fetch=not args.no_fetch)
    notes = [f"thread DB unreadable: {e}" for e in db_errors] + notes
    log = []
    if db_errors:
        for wt in worktrees:
            if wt.verdict == "remove":
                wt.verdict, wt.why = "keep-needs-me", f"thread DB unreadable, so thread state is unknown (was: {wt.why})"
    start_free = free_kb()
    for wt in worktrees:
        if wt.verdict == "remove":
            if args.apply:
                remove(wt, set(args.only), log)
            else:
                wt.du_kb = du_kb(wt.path)
    end_free = free_kb()
    removed = [wt for wt in worktrees if wt.freed_kb is not None]

    out = [f"# clean-worktrees {'(applied)' if args.apply else '(report only)'} {NOW.astimezone():%Y-%m-%d %H:%M}",
           f"{len(repos)} repos, {len(worktrees)} linked worktrees, free space {fmt_gb(start_free)}"]
    out.append("\n## Removed" if args.apply else "\n## Would remove")
    for wt in worktrees:
        if wt.verdict == "remove" or wt.freed_kb is not None:
            size = f"freed {fmt_gb(max(wt.freed_kb, 0))} (df)" if wt.freed_kb is not None else f"{fmt_gb(wt.du_kb)} by du, real freed unknown until removal"
            out.append(f"- {wt.path} [{Path(wt.repo).name}, {wt.branch or 'detached'}]: {wt.why}; threads: {wt.threads}; {size}")
    if args.apply:
        out.append(f"- total: free space {fmt_gb(start_free)} -> {fmt_gb(end_free)} ({fmt_gb(end_free - start_free)} by df)")
    out.append("\n## Kept, needs me")
    for wt in worktrees:
        if wt.verdict == "keep-needs-me":
            out.append(f"- {wt.path} [{Path(wt.repo).name}, {wt.branch or 'detached'}]: {wt.why}; threads: {wt.threads}")
            out.extend(f"    {d}" for d in wt.details[:15])
            if len(wt.details) > 15:
                out.append(f"    ... {len(wt.details) - 15} more")
    for path, why, kb in find_orphans(repos):
        out.append(f"- orphaned folder {path}: {why}" + (f", {fmt_gb(kb)} by du" if kb else ""))
    out.append("\n## Kept, active or snoozed")
    for wt in worktrees:
        if wt.verdict == "keep-active":
            out.append(f"- {wt.path} [{Path(wt.repo).name}]: {wt.why}")
    out.append("\n## Leftover processes (not stopped)")
    out.extend(leftover_report(procs, threads, [wt.path for wt in removed], fsmonitor_targets(procs)))
    if not args.no_caches:
        out.append("\n## Caches and scratch (report only)")
        out.extend(cache_report(repos))
    if notes or log:
        out.append("\n## Notes")
        out.extend(f"- {n}" for n in notes + log)
    print("\n".join(out))


if __name__ == "__main__":
    main()
