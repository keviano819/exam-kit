"""Run package self-checks in a temporary directory; no network or installation."""

import copy
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from build_workbench import SKILL_ROOT, build, read_course, validate_course


def must_reject(payload):
    try:
        validate_course(payload)
    except (ValueError, TypeError):
        return
    raise AssertionError("invalid course accepted")


def verify():
    skill_text = (SKILL_ROOT / "SKILL.md").read_text()
    assert SKILL_ROOT.name == "exam-kit"
    assert re.search(r"^name: exam-kit$", skill_text, re.MULTILINE)
    assert "$exam-kit" in (SKILL_ROOT / "agents" / "openai.yaml").read_text()
    sample = read_course(SKILL_ROOT / "examples" / "course.json")
    for mutation in ["missing-lesson", "duplicate-question", "bad-answer", "missing-reference", "empty-units", "reserved-id"]:
        damaged = copy.deepcopy(sample)
        if mutation == "missing-lesson":
            del damaged["units"][0]["lesson"]
        elif mutation == "duplicate-question":
            damaged["units"][1]["questions"][0]["id"] = damaged["units"][0]["questions"][0]["id"]
        elif mutation == "bad-answer":
            damaged["units"][0]["questions"][0]["answer"] = 99
        elif mutation == "missing-reference":
            damaged["units"][0]["questions"][0]["sectionIds"] = ["unknown"]
        elif mutation == "empty-units":
            damaged["units"] = []
        else:
            damaged["units"][0]["questions"][0]["id"] = "constructor"
        must_reject(damaged)
    with tempfile.TemporaryDirectory(prefix="exam-kit-verify-") as temporary:
        root = Path(temporary)
        local = build(sample, "local-html", root / "local")
        online = build(sample, "vercel", root / "online")
        local_html = (local / "复习工作台.html").read_text()
        publish = online / "vercel-deploy"
        assert 'src="data.js"' not in local_html
        assert 'rel="manifest"' not in local_html
        assert "serviceWorker.register" not in local_html
        assert "window.EXAM_KIT_DATA" in local_html
        assert "window.EXAM_REVIEW_DATA" not in local_html
        assert not re.search(r"__[A-Z_]+__", local_html)
        for forbidden in ["ENGE", "RESEARCH_METHODS_DATA", "Research methods", "Population variance", "/Users/", "sourceFiles"]:
            assert forbidden not in local_html, forbidden
        expected = {"index.html", "data.js", "manifest.json", "sw.js"}
        assert {entry.name for entry in publish.iterdir()} == expected
        with zipfile.ZipFile(online / "复习工作台-vercel.zip") as archive:
            assert set(archive.namelist()) == expected
        assert "从注册" in (online / "Vercel上传指南.md").read_text() or "注册或登录" in (online / "Vercel上传指南.md").read_text()
        try:
            build(sample, "local-html", local)
        except ValueError:
            pass
        else:
            raise AssertionError("existing output overwritten")
        changed = copy.deepcopy(sample)
        changed["units"][0]["lesson"]["sections"][0]["body"] += "\n\n补充说明。"
        update = build(changed, "vercel", root / "update")
        assert (publish / "sw.js").read_text() != (update / "vercel-deploy" / "sw.js").read_text()
        hostile = copy.deepcopy(sample)
        hostile["course"]["title"] = 'Quotes " & <title> __PAGE_TITLE__'
        hostile["units"][0]["lesson"]["sections"][0]["body"] += "</script><script>throw Error('injected')</script><!-- & >"
        hostile_local = build(hostile, "local-html", root / "hostile-local")
        hostile_online = build(hostile, "vercel", root / "hostile-online")
        hostile_html = (hostile_local / "复习工作台.html").read_text()
        assert len(re.findall(r"<script>", hostile_html)) == 2
        assert "\\u003c/script\\u003e" in hostile_html
        assert json.loads((hostile_online / "vercel-deploy" / "manifest.json").read_text())["name"] == hostile["course"]["title"]
        print("PASS: validation rejects 6 invalid inputs; both modes; ZIP root; overwrite guard; cache digest; safe JSON embedding")
        if shutil.which("node"):
            scripts = re.findall(r"<script>([\s\S]*?)</script>", local_html)
            for document in [local_html, hostile_html, (publish / "index.html").read_text()]:
                for script in re.findall(r"<script>([\s\S]*?)</script>", document):
                    subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(0,'utf8'));"], input=script, text=True, check=True)
            for resource in ["data.js", "sw.js"]:
                subprocess.run(["node", "--check", str(publish / resource)], check=True)
            harness = r'''
const vm = require("node:vm");
const assert = require("node:assert/strict");
const nodes = new Map();
function element(id) {
  if (!nodes.has(id)) nodes.set(id, {innerHTML:"", textContent:"", value:"", classList:{toggle(){}}, addEventListener(){}, querySelector(){return element("control");}, querySelectorAll(){return [];}, scrollIntoView(){}});
  return nodes.get(id);
}
const storage = new Map();
storage.set("exam-review-study-demo-v1", JSON.stringify({answers:{"claims-choice":{answer:1,correct:true,confidence:"不确定",history:[]}},drafts:{"scope-written":"旧版草稿"}}));
const context = {window:{scrollTo(){}}, document:{getElementById:element, querySelector:element, querySelectorAll(){return [];}}, localStorage:{getItem(key){return storage.get(key) || null;}, setItem(key,value){storage.set(key,value);}}, console, navigator:{}, location:{protocol:"file:"}};
vm.createContext(context);
for (const script of JSON.parse(require("fs").readFileSync(0,"utf8"))) vm.runInContext(script,context);
vm.runInContext(`
if (appState.answers["claims-choice"]?.answer !== 1 || appState.drafts["scope-written"] !== "旧版草稿") throw Error("rename lost legacy records");
if (appState.selectedUnit !== "claims") throw Error("hardcoded first unit");
if (renderLesson(unitById("u5")).includes("Population variance")) throw Error("course-specific formula");
const choice = unitById("claims").questions[0];
startUnit("claims");
submitAnswer(choice, choice.answer);
setConfidence(choice, "不确定");
if (!needsReview(appState.answers[choice.id])) throw Error("uncertain correct answer missing from review");
retryQuestion(choice.id);
if (!appState.answers[choice.id]) throw Error("retry destroyed history");
submitAnswer(choice, choice.answer);
setConfidence(choice, "会");
if (needsReview(appState.answers[choice.id])) throw Error("review not resolved");
if (appState.answers[choice.id].history.length !== 1) throw Error("retry history lost");
startUnit("u5");
const written = unitById("u5").questions[0];
persistAnswer(written, {writtenAnswer:"只观察了本次五名志愿者，结论应限于本次参与者的评价。", revealed:true, correct:null});
if (appState.completedUnits.includes("u5")) throw Error("ungraded case completed");
persistAnswer(written, {...appState.answers[written.id], criteria:[0,1], score:2, correct:true, grading:"self"});
if (appState.completedUnits.length !== 2) throw Error("completion failed");
const restored = loadState();
if (!restored.answers[choice.id] || !restored.answers[written.id]) throw Error("persistence failed");
renderHome();
if (!document.getElementById("home-view").innerHTML.includes("本轮排查已完成")) throw Error("complete home failed");
localStorage.setItem = () => { throw Error("blocked storage"); };
saveState();
if (!document.querySelector("footer").textContent.includes("导出")) throw Error("missing save warning");
`, context);
console.log("PASS: renamed data entry; legacy record compatibility; script syntax; generic IDs; choice/uncertainty/retry/history; written self-assessment; persistence; storage failure");
'''
            subprocess.run(["node", "-e", harness], input=json.dumps(scripts), text=True, check=True)
        else:
            print("SKIP: JavaScript syntax/state checks (Node.js unavailable); browser validation still required")


if __name__ == "__main__":
    verify()
