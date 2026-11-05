"""Build the bundled workbench from JSON without executing course code."""

import argparse
import copy
import hashlib
import html
import json
import re
import sys
import zipfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "workbench"
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\Z")
RESERVED = {"__proto__", "constructor", "prototype"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, path):
    require(isinstance(value, str) and bool(value.strip()), f"{path}: expected nonempty text")
    return value


def identifier(value, path):
    text(value, path)
    require(bool(IDENTIFIER.fullmatch(value)) and value not in RESERVED, f"{path}: invalid stable ID")
    return value


def texts(value, path, minimum=1):
    require(isinstance(value, list) and len(value) >= minimum, f"{path}: expected text list (min {minimum})")
    for position, item in enumerate(value):
        text(item, f"{path}[{position}]")


def fields(value, names, path):
    require(isinstance(value, dict), f"{path}: expected object")
    for name in names:
        text(value.get(name), f"{path}.{name}")


def validate_course(payload):
    require(isinstance(payload, dict), "course JSON must be an object")
    require(type(payload.get("schemaVersion")) is int and payload["schemaVersion"] == 1, "schemaVersion must be 1")
    fields(payload, ["version"], "root")
    course = payload.get("course")
    fields(course, ["id", "title", "scope", "mode"], "course")
    identifier(course["id"], "course.id")
    for name in ["shortTitle", "brand", "mark", "subtitle"]:
        if name in course:
            text(course[name], f"course.{name}")
    if "exclusions" in course:
        texts(course["exclusions"], "course.exclusions", 0)
    if "errorReasons" in course:
        texts(course["errorReasons"], "course.errorReasons")
    units = payload.get("units")
    require(isinstance(units, list) and units, "units must not be empty")
    unit_ids, question_ids, section_ids = set(), set(), set()
    for unit in units:
        fields(unit, ["id", "title", "summary", "source"], "unit")
        unit_id = identifier(unit["id"], "unit.id")
        require(unit_id not in unit_ids, f"duplicate unit ID: {unit_id}")
        unit_ids.add(unit_id)
        unit.setdefault("zhTitle", unit["title"])
        unit.setdefault("week", f"单元 {len(unit_ids)}")
        unit.setdefault("difficulty", "进阶")
        fields(unit, ["zhTitle", "week", "difficulty"], unit_id)
        texts(unit.get("objectives"), f"{unit_id}.objectives")
        require(isinstance(unit.get("terms"), list), f"{unit_id}.terms: expected list")
        for term in unit["terms"]:
            texts(term, f"{unit_id}.term", 3)
            require(len(term) == 3, f"{unit_id}.term must have exactly three columns")
        lesson = unit.get("lesson")
        fields(lesson, ["question", "provenance"], f"{unit_id}.lesson")
        for name in ["prerequisites", "conceptMap", "transfer"]:
            texts(lesson.get(name), f"{unit_id}.lesson.{name}")
        sections = lesson.get("sections")
        require(isinstance(sections, list) and sections, f"{unit_id}.lesson.sections missing")
        local_sections = set()
        for section in sections:
            fields(section, ["id", "heading", "why", "body", "examCue", "source"], f"{unit_id}.section")
            section_id = identifier(section["id"], "section.id")
            require(section_id not in section_ids, f"duplicate section ID: {section_id}")
            section_ids.add(section_id)
            local_sections.add(section_id)
            for name in ["points", "pitfalls"]:
                texts(section.get(name), f"{section_id}.{name}")
            fields(section.get("example"), ["title", "conclusion"], f"{section_id}.example")
            texts(section["example"].get("steps"), f"{section_id}.example.steps", 2)
        worked = lesson.get("workedExample")
        fields(worked, ["scenario", "conclusion"], f"{unit_id}.workedExample")
        texts(worked.get("steps"), f"{unit_id}.workedExample.steps", 2)
        questions = unit.get("questions")
        require(isinstance(questions, list) and questions, f"{unit_id}.questions missing")
        for question in questions:
            fields(question, ["id", "type", "prompt", "explanation", "source"], f"{unit_id}.question")
            question_id = identifier(question["id"], "question.id")
            require(question_id not in question_ids, f"duplicate question ID: {question_id}")
            question_ids.add(question_id)
            question.setdefault("level", "基础")
            text(question["level"], f"{question_id}.level")
            texts(question.get("sectionIds"), f"{question_id}.sectionIds")
            require(set(question["sectionIds"]) <= local_sections, f"{question_id}: unknown section reference")
            if question["type"] == "choice":
                texts(question.get("options"), f"{question_id}.options", 2)
                answer = question.get("answer")
                require(type(answer) is int and 0 <= answer < len(question["options"]), f"{question_id}: invalid answer index")
            elif question["type"] == "written":
                texts(question.get("rubric"), f"{question_id}.rubric")
            else:
                raise ValueError(f"{question_id}: supported types are choice and written")
    return payload


