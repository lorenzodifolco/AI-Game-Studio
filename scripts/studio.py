#!/usr/bin/env python3
"""studio.py - deterministic backbone of the AI Game Studio (stdlib only).

Owns pipeline state (games/<slug>/state.json), exit-criteria checks, human
gates, git checkpoints, routing of the next actions, and Godot wrappers.
LLM agents produce artifacts; this script decides whether a stage is done.

Run `python scripts/studio.py -h` for commands.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parent.parent)
STUDIO = ROOT / "studio"
GAMES = ROOT / "games"
TEMPLATE_DIR = ROOT / "scripts" / "templates" / "godot-mobile"

ALWAYS_HUMAN_GATES = {"release"}
CONCEPT_STATUSES = {"new", "shortlisted", "rejected", "parked", "greenlit"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GODOT_ERROR_RE = re.compile(r"SCRIPT ERROR|Parse Error|Failed to load script|Compile Error", re.I)
TEXT_SUFFIXES = {".gd", ".tscn", ".tres", ".godot", ".cfg", ".md", ".svg", ".json", ".txt"}

try:  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:  # pragma: no cover
    pass


# --------------------------------------------------------------------------- utils
class StudioError(Exception):
    """Expected failure: printed without traceback, exit code 1."""


def today() -> str:
    return dt.date.today().isoformat()


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise StudioError(f"missing {path.relative_to(ROOT)}")
    except json.JSONDecodeError as e:
        raise StudioError(f"invalid JSON in {path.relative_to(ROOT)}: {e}")


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def config() -> dict:
    return load_json(STUDIO / "config.json")


def pipeline() -> list[dict]:
    return load_json(STUDIO / "pipeline.json")["stages"]


def stage_ids() -> list[str]:
    return [s["id"] for s in pipeline()]


def stage_def(stage: str) -> dict:
    for s in pipeline():
        if s["id"] == stage:
            return s
    raise StudioError(f"unknown stage '{stage}'")


def is_agent_session() -> bool:
    """True when running inside a Claude Code tool call (Claude sets CLAUDECODE=1)."""
    return bool(os.environ.get("CLAUDECODE"))


def require_human(action: str) -> None:
    if is_agent_session():
        raise StudioError(
            f"'{action}' is a human-only decision. Ask the user to run this command "
            "in their own terminal (not through Claude)."
        )


def read_frontmatter(path: Path) -> dict[str, str]:
    """Minimal YAML-frontmatter reader: top-level `key: scalar` pairs only."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line[0] in " \t-#":
            continue
        key, sep, val = line.partition(":")
        if sep:
            val = re.sub(r"\s+#.*$", "", val).strip().strip("\"'")
            out[key.strip()] = val
    return out


def set_frontmatter(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^(---\r?\n)(.*?)(\r?\n---)", text, re.S)
    if not m:
        raise StudioError(f"{path} has no frontmatter")
    lines = m.group(2).splitlines()
    for key, val in updates.items():
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(key)}\s*:", line):
                lines[i] = f"{key}: {val}"
                break
        else:
            lines.append(f"{key}: {val}")
    path.write_text(m.group(1) + "\n".join(lines) + text[m.end(2):], encoding="utf-8")


def check_slug(slug: str) -> str:
    if not SLUG_RE.match(slug):
        raise StudioError(f"invalid slug '{slug}' (use kebab-case: a-z, 0-9, -)")
    return slug


# --------------------------------------------------------------------------- data access
def game_dir(slug: str) -> Path:
    return GAMES / check_slug(slug)


def load_state(slug: str) -> dict:
    p = game_dir(slug) / "state.json"
    if not p.exists():
        raise StudioError(f"no game '{slug}' (games/{slug}/state.json missing)")
    return load_json(p)


def save_state(slug: str, st: dict) -> None:
    save_json(game_dir(slug) / "state.json", st)


def list_games() -> list[dict]:
    out = []
    for p in sorted(GAMES.glob("*/state.json")):
        try:
            out.append(load_json(p))
        except StudioError:
            out.append({"slug": p.parent.name, "stage": "?", "status": "corrupt"})
    return out


def active_games() -> list[dict]:
    return [g for g in list_games() if g.get("status") == "active"]


