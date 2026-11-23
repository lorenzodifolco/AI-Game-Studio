"""Tests for scripts/studio.py and .claude/hooks (stdlib unittest).

Run: python -m unittest discover -s tests
Each test builds a throwaway studio in a temp git repo (STUDIO_ROOT) and uses a
fake Godot binary, so no engine is needed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STUDIO_PY = REPO / "scripts" / "studio.py"
HOOKS = REPO / ".claude" / "hooks"
ALL_HEADINGS = json.loads((REPO / "studio" / "pipeline.json").read_text(encoding="utf-8"))["stages"][0]["exit"][0]["headings"]


def run(args, root, agent=False, extra_env=None, stdin=None, script=STUDIO_PY):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["STUDIO_ROOT"] = str(root)
    if agent:
        env["CLAUDECODE"] = "1"
    env.update(extra_env or {})
    r = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                       env=env, input=stdin, cwd=root, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


class StudioSandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="studio-test-"))
        for d in ("studio", "scripts", ".claude"):
            shutil.copytree(REPO / d, self.root / d, ignore=shutil.ignore_patterns("logs", "agent-memory*"))
        for d in ("studio/research", "studio/concepts", "games"):
            p = self.root / d
            shutil.rmtree(p, ignore_errors=True)
            p.mkdir(parents=True)
        for cmd in (["init", "-q"], ["config", "user.name", "Test Owner"], ["config", "user.email", "t@example.com"],
                    ["add", "-A"], ["commit", "-q", "-m", "init"]):
            subprocess.run(["git", *cmd], cwd=self.root, capture_output=True, check=True)
        self.fake_godot = self._make_fake_godot()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _make_fake_godot(self) -> Path:
        """Fake godot: prints $FAKE_GODOT_OUT and exits with $FAKE_GODOT_RC."""
        py = self.root / "fake_godot.py"
        py.write_text("import os,sys\nprint(os.environ.get('FAKE_GODOT_OUT','RESULT: 1 passed, 0 failed'))\n"
                      "sys.exit(int(os.environ.get('FAKE_GODOT_RC','0')))\n", encoding="utf-8")
        if os.name == "nt":
            exe = self.root / "fake_godot.cmd"
            exe.write_text(f'@"{sys.executable}" "{py}" %*\r\n', encoding="utf-8")
        else:
            exe = self.root / "fake_godot"
            exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{py}" "$@"\n', encoding="utf-8")
            exe.chmod(0o755)
        return exe

    # helpers
    def studio(self, *args, agent=False, **env):
        env.setdefault("GODOT_BIN", str(self.fake_godot))
        return run(list(args), self.root, agent=agent, extra_env=env)

    def next_kinds(self):
        code, out = self.studio("next", "--json")
        self.assertEqual(code, 0, out)
        return [(a["kind"], a.get("skill") or a.get("gate")) for a in json.loads(out)]

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def add_concept(self, slug, status="new", score=""):
        self.write(f"studio/concepts/{slug}.md",
                   f"---\nslug: {slug}\ntitle: {slug.title()}\nstatus: {status}\nscore: {score}\n---\n# {slug}\n")

    def greenlit_game(self, slug="orbit-pop"):
        self.write("studio/research/2000-01-01-old/report.md", "# old\n")
        self.add_concept(slug, "shortlisted", "7.5")
        code, out = self.studio("greenlight", slug)
        self.assertEqual(code, 0, out)
        return slug

    def git_log(self):
        return subprocess.run(["git", "log", "--format=%s%n%b"], cwd=self.root, capture_output=True, text=True).stdout

    def git_tags(self):
        return subprocess.run(["git", "tag"], cwd=self.root, capture_output=True, text=True).stdout.split()


class TestRouting(StudioSandbox):
    def test_studio_level_routing(self):
        self.assertEqual(self.next_kinds(), [("skill", "market-research")])
        today = __import__("datetime").date.today().isoformat()
        self.write(f"studio/research/{today}-broad/report.md", "# r\n")
        self.assertEqual(self.next_kinds(), [("skill", "ideate")])
        self.add_concept("alpha")
        self.assertEqual(self.next_kinds(), [("skill", "evaluate-concepts")])
        self.add_concept("alpha", "shortlisted", "7.4")
        self.assertEqual(self.next_kinds(), [("wait", "greenlight")])

    def test_stale_research_triggers_research(self):
        self.write("studio/research/2000-01-01-broad/report.md", "# r\n")
        self.assertEqual(self.next_kinds(), [("skill", "market-research")])

    def test_capacity_blocks_studio_level_work(self):
        slug = self.greenlit_game()
        kinds = self.next_kinds()
        self.assertEqual(kinds, [("skill", "design-game")])
        self.assertNotIn("market-research", str(kinds))
        self.assertIn(slug, self.studio("status")[1])


class TestGatesAndStages(StudioSandbox):
    def test_human_only_commands_refused_for_agent(self):
        self.add_concept("beta", "shortlisted", "8")
        for args in (["greenlight", "beta"], ["approve", "beta"], ["kill", "beta", "--reason", "x"]):
            code, out = self.studio(*args, agent=True)
            self.assertEqual(code, 1, out)
            self.assertIn("human-only", out)
        self.assertFalse((self.root / "games" / "beta").exists())

    def test_greenlight_requires_shortlisted(self):
        self.add_concept("gamma", "new")
        code, out = self.studio("greenlight", "gamma")
        self.assertEqual(code, 1)
        self.assertIn("expected 'shortlisted'", out)

    def test_full_pipeline_walk(self):
        slug = self.greenlit_game()
        st = json.loads((self.root / f"games/{slug}/state.json").read_text())
        self.assertEqual((st["stage"], st["status"]), ("design", "active"))
        self.assertTrue(st["package"].endswith(".orbitpop"))
        self.assertIn(f"{slug}/greenlight", self.git_tags())
        self.assertIn("status: greenlit", (self.root / f"studio/concepts/{slug}.md").read_text())

        # design: blocked until GDD has all sections
        code, out = self.studio("advance", slug, agent=True)
        self.assertEqual(code, 1, out)
        self.assertIn("NOT READY", out)
        self.write(f"games/{slug}/design/gdd.md", "# GDD\n" + "".join(f"## {h}\ntext\n" for h in ALL_HEADINGS[:-1]))
        self.write(f"games/{slug}/design/backlog.md", "## Prototype\n- [ ] P1-01 a\n## Production\n- [ ] P1-10 b\n")
        code, out = self.studio("check", slug)
        self.assertIn("missing sections: Prototype Hypothesis", out)
        with open(self.root / f"games/{slug}/design/gdd.md", "a", encoding="utf-8") as f:
            f.write("## 14. Prototype Hypothesis\nWe believe...\n")
        code, out = self.studio("advance", slug, agent=True)
        self.assertEqual(code, 0, out)
        self.assertIn(f"{slug}/prototype", self.git_tags())
        self.assertIn("Co-Authored-By", self.git_log())  # agent-made commit carries trailer

        # prototype: scaffold, tests via fake godot, report, then human gate
        code, out = self.studio("scaffold", slug, agent=True)
        self.assertEqual(code, 0, out)
        pg = (self.root / f"games/{slug}/project/project.godot").read_text()
        self.assertIn('config/name="Orbit-Pop"', pg)
        self.assertNotIn("{{", (self.root / f"games/{slug}/project/export_presets.cfg").read_text())
        self.assertEqual([k for k, _ in self.next_kinds()], ["skill"])  # report missing
        self.write(f"games/{slug}/qa/prototype-report.md", "# R\n\nRecommendation: **GO**\n")
        self.assertEqual(self.next_kinds(), [("wait", "prototype")])
        code, out = self.studio("advance", slug, agent=True)
        self.assertEqual(code, 3, out)
        self.assertIn("approve orbit-pop prototype", out)
        code, out = self.studio("approve", slug, "release")
        self.assertEqual(code, 1, out)  # only the current stage's gate can be approved
        code, out = self.studio("approve", slug, "--note", "fun!")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.root / f"games/{slug}/state.json").read_text())["stage"], "production")

        # production: checklist must be complete
        self.assertEqual(self.next_kinds(), [("skill", "develop")])
        self.write(f"games/{slug}/design/backlog.md", "## Prototype\n- [x] P1-01 a\n## Production\n- [x] P1-10 b\n")
        self.assertEqual(self.next_kinds(), [("advance", None)])
        self.assertEqual(self.studio("advance", slug, agent=True)[0], 0)

        # qa: verdict line required
        self.write(f"games/{slug}/qa/qa-report.md", "# QA\nVerdict: FAIL\n")
        self.assertEqual(self.next_kinds(), [("skill", "qa")])
        self.write(f"games/{slug}/qa/qa-report.md", "# QA\nVerdict: PASS\n")
        self.assertEqual(self.studio("advance", slug, agent=True)[0], 0)

        # launch: marketing + release run as two independent skills
        self.assertEqual(sorted(s for _, s in self.next_kinds()), ["marketing-kit", "release-prep"])
        self.write(f"games/{slug}/marketing/store-listing.md",
                   "".join(f"## {h}\nx\n" for h in ["Title", "Short Description", "Full Description",
                                                     "Keywords", "Screenshots", "Feature Graphic"]))
        self.write(f"games/{slug}/marketing/launch-plan.md", "plan\n")
        self.write(f"games/{slug}/release/release-checklist.md", "- [x] a\n  - evidence: x\n- [x] b\n")
        self.assertEqual(self.studio("advance", slug, agent=True)[0], 3)  # release gate always human
        code, out = self.studio("approve", slug, "release")
        self.assertEqual(code, 0, out)
        st = json.loads((self.root / f"games/{slug}/state.json").read_text())
        self.assertEqual((st["stage"], st["status"]), ("released", "released"))

    def test_auto_gate_policy(self):
        cfg = json.loads((self.root / "studio/config.json").read_text())
        cfg["gates"]["prototype"] = "auto"
        cfg["gates"]["release"] = "auto"  # must be ignored: release is always human
        (self.root / "studio/config.json").write_text(json.dumps(cfg))
        slug = self.greenlit_game()
        self.write(f"games/{slug}/design/gdd.md", "".join(f"## {h}\nx\n" for h in ALL_HEADINGS))
        self.write(f"games/{slug}/design/backlog.md", "- [ ] a\n")
        self.studio("advance", slug, agent=True)
        self.studio("scaffold", slug, agent=True)
        self.write(f"games/{slug}/qa/prototype-report.md", "Recommendation: GO\n")
        self.assertEqual(self.studio("advance", slug, agent=True)[0], 0)
        self.assertEqual(json.loads((self.root / f"games/{slug}/state.json").read_text())["stage"], "production")

    def test_kill(self):
        slug = self.greenlit_game()
        code, out = self.studio("kill", slug, "--reason", "not fun")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.root / f"games/{slug}/state.json").read_text())["status"], "killed")
        self.assertEqual(self.next_kinds()[0][0], "skill")  # capacity freed -> studio-level work


class TestGodotWrappers(StudioSandbox):
    def setUp(self):
        super().setUp()
        self.slug = self.greenlit_game()
        self.studio("scaffold", self.slug)
        (self.root / f"games/{self.slug}/project/.godot").mkdir()

    def test_tests_pass(self):
        code, out = self.studio("test", self.slug)
        self.assertEqual(code, 0, out)
        self.assertIn("TESTS PASSED", out)

    def test_script_error_fails_even_with_exit_zero(self):
        code, out = self.studio("test", self.slug, FAKE_GODOT_OUT="SCRIPT ERROR: Invalid call")
        self.assertEqual(code, 1, out)

    def test_failing_exit_code(self):
        code, out = self.studio("test", self.slug, FAKE_GODOT_RC="1")
        self.assertEqual(code, 1, out)

    def test_missing_godot_is_blocked(self):
        code, out = self.studio("test", self.slug, GODOT_BIN=str(self.root / "nope.exe"), PATH="")
        self.assertEqual(code, 2, out)
        self.assertIn("BLOCKED", out)

    def test_release_build_is_human_only(self):
        code, out = self.studio("build", self.slug, "--release", agent=True)
        self.assertEqual(code, 1, out)
        self.assertIn("human-only", out)


class TestCheckpointAndValidate(StudioSandbox):
    def test_checkpoint_scopes(self):
        self.write("studio/research/2026-01-01-x/report.md", "r\n")
        self.write("scripts/unrelated.txt", "x\n")
        code, out = self.studio("checkpoint", "studio", "-m", "research: x", agent=True)
        self.assertIn("committed", out)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.root, capture_output=True, text=True).stdout
        self.assertIn("scripts/unrelated.txt", status)  # outside scope stays uncommitted
        self.assertIn("nothing to commit", self.studio("checkpoint", "studio", "-m", "again")[1])

    def test_validate_real_repo(self):
        code, out = run(["validate"], REPO)
        self.assertEqual(code, 0, out)

    def test_validate_detects_problems(self):
        self.add_concept("bad", status="weird")
        p = self.root / ".claude/agents/market-analyst.md"
        p.write_text(p.read_text(encoding="utf-8").replace("name: market-analyst", "name: wrong"), encoding="utf-8")
        code, out = self.studio("validate")
        self.assertEqual(code, 1)
        self.assertIn("bad status", out)
        self.assertIn("!= filename", out)


class TestHooks(unittest.TestCase):
    def bash(self, command):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        return run([], REPO, stdin=payload, script=HOOKS / "guard_bash.py")

    def edit(self, path):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})
        code, out = run([], REPO, stdin=payload, script=HOOKS / "protect_files.py",
                        extra_env={"CLAUDE_PROJECT_DIR": str(REPO)})
        self.assertEqual(code, 0)
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"

    def test_bash_blocked(self):
        for cmd in ["python scripts/studio.py approve x prototype",
                    "python ./scripts/studio.py greenlight foo",
                    "cd x && python scripts/studio.py kill a --reason b",
                    "python scripts/studio.py build x --release --aab",
                    "git push --force origin main", "git push -f", "git reset --hard HEAD~1",
                    "git clean -fdx", "git checkout -- .", "rm -rf games/orbit-pop", "rm -rf .git",
                    "rm -rf studio && echo done", "rm -r -f build games;",
                    "rm -rf /", "cat studio/secrets/release.keystore", "type .env",
                    "fastlane supply --aab x.aab", "echo $GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD"]:
            code, out = self.bash(cmd)
            self.assertEqual(code, 2, f"should block: {cmd}")
            self.assertIn("BLOCKED", out)

    def test_bash_allowed(self):
        for cmd in ["python scripts/studio.py status", "python scripts/studio.py next --json",
                    "python scripts/studio.py build orbit-pop", "git push origin main",
                    "git push --follow-tags", "git commit -m 'approve the design'",
                    "rm -rf games/orbit-pop/project/.godot", "rm build/tmp.txt",
                    "python scripts/studio.py checkpoint orbit-pop -m \"qa: fix kill-switch\"",
                    "ls studio/concepts", "grep -l '^status: new' studio/concepts/*.md",
                    "rm -rf tests/__pycache__ && git status --short | sed 's/^?? //'"]:
            code, out = self.bash(cmd)
            self.assertEqual(code, 0, f"should allow: {cmd} -> {out}")

    def test_file_guard(self):
        self.assertEqual(self.edit(str(REPO / "games" / "x" / "state.json")), "deny")
        self.assertEqual(self.edit("games\\x\\state.json"), "deny")
        self.assertEqual(self.edit(str(REPO / "studio" / "secrets" / "a.txt")), "deny")
        self.assertEqual(self.edit(str(REPO / "release.keystore")), "deny")
        self.assertEqual(self.edit(str(REPO / ".env")), "deny")
        self.assertEqual(self.edit(str(REPO / ".claude" / "settings.json")), "ask")
        self.assertEqual(self.edit(str(REPO / ".claude" / "hooks" / "guard_bash.py")), "ask")
        self.assertEqual(self.edit(str(REPO / "games" / "x" / "design" / "gdd.md")), "allow")
        self.assertEqual(self.edit(str(REPO / "studio" / "concepts" / "a.md")), "allow")


if __name__ == "__main__":
    unittest.main()
