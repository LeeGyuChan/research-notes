"""
update_archive.py  v3
──────────────────────────────────────────────────────────────
변경사항 (v3)
  1. projects/ 하위 폴더 자동 감지 — PROJECTS_META 등록 불필요
  2. 한글·공백·특수문자 폴더명 완전 지원
  3. topics/ 도 AUTO_TOPICS_DIRS 에 루트 폴더만 지정하면 자동 감지
  4. 폴더명 → id/color/icon 자동 매핑

폴더 구조 예시 (index.html 기준)
  computer-vision/tracking/review_ByteTrack_v1.html
  projects/자동 분체 도장라인 멀티모달 AI 불량예방 시스템/note_설계검토_v7.html

파일명 prefix → type
  review_ note_ ref_ report_ spec_ data_
숨김: README.md, _templates/, 파일명이 . 로 시작
"""

import re, json
from pathlib import Path
from datetime import datetime

# ── 설정 ──────────────────────────────────────────────────────

ALLOWED_EXT    = {".html", ".pdf", ".md"}
HIDDEN_FILES   = {"readme.md"}
HIDDEN_FOLDERS = {"_templates", ".git", ".github", "scripts", "node_modules"}

# 주제 루트 폴더 목록 (이 안의 1-depth 서브폴더가 subfolder label이 됨)
AUTO_TOPICS_DIRS = [
    "computer-vision",
    "machine-learning",
    # 새 주제 추가 시 여기에만 추가
]

# projects/ 하위는 완전 자동 감지 — 별도 등록 불필요

# 주제 폴더명 → 아이콘/색상 매핑 (없으면 기본값 사용)
TOPIC_META_MAP = {
    "computer-vision":  {"icon": "👁",  "iconBg": "#E4EFFE", "color": "blue"},
    "machine-learning": {"icon": "🧠", "iconBg": "#DFF5ED", "color": "teal"},
    "nlp":              {"icon": "💬", "iconBg": "#ECEAFD", "color": "purple"},
    "robotics":         {"icon": "🤖", "iconBg": "#E8F2DC", "color": "green"},
}

# 프로젝트 폴더명 → 아이콘/색상/라벨 매핑 (없으면 기본값 사용)
PROJECT_META_MAP = {
    "자동 분체 도장라인 멀티모달 AI 불량예방 시스템": {
        "icon": "🏭", "iconBg": "#E4EFFE", "color": "blue",
        "label": "수요기관 · 대원공업㈜",
    },
    "사고 실시간 탐지 시스템": {
        "icon": "⚠️", "iconBg": "#FAF0D8", "color": "amber",
        "label": "중소 제조현장",
    },
    # 새 프로젝트 폴더가 생겨도 여기 없으면 기본값 자동 적용
}

DEFAULT_TOPIC_META   = {"icon": "📂", "iconBg": "#EFEDE6", "color": "gray"}
DEFAULT_PROJECT_META = {"icon": "🗂",  "iconBg": "#EFEDE6", "color": "gray", "label": "프로젝트"}

# prefix → type
PREFIX_TYPE = {
    "review_": "review", "note_":   "note",   "ref_":    "ref",
    "report_": "report", "spec_":   "spec",   "data_":   "data",
}

KEYWORD_TYPE = [
    (["보고서","report","결과","최종"], "report"),
    (["연구노트","note","노트","실험"],  "note"),
    (["리뷰","review","survey"],        "review"),
    (["설계","spec","architecture"],    "spec"),
    (["데이터","data","dataset"],       "data"),
    (["참고","ref","비교","정리"],      "ref"),
    (["발표","슬라이드","ppt"],         "etc"),
]

TAG_KEYWORDS = [
    "YOLO","YOLOX","ByteTrack","DeepSORT","Optical Flow",
    "GRU","LSTM","CNN","Transformer","TFT",
    "Edge AI","멀티모달","불량예방","발표자료","실증저변확대형",
    "딥러닝","객체탐지","Re-ID","MOT","anchor-free",
    "시계열","LR","optimizer","배포",
]

TYPE_ORDER = ["report","review","spec","note","ref","data","etc"]

END_MARKER = "// ════════════════════════════════════════════════════════════════\n//  렌더링 (수정 불필요)"


# ── 파일 메타 추론 ─────────────────────────────────────────────

def infer_type(name):
    lower = name.lower()
    for prefix, t in PREFIX_TYPE.items():
        if lower.startswith(prefix):
            return t
    for keywords, t in KEYWORD_TYPE:
        if any(k.lower() in lower for k in keywords):
            return t
    return "etc"

def infer_tags(name):
    return [tag for tag in TAG_KEYWORDS if tag.lower() in name.lower()]

def infer_date(name):
    m = re.search(r"(20\d{2})[-_]?(\d{2})", name)
    return f"{m.group(1)}-{m.group(2)}" if m else datetime.now().strftime("%Y-%m")

def make_title(name):
    stem = Path(name).stem
    for prefix in PREFIX_TYPE:
        if stem.lower().startswith(prefix):
            stem = stem[len(prefix):]
            break
    stem = re.sub(r"^\d+_", "", stem)
    return re.sub(r"\s+", " ", stem.replace("_", " ").replace("-", " ")).strip()

def is_hidden(path: Path):
    if path.name.startswith("."): return True
    if path.name.lower() in HIDDEN_FILES: return True
    for part in path.parts:
        if part in HIDDEN_FOLDERS: return True
    return False


# ── 폴더 스캔 ─────────────────────────────────────────────────

def folder_to_id(name: str) -> str:
    """폴더명 → HTML anchor id (영문·숫자·하이픈만)"""
    s = re.sub(r"[^\w\s-]", "", name)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "section"