def list_concepts() -> list[dict]:
    out = []
    for p in sorted((STUDIO / "concepts").glob("*.md")):
        if p.name.startswith("_") or p.stem.isupper():
            continue  # RANKING.md, _notes.md ...
        fm = read_frontmatter(p)
        fm["_path"] = str(p.relative_to(ROOT)).replace("\\", "/")
        fm.setdefault("slug", p.stem)
        out.append(fm)
    return out


def latest_research() -> tuple[dt.date, Path] | None:
    best = None
    for p in (STUDIO / "research").glob("*/report.md"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.parent.name)
        if m:
            d = dt.date.fromisoformat(m.group(1))
            if best is None or d > best[0]:
                best = (d, p)
    return best


# --------------------------------------------------------------------------- godot
def find_godot() -> str | None:
    cand = os.environ.get("GODOT_BIN") or config().get("godot_bin") or ""
    if cand and Path(cand).exists():
        return cand
    for name in ("godot", "godot4", "Godot"):
        p = shutil.which(name)
        if p:
            return p
    local = sorted((ROOT / "tools").glob("**/Godot*console*.exe")) + sorted((ROOT / "tools").glob("**/Godot_v4*"))
    for p in local:
        if p.is_file() and p.suffix.lower() in ("", ".exe", ".x86_64", ".64", ".arm64"):
            return str(p)
    return None