def read_course(path):
    raw = path.read_text(encoding="utf-8")
    require(len(raw.encode("utf-8")) <= 20_000_000, "course JSON exceeds 20 MB")
    return validate_course(json.loads(raw))


def script_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def replace_tokens(template, replacements):
    tokens = set(re.findall(r"__[A-Z_]+__", template))
    require(tokens == set(replacements), f"template token mismatch: {tokens ^ set(replacements)}")
    return re.sub(r"__[A-Z_]+__", lambda match: replacements[match.group()], template)


def build(payload, mode, output):
    require(mode in {"local-html", "vercel"}, "unknown output mode")
    payload = validate_course(copy.deepcopy(payload))
    require(not output.exists(), f"output already exists: {output}; choose a new directory")
    course = payload["course"]
    data_script = "window.EXAM_KIT_DATA = " + script_json(payload) + ";\n"
    document = replace_tokens((TEMPLATE_ROOT / "index.html").read_text(encoding="utf-8"), {
        "__PAGE_TITLE__": html.escape(course["title"]),
        "__FOOTER_TEXT__": "本地学习记录",
        "__MANIFEST_LINK__": '<link rel="manifest" href="manifest.json">' if mode == "vercel" else "",
        "__CONTENT_SCRIPTS__": '<script src="data.js"></script>' if mode == "vercel" else f"<script>{data_script}</script>",
        "__SERVICE_WORKER__": 'if ("serviceWorker" in navigator && ["https:", "http:"].includes(location.protocol)) navigator.serviceWorker.register("sw.js").catch(() => {});' if mode == "vercel" else "",
    })
    output.mkdir(parents=True)
    (output / "交付记录.json").write_text(json.dumps({
        "courseId": course["id"], "version": payload["version"], "mode": mode,
        "status": "generated-not-deployed", "units": len(payload["units"]),
        "questions": sum(len(unit["questions"]) for unit in payload["units"]),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if mode == "local-html":
        (output / "复习工作台.html").write_text(document, encoding="utf-8")
        (output / "本地使用说明.md").write_text(
            f"# {course['title']}\n\n用桌面浏览器打开同目录的 `复习工作台.html`，无需安装软件或启动服务器。\n\n"
            "文件包含讲解、题库和交互，不联网调用 AI。作答不会自动写回 HTML；浏览器可能保存记录，但 file: 存储行为因环境而异。请固定文件位置，定期在薄弱点页导出复习记录。\n\n"
            "此版本支持导出供 AI 读取，尚不支持记录导入或跨设备同步。不要清除网站数据来排查问题。移动端文件预览器可能不运行脚本，需要分享网址时再生成 Vercel 版。\n", encoding="utf-8")
    else:
        publish = output / "vercel-deploy"
        publish.mkdir()
        (publish / "index.html").write_text(document, encoding="utf-8")
        (publish / "data.js").write_text(data_script, encoding="utf-8")
        manifest = json.loads((TEMPLATE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest.update(name=course["title"], short_name=course.get("shortTitle", course["title"])[:20])
        (publish / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        digest = hashlib.sha256((document + data_script + json.dumps(manifest) + (TEMPLATE_ROOT / "sw.js").read_text()).encode()).hexdigest()[:16]
        worker = replace_tokens((TEMPLATE_ROOT / "sw.js").read_text(), {
            "__CACHE_NAME__": f"exam-review-{course['id']}-{digest}",
            "__CACHE_PREFIX__": f"exam-review-{course['id']}-",
        })
        (publish / "sw.js").write_text(worker, encoding="utf-8")
        with zipfile.ZipFile(output / "复习工作台-vercel.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for resource in sorted(publish.iterdir()):
                archive.write(resource, resource.name)
        guide = (SKILL_ROOT / "references" / "vercel-guide.md").read_text(encoding="utf-8")
        marker = "## 1. 你会拿到哪些文件"
        require(marker in guide, "Vercel guide missing user instructions")
        guide = guide[guide.index(marker):].replace("  lesson-details.js\n", "")
        preface = f"# {course['title']} · Vercel 上传指南\n\n课程版本：{payload['version']}。当前状态：已生成，尚未上传。\n\n本次 ZIP 为 `复习工作台-vercel.zip`，根部有 index.html、data.js、manifest.json、sw.js 共四个文件；深度正文已合入 data.js，无需独立 lesson-details.js。先人工检查内容可公开，再按下列步骤上传。\n\n"
        (output / "Vercel上传指南.md").write_text(preface + guide, encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", type=Path, required=True, help="course.json, not executable JavaScript")
    parser.add_argument("--mode", choices=["local-html", "vercel"], required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output directory")
    args = parser.parse_args()
    try:
        result = build(read_course(args.course), args.mode, args.output)
    except (OSError, ValueError, TypeError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(f"Built {args.mode}: {result.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