def scan_subfolders(root: Path) -> list[dict]:
    """root 하위를 1-depth 서브폴더 단위로 스캔"""
    if not root.exists():
        return []
    result: dict[str, list] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file(): continue
        if path.suffix.lower() not in ALLOWED_EXT: continue
        if is_hidden(path): continue
        rel   = path.relative_to(root)
        label = rel.parts[0] if len(rel.parts) > 1 else ""
        tags  = infer_tags(path.name)
        result.setdefault(label, []).append({
            "title": make_title(path.name),
            "desc":  " · ".join(tags[:3]) if tags else "",
            "file":  str(path).replace("\\", "/"),
            "type":  infer_type(path.name),
            "date":  infer_date(path.name),
            "tags":  tags,
        })
    subfolders = []
    for label, files in result.items():
        files.sort(key=lambda x: (
            TYPE_ORDER.index(x["type"]) if x["type"] in TYPE_ORDER else 99, x["title"]
        ))
        subfolders.append({"label": label, "files": files})
    subfolders.sort(key=lambda x: x["label"])
    return subfolders

def build_topics() -> list[dict]:
    sections = []
    for folder_name in AUTO_TOPICS_DIRS:
        p = Path(folder_name)
        if not p.exists(): continue
        meta = {**DEFAULT_TOPIC_META, **TOPIC_META_MAP.get(folder_name, {})}
        sections.append({
            "id":         folder_to_id(folder_name),
            "icon":       meta["icon"],
            "iconBg":     meta["iconBg"],
            "label":      f"주제 · {folder_name}",
            "title":      folder_name,
            "color":      meta["color"],
            "subfolders": scan_subfolders(p),
        })
    return sections

def build_projects() -> list[dict]:
    """projects/ 하위 폴더를 자동 감지"""
    projects_root = Path("projects")
    if not projects_root.exists():
        return []

    sections = []
    # 한글·공백 포함 폴더명도 정상 처리
    for folder in sorted(projects_root.iterdir()):
        if not folder.is_dir(): continue
        if folder.name.startswith(".") or folder.name in HIDDEN_FOLDERS: continue

        name = folder.name
        meta = {**DEFAULT_PROJECT_META, **PROJECT_META_MAP.get(name, {})}
        sections.append({
            "id":         folder_to_id(name),
            "icon":       meta["icon"],
            "iconBg":     meta["iconBg"],
            "label":      meta.get("label", f"프로젝트 · {name}"),
            "title":      name,
            "color":      meta["color"],
            "subfolders": scan_subfolders(folder),
        })
    return sections


# ── JS 직렬화 ──────────────────────────────────────────────────

def jv(v) -> str:
    if isinstance(v, bool):          return "true" if v else "false"
    if isinstance(v, (int, float)):  return str(v)
    if isinstance(v, str):           return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        if not v: return "[]"
        return "[" + ", ".join(jv(i) for i in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{json.dumps(k)}: {jv(val)}" for k, val in v.items()) + " }"
    return json.dumps(v, ensure_ascii=False)

def build_array_js(var_name: str, sections: list[dict]) -> str:
    lines = [f"const {var_name} = [", ""]
    for sec in sections:
        lines.append(f"  // ── {sec['title']} ──")
        lines.append("  {")
        for k, v in sec.items():
            if k == "subfolders":
                lines.append("    subfolders: [")
                for sf in v:
                    lines.append("      {")
                    lines.append(f"        label: {jv(sf['label'])},")
                    lines.append("        files: [")
                    for f in sf["files"]:
                        inner = ", ".join(f"{json.dumps(fk)}: {jv(fv)}" for fk, fv in f.items())
                        lines.append(f"          {{ {inner} }},")
                    lines.append("        ],")
                    lines.append("      },")
                lines.append("    ],")
            else:
                lines.append(f"    {json.dumps(k)}: {jv(v)},")
        lines.append("  },")
        lines.append("")
    lines.append("];")
    return "\n".join(lines)


# ── index.html 패치 ────────────────────────────────────────────

def patch_block(html: str, var_name: str, new_js: str) -> str:
    start = re.search(rf"const {var_name}\s*=\s*\[", html)
    if not start:
        raise ValueError(f"'const {var_name} = [' 를 찾을 수 없습니다.")
    next_const = re.search(r"\nconst \w+ = \[", html[start.end():])
    end_marker = html.find(END_MARKER, start.start())
    block_end  = (start.end() + next_const.start()) if next_const else end_marker
    if block_end == -1:
        raise ValueError("블록 끝 마커를 찾을 수 없습니다.")
    return html[:start.start()] + new_js + "\n\n" + html[block_end:]


# ── 메인 ───────────────────────────────────────────────────────

def main():
    index_path = Path("index.html")
    if not index_path.exists():
        raise FileNotFoundError("index.html 이 현재 디렉터리에 없습니다.")

    html     = index_path.read_text(encoding="utf-8")
    topics   = build_topics()
    projects = build_projects()

    html = patch_block(html, "topics",   build_array_js("topics",   topics))
    html = patch_block(html, "projects", build_array_js("projects", projects))
    index_path.write_text(html, encoding="utf-8")

    print("✅ index.html 업데이트 완료")
    for s in topics:
        total = sum(len(sf["files"]) for sf in s["subfolders"])
        print(f"  {s['icon']} [주제]     {s['title']} — {total}개 파일")
    for s in projects:
        total = sum(len(sf["files"]) for sf in s["subfolders"])
        print(f"  {s['icon']} [프로젝트] {s['title']} — {total}개 파일")

if __name__ == "__main__":
    main()