def godot_run(args: list[str], timeout: int = 600) -> tuple[int, str]:
    godot = find_godot()
    if not godot:
        return -1, "BLOCKED: Godot not found. Set GODOT_BIN or godot_bin in studio/config.json (see: studio.py doctor)."
    try:
        r = subprocess.run([godot, *args], capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"Godot timed out after {timeout}s"
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run_tests(slug: str) -> tuple[int, str]:
    """Return (code, output). code -1 = environment blocked, 0 = pass."""
    proj = game_dir(slug) / "project"
    if not (proj / "project.godot").exists():
        return 1, f"no Godot project at games/{slug}/project"
    if not (proj / "tests" / "test_runner.gd").exists():
        return 1, f"missing games/{slug}/project/tests/test_runner.gd"
    if not (proj / ".godot").exists():  # first run: build import cache + class registry
        code, out = godot_run(["--headless", "--path", str(proj), "--import"])
        if code == -1:
            return code, out
    code, out = godot_run(["--headless", "--path", str(proj), "-s", "res://tests/test_runner.gd"])
    if code == 0 and GODOT_ERROR_RE.search(out):
        code = 1
        out += "\nstudio.py: script errors detected in output -> treating run as FAILED"
    return code, out


# --------------------------------------------------------------------------- criteria
def eval_criterion(slug: str, c: dict, run_slow: bool = True) -> tuple[bool | None, str]:
    """Return (ok, detail). ok None = not evaluated / blocked by environment."""
    gdir = game_dir(slug)
    t = c["type"]
    if t == "tests":
        if not run_slow:
            return None, "tests (not run in fast mode)"
        code, out = run_tests(slug)
        if code == -1:
            return None, out
        tail = " | ".join(l for l in out.strip().splitlines()[-3:])
        return code == 0, ("tests pass" if code == 0 else f"tests failing: {tail}")
    if t == "glob":
        hits = list(gdir.glob(c["pattern"]))
        return bool(hits), f"{c['pattern']}: {len(hits)} match(es)"
    p = gdir / c["path"]
    if not p.is_file() or p.stat().st_size == 0:
        return False, f"missing {c['path']}"
    text = p.read_text(encoding="utf-8", errors="replace")
    if t == "file":
        return True, f"{c['path']} present"
    if t == "headings":
        found = {re.sub(r"^\d+[.)]\s*", "", h).strip().lower()
                 for h in re.findall(r"^#{1,4}\s+(.+?)\s*#*\s*$", text, re.M)}
        missing = [h for h in c["headings"] if h.lower() not in found]
        return (not missing), (f"{c['path']} missing sections: {', '.join(missing)}" if missing
                               else f"{c['path']} has all {len(c['headings'])} sections")
    if t == "checklist":
        done = len(re.findall(r"^\s*[-*] \[[xX]\]", text, re.M))
        todo = len(re.findall(r"^\s*[-*] \[ \]", text, re.M))
        if done + todo == 0:
            return False, f"{c['path']} has no checklist items"
        return todo == 0, f"{c['path']}: {done}/{done + todo} items done"
    if t == "contains":
        ok = re.search(c["pattern"], text, re.M | re.I) is not None
        return ok, (f"{c['path']} OK" if ok else f"{c['path']} lacks {c.get('label', c['pattern'])}")
    raise StudioError(f"unknown criterion type '{t}'")


def check_stage(slug: str, run_slow: bool = True) -> list[tuple[dict, bool | None, str]]:
    st = load_state(slug)
    return [(c, *eval_criterion(slug, c, run_slow)) for c in stage_def(st["stage"])["exit"]]


def gate_policy(gate: str) -> str:
    if gate in ALWAYS_HUMAN_GATES:
        return "human"
    return config().get("gates", {}).get(gate, "human")


# --------------------------------------------------------------------------- git
def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def in_git_repo() -> bool:
    try:
        return git("rev-parse", "--is-inside-work-tree").returncode == 0
    except FileNotFoundError:
        return False


def commit(paths: list[str], message: str, tag: str | None = None) -> str:
    """Stage `paths`, commit only those paths, optionally tag. Returns a status line."""
    if not config().get("auto_commit", True):
        return "auto_commit disabled - not committed"
    if not in_git_repo():
        return "not a git repository - not committed"
    paths = [p for p in paths if (ROOT / p).exists()]
    if not paths:
        return "nothing to commit"
    git("add", "-A", "--", *paths)
    if git("diff", "--cached", "--quiet", "--", *paths).returncode == 0:
        return "nothing to commit"
    trailer = config().get("commit_trailer", "")
    if trailer and is_agent_session():
        message = f"{message}\n\n{trailer}"
    r = git("commit", "-q", "-m", message, "--", *paths)
    if r.returncode != 0:
        raise StudioError(f"git commit failed: {r.stderr.strip() or r.stdout.strip()}")
    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    if tag:
        name, n = tag, 2
        while git("rev-parse", "-q", "--verify", f"refs/tags/{name}").returncode == 0:
            name, n = f"{tag}-{n}", n + 1
        git("tag", name)
        return f"committed {sha}, tagged {name}"
    return f"committed {sha}"


def actor() -> str:
    if is_agent_session():
        return "claude"
    name = git("config", "user.name").stdout.strip() if in_git_repo() else ""
    return name or os.environ.get("USERNAME") or os.environ.get("USER") or "human"


# --------------------------------------------------------------------------- routing
def compute_next(run_slow: bool = True) -> list[dict]:
    """Deterministic router: what should the studio do now?

    kinds: skill (run a stage skill), advance (stage complete), wait (human gate),
    blocked (environment problem), idle.
    """
    cfg = config()
    order = stage_ids()
    actions: list[dict] = []
    games = sorted(active_games(), key=lambda g: -order.index(g["stage"]) if g["stage"] in order else 0)
    for g in games:
        slug, stage = g["slug"], g["stage"]
        if stage == order[-1]:
            continue
        results = [(c, *eval_criterion(slug, c, run_slow)) for c in stage_def(stage)["exit"]]
        blocked = [d for c, ok, d in results if ok is None and d.startswith("BLOCKED")]
        unmet = [(c, d) for c, ok, d in results if ok is False]
        if unmet:
            seen: dict[str, list[str]] = {}
            for c, d in unmet:
                seen.setdefault(c["by"], []).append(d)
            for skill, details in seen.items():
                actions.append({"kind": "skill", "skill": skill, "args": slug, "game": slug,
                                "reason": "; ".join(details)})
        elif blocked:
            actions.append({"kind": "blocked", "game": slug, "reason": "; ".join(blocked)})
        else:
            gate = stage_def(stage).get("gate")
            if gate and gate_policy(gate) == "human" and not g.get("gates", {}).get(gate, {}).get("approved"):
                actions.append({"kind": "wait", "game": slug, "gate": gate,
                                "reason": f"{stage} complete; human gate '{gate}' pending",
                                "command": f"python scripts/studio.py approve {slug} {gate}"})
            else:
                actions.append({"kind": "advance", "game": slug, "args": slug,
                                "reason": f"{stage} exit criteria met",
                                "command": f"python scripts/studio.py advance {slug}"})

    # Studio-level work only when there is capacity for a new game.
    if len(games) < int(cfg.get("max_active_games", 1)):
        concepts = list_concepts()
        new = [c for c in concepts if c.get("status") == "new"]
        short = [c for c in concepts if c.get("status") == "shortlisted"]
        research = latest_research()
        max_age = int(cfg.get("research_max_age_days", 30))
        if new:
            actions.append({"kind": "skill", "skill": "evaluate-concepts", "args": "",
                            "reason": f"{len(new)} unscored concept(s)"})
        elif short:
            actions.append({"kind": "wait", "gate": "greenlight",
                            "reason": "shortlisted concepts await a human greenlight: "
                                      + ", ".join(f"{c['slug']} ({c.get('score') or '?'})" for c in short),
                            "command": "python scripts/studio.py greenlight <concept-slug>"})
        elif research is None or (dt.date.today() - research[0]).days > max_age:
            why = "no market research yet" if research is None else f"latest research is {(dt.date.today() - research[0]).days} days old"
            actions.append({"kind": "skill", "skill": "market-research", "args": "", "reason": why})
        else:
            actions.append({"kind": "skill", "skill": "ideate", "args": "",
                            "reason": f"no open concepts; research {research[1].parent.name} is fresh"})
    if not actions:
        actions.append({"kind": "idle", "reason": "studio at capacity and nothing actionable"})
    return actions


# --------------------------------------------------------------------------- commands
def cmd_status(a) -> int:
    cfg = config()
    research = latest_research()
    concepts = list_concepts()
    counts: dict[str, int] = {}
    for c in concepts:
        counts[c.get("status", "?")] = counts.get(c.get("status", "?"), 0) + 1
    games = list_games()
    print(f"{cfg.get('studio_name', 'Studio')} | {today()}")
    if research:
        print(f"Research : {research[1].parent.name} ({(dt.date.today() - research[0]).days}d old)")
    else:
        print("Research : none")
    print("Concepts : " + (", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "none"))
    act = [g for g in games if g.get("status") == "active"]
    print(f"Games    : {len(act)} active / max {cfg.get('max_active_games', 1)}, {len(games)} total")
    for g in games:
        gates = g.get("gates", {})
        gate = stage_def(g["stage"]).get("gate") if g.get("stage") in stage_ids() else None
        gate_txt = ""
        if gate:
            gate_txt = f" gate:{gate}={'approved' if gates.get(gate, {}).get('approved') else 'pending'}"
        if a.brief:
            print(f"  - {g['slug']:<22} {g.get('stage', '?'):<11} {g.get('status', '?')}{gate_txt}")
            continue
        results = check_stage(g["slug"], run_slow=False) if g.get("status") == "active" else []
        met = sum(1 for _, ok, _ in results if ok)
        print(f"  - {g['slug']:<22} {g.get('stage', '?'):<11} {g.get('status', '?')}{gate_txt}"
              f"  [{met}/{len(results)} criteria]")
    if a.brief:
        print("Run /studio for next actions.")
    return 0


def cmd_next(a) -> int:
    actions = compute_next(run_slow=not a.fast)
    if a.json:
        print(json.dumps(actions, indent=2))
        return 0
    print("Next actions:")
    for i, x in enumerate(actions, 1):
        if x["kind"] == "skill":
            what = f"/{x['skill']} {x.get('args', '')}".rstrip()
        elif x["kind"] in ("wait", "advance"):
            what = f"{x['kind'].upper()}: {x.get('command', '')}"
        else:
            what = x["kind"].upper()
        print(f"{i}. {what}  -- {x['reason']}")
    return 0


def cmd_check(a) -> int:
    st = load_state(a.slug)
    results = check_stage(a.slug, run_slow=not a.fast)
    print(f"{a.slug}: stage '{st['stage']}' ({st.get('status')})")
    for c, ok, d in results:
        mark = {True: "PASS", False: "FAIL", None: "SKIP"}[ok]
        print(f"  [{mark}] ({c['by']}) {d}")
    gate = stage_def(st["stage"]).get("gate")
    if gate:
        g = st.get("gates", {}).get(gate, {})
        print(f"  gate '{gate}' ({gate_policy(gate)}): {'approved' if g.get('approved') else 'pending'}")
    return 0 if all(ok is not False for _, ok, _ in results) else 1


def cmd_advance(a) -> int:
    slug = a.slug
    st = load_state(slug)
    if st.get("status") != "active":
        raise StudioError(f"{slug} is {st.get('status')}, not active")
    order = stage_ids()
    stage = st["stage"]
    if stage == order[-1]:
        print(f"{slug} is already in the final stage '{stage}'.")
        return 0
    results = check_stage(slug)
    bad = [(c, ok, d) for c, ok, d in results if ok is not True]
    if bad:
        print(f"NOT READY: {slug} cannot leave '{stage}':")
        for c, ok, d in bad:
            print(f"  - ({c['by']}) {d}")
        return 1
    gate = stage_def(stage).get("gate")
    if gate:
        approved = st.get("gates", {}).get(gate, {}).get("approved")
        if gate_policy(gate) == "human" and not approved:
            print(f"WAIT: '{stage}' is complete but human gate '{gate}' is pending.\n"
                  f"The user must run: python scripts/studio.py approve {slug} {gate}")
            return 3
        if not approved:
            st.setdefault("gates", {})[gate] = {"approved": True, "by": "auto-policy", "at": now()}
    nxt = order[order.index(stage) + 1]
    st["stage"] = nxt
    if nxt == order[-1]:
        st["status"] = "released"
    st.setdefault("history", []).append({"at": now(), "event": f"advance {stage} -> {nxt}", "by": actor()})
    save_state(slug, st)
    print(f"{slug}: {stage} -> {nxt}. " + commit([f"games/{slug}"], f"[{slug}] advance: {stage} -> {nxt}", tag=f"{slug}/{nxt}"))
    return 0


def cmd_approve(a) -> int:
    require_human("approve")
    st = load_state(a.slug)
    gate = a.gate or stage_def(st["stage"]).get("gate")
    current_gate = stage_def(st["stage"]).get("gate")
    if not gate or gate != current_gate:
        raise StudioError(f"stage '{st['stage']}' has gate '{current_gate}'; cannot approve '{gate}' now")
    st.setdefault("gates", {})[gate] = {"approved": True, "by": actor(), "at": now(), "note": a.note or ""}
    st.setdefault("history", []).append({"at": now(), "event": f"gate {gate} approved", "by": actor(), "note": a.note or ""})
    save_state(a.slug, st)
    print(f"Gate '{gate}' approved for {a.slug}. " + commit([f"games/{a.slug}"], f"[{a.slug}] gate approved: {gate}"))
    return cmd_advance(argparse.Namespace(slug=a.slug))


def cmd_greenlight(a) -> int:
    require_human("greenlight")
    slug = check_slug(a.concept)
    cpath = STUDIO / "concepts" / f"{slug}.md"
    if not cpath.exists():
        raise StudioError(f"no concept studio/concepts/{slug}.md")
    fm = read_frontmatter(cpath)
    if fm.get("status") != "shortlisted" and not a.force:
        raise StudioError(f"concept status is '{fm.get('status')}', expected 'shortlisted' (use --force to override)")
    cfg = config()
    if len(active_games()) >= int(cfg.get("max_active_games", 1)) and not a.force:
        raise StudioError("studio at max_active_games capacity (raise it in studio/config.json or use --force)")
    gdir = game_dir(slug)
    if (gdir / "state.json").exists():
        raise StudioError(f"games/{slug} already exists")
    for sub in ("design", "qa", "marketing", "release"):
        (gdir / sub).mkdir(parents=True, exist_ok=True)
        (gdir / sub / ".gitkeep").touch()
    shutil.copyfile(cpath, gdir / "concept.md")
    pkg_tail = re.sub(r"[^a-z0-9]", "", slug)
    if not pkg_tail[:1].isalpha():
        pkg_tail = "g" + pkg_tail
    st = {
        "slug": slug,
        "title": fm.get("title") or slug.replace("-", " ").title(),
        "stage": stage_ids()[0],
        "status": "active",
        "package": f"{cfg.get('package_prefix', 'com.example.studio')}.{pkg_tail}",
        "created": today(),
        "gates": {"greenlight": {"approved": True, "by": actor(), "at": now(), "note": a.note or ""}},
        "history": [{"at": now(), "event": "greenlit", "by": actor(), "note": a.note or ""}],
    }
    save_state(slug, st)
    set_frontmatter(cpath, {"status": "greenlit"})
    print(f"Greenlit '{st['title']}' -> games/{slug} (stage {st['stage']}). "
          + commit([f"games/{slug}", "studio/concepts"], f"[{slug}] greenlight", tag=f"{slug}/greenlight"))
    return 0


def cmd_kill(a) -> int:
    require_human("kill")
    st = load_state(a.slug)
    st["status"] = "killed"
    st.setdefault("history", []).append({"at": now(), "event": f"killed in {st['stage']}", "by": actor(), "note": a.reason})
    save_state(a.slug, st)
    print(f"Killed {a.slug}. " + commit([f"games/{a.slug}"], f"[{a.slug}] killed: {a.reason}"))
    return 0


def cmd_checkpoint(a) -> int:
    scope = a.scope
    if scope == "studio":
        paths = ["studio", ".claude/agent-memory"]
    elif scope == "infra":
        paths = [".claude", "scripts", "docs", "tests", "CLAUDE.md", "DECISIONS.md", "README.md", ".gitignore"]
    else:
        paths = [f"games/{check_slug(scope)}", ".claude/agent-memory"]
    print(commit(paths, f"[{scope}] {a.message}"))
    return 0


def cmd_scaffold(a) -> int:
    st = load_state(a.slug)
    dest = game_dir(a.slug) / "project"
    if (dest / "project.godot").exists():
        raise StudioError(f"games/{a.slug}/project already contains a Godot project")
    if not TEMPLATE_DIR.exists():
        raise StudioError(f"template missing: {TEMPLATE_DIR}")
    shutil.copytree(TEMPLATE_DIR, dest, dirs_exist_ok=True)
    subs = {"{{TITLE}}": st["title"], "{{PACKAGE}}": st["package"], "{{SLUG}}": a.slug}
    for p in dest.rglob("*"):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            text = p.read_text(encoding="utf-8")
            for k, v in subs.items():
                text = text.replace(k, v)
            p.write_text(text, encoding="utf-8")
    print(f"Scaffolded Godot project at games/{a.slug}/project (package {st['package']}).")
    return 0


def cmd_test(a) -> int:
    code, out = run_tests(a.slug)
    lines = out.strip().splitlines()
    print("\n".join(lines if a.verbose else lines[-40:]))
    if code == -1:
        return 2
    print("TESTS PASSED" if code == 0 else f"TESTS FAILED (exit {code})")
    return 0 if code == 0 else 1


def cmd_build(a) -> int:
    st = load_state(a.slug)
    proj = game_dir(a.slug) / "project"
    out_dir = game_dir(a.slug) / "build"
    out_dir.mkdir(exist_ok=True)
    if a.release:
        require_human("build --release (signing uses the release keystore)")
        missing = [v for v in ("GODOT_ANDROID_KEYSTORE_RELEASE_PATH", "GODOT_ANDROID_KEYSTORE_RELEASE_USER",
                               "GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD") if not os.environ.get(v)]
        if missing:
            print("BLOCKED: release keystore env vars not set: " + ", ".join(missing))
            return 2
    kind = "release" if a.release else "debug"
    ext = "aab" if a.aab else "apk"
    out = out_dir / f"{a.slug}-{kind}.{ext}"
    code, log = godot_run(["--headless", "--path", str(proj), f"--export-{kind}", a.preset, str(out)], timeout=1800)
    print("\n".join(log.strip().splitlines()[-30:]))
    if code == -1:
        return 2
    if code != 0 or not out.exists():
        print(f"BUILD FAILED (exit {code})")
        return 1
    print(f"BUILD OK: {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB) for {st['package']}")
    return 0


def cmd_doctor(a) -> int:
    rows: list[tuple[str, str, str]] = []

    def probe(cmd: list[str]) -> str | None:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[0] if r.returncode == 0 or r.stderr else None
        except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
            return None

    rows.append(("python", "OK", sys.version.split()[0]))
    g = probe(["git", "--version"])
    rows.append(("git", "OK" if g else "MISSING", g or "install git"))
    rows.append(("git repo", "OK" if in_git_repo() else "WARN", "" if in_git_repo() else "run: git init"))
    j = probe(["java", "-version"])
    jm = re.search(r'"(\d+)', j or "")
    rows.append(("java (JDK)", "OK" if j else "MISSING", (j or "install JDK 17+") +
                 ("" if not jm or jm.group(1) == "17" else "  (Godot docs recommend JDK 17; newer usually works)")))
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        for c in (Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk", Path.home() / "Library/Android/sdk",
                  Path.home() / "Android" / "Sdk"):
            if c.exists():
                sdk = str(c)
                break
    rows.append(("android sdk", "OK" if sdk else "MISSING", sdk or "install Android Studio / cmdline-tools"))
    godot = find_godot()
    ver = probe([godot, "--version"]) if godot else None
    rows.append(("godot", "OK" if ver else "MISSING", f"{ver} ({godot})" if ver else
                 "download Godot 4 and set GODOT_BIN or studio/config.json godot_bin"))
    if ver:
        vm = re.match(r"(\d+\.\d+(?:\.\d+)?)\.(\w+)", ver)
        tdirs = [Path(os.environ.get("APPDATA", "")) / "Godot" / "export_templates",
                 Path.home() / ".local/share/godot/export_templates",
                 Path.home() / "Library/Application Support/Godot/export_templates"]
        want = f"{vm.group(1)}.{vm.group(2)}" if vm else "?"
        has = any((d / want).exists() for d in tdirs)
        rows.append(("export templates", "OK" if has else "MISSING", want if has else
                     f"install {want} templates (Godot editor > Manage Export Templates)"))
    claude = shutil.which("claude")
    rows.append(("claude CLI", "OK" if claude else "WARN", claude or "needed only for headless autopilot (scripts/autopilot.*)"))
    ks = os.environ.get("GODOT_ANDROID_KEYSTORE_RELEASE_PATH")
    rows.append(("release keystore", "OK" if ks else "INFO", "env set" if ks else "not set (needed only for human release builds)"))
    for name, status, detail in rows:
        print(f"[{status:<7}] {name:<17} {detail}")
    return 1 if any(s == "MISSING" for _, s, _ in rows) else 0


def cmd_validate(a) -> int:
    problems: list[str] = []
    try:
        stages = stage_ids()
        config()
    except StudioError as e:
        print(f"INVALID: {e}")
        return 1
    skills_dir = ROOT / ".claude" / "skills"
    agents_dir = ROOT / ".claude" / "agents"
    skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    agents = set()
    for p in agents_dir.glob("*.md"):
        fm = read_frontmatter(p)
        if fm.get("name") != p.stem:
            problems.append(f"agent {p.name}: frontmatter name '{fm.get('name')}' != filename")
        if not fm.get("description"):
            problems.append(f"agent {p.name}: missing description")
        agents.add(p.stem)
    for p in skills_dir.glob("*/SKILL.md"):
        fm = read_frontmatter(p)
        if fm.get("name", p.parent.name) != p.parent.name:
            problems.append(f"skill {p.parent.name}: name '{fm.get('name')}' != directory")
        if not fm.get("description"):
            problems.append(f"skill {p.parent.name}: missing description")
        body = p.read_text(encoding="utf-8")
        for ref in set(re.findall(r"`([a-z0-9-]+)` (?:sub)?agents?\b", body)):
            if ref not in agents:
                problems.append(f"skill {p.parent.name}: references unknown agent '{ref}'")
        for ref in set(re.findall(r"\]\(([^)#]+)\)", body)):
            if not ref.startswith("http") and not (p.parent / ref).exists() and not (ROOT / ref).exists():
                problems.append(f"skill {p.parent.name}: broken link '{ref}'")
    for p in agents_dir.glob("*.md"):
        body = p.read_text(encoding="utf-8")
        m = re.search(r"^skills:\s*\n((?:\s+-\s*\S+\n?)+)", body, re.M)
        for ref in re.findall(r"-\s*(\S+)", m.group(1)) if m else []:
            if ref not in skills:
                problems.append(f"agent {p.stem}: preloads unknown skill '{ref}'")
    for s in pipeline():
        for c in s["exit"]:
            if c.get("by") not in skills:
                problems.append(f"pipeline stage {s['id']}: criterion by unknown skill '{c.get('by')}'")
    settings = ROOT / ".claude" / "settings.json"
    if settings.exists():
        try:
            text = settings.read_text(encoding="utf-8")
            json.loads(text)
            for ref in re.findall(r"/(\.claude/hooks/[\w.-]+|scripts/[\w.-]+)", text):
                if not (ROOT / ref).exists():
                    problems.append(f"settings.json: hook script missing: {ref}")
        except json.JSONDecodeError as e:
            problems.append(f"settings.json invalid: {e}")
    for c in list_concepts():
        miss = [k for k in ("slug", "title", "status") if not c.get(k)]
        if miss:
            problems.append(f"concept {c['_path']}: missing {', '.join(miss)}")
        elif c["status"] not in CONCEPT_STATUSES:
            problems.append(f"concept {c['_path']}: bad status '{c['status']}'")
        elif Path(c["_path"]).stem != c["slug"]:
            problems.append(f"concept {c['_path']}: slug '{c['slug']}' != filename")
    for g in list_games():
        if g.get("status") == "corrupt":
            problems.append(f"games/{g['slug']}/state.json is not valid JSON")
            continue
        for k in ("slug", "title", "stage", "status", "package"):
            if k not in g:
                problems.append(f"games/{g.get('slug')}/state.json missing '{k}'")
        if g.get("stage") not in stages:
            problems.append(f"games/{g.get('slug')}: unknown stage '{g.get('stage')}'")
    if problems:
        print(f"INVALID ({len(problems)} problem(s)):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {len(agents)} agents, {len(skills)} skills, {len(stages)} stages, "
          f"{len(list_concepts())} concepts, {len(list_games())} games")
    return 0


# --------------------------------------------------------------------------- cli
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="portfolio overview")
    s.add_argument("--brief", action="store_true", help="short form, no criteria checks")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("next", help="deterministic list of next actions")
    s.add_argument("--json", action="store_true")
    s.add_argument("--fast", action="store_true", help="skip running Godot tests")
    s.set_defaults(fn=cmd_next)

    s = sub.add_parser("check", help="evaluate exit criteria of a game's current stage")
    s.add_argument("slug")
    s.add_argument("--fast", action="store_true", help="skip running Godot tests")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("advance", help="move a game to the next stage if criteria + gate allow")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_advance)

    s = sub.add_parser("greenlight", help="[HUMAN] turn a shortlisted concept into a game")
    s.add_argument("concept")
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_greenlight)

    s = sub.add_parser("approve", help="[HUMAN] approve the current stage gate and advance")
    s.add_argument("slug")
    s.add_argument("gate", nargs="?")
    s.add_argument("--note", default="")
    s.set_defaults(fn=cmd_approve)

    s = sub.add_parser("kill", help="[HUMAN] stop a game")
    s.add_argument("slug")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_kill)

    s = sub.add_parser("checkpoint", help="git commit a scope: <slug> | studio | infra")
    s.add_argument("scope")
    s.add_argument("-m", "--message", required=True)
    s.set_defaults(fn=cmd_checkpoint)

    s = sub.add_parser("scaffold", help="create the Godot project for a game from the mobile template")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_scaffold)

    s = sub.add_parser("test", help="run the game's headless Godot tests")
    s.add_argument("slug")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=cmd_test)

    s = sub.add_parser("build", help="export an Android build (debug APK by default)")
    s.add_argument("slug")
    s.add_argument("--release", action="store_true", help="[HUMAN] signed release build")
    s.add_argument("--aab", action="store_true", help="export .aab (requires Gradle build in preset)")
    s.add_argument("--preset", default="Android")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("doctor", help="check the toolchain")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("validate", help="check studio integrity (agents, skills, pipeline, data)")
    s.set_defaults(fn=cmd_validate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except StudioError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
