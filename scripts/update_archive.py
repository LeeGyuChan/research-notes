"""
update_archive.py
─────────────────
프로젝트 폴더를 스캔하여 index.html 내 projects 배열을 자동 갱신합니다.

파일명 규칙 (없어도 동작하지만, 있으면 메타 자동 추론):
  날짜  : 파일명에 YYYY-MM 또는 YYYY_MM 포함  →  date 자동 설정
  버전  : _v숫자  포함  →  제목에 표시
  타입  : 키워드 매핑으로 자동 분류 (아래 TYPE_RULES 참고)
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# ── 설정 ──────────────────────────────────────────────────────────

# 스캔할 프로젝트 폴더 정의
# folder      : 실제 디렉터리 경로 (index.html 기준 상대경로)
# id          : HTML anchor id
# icon        : 이모지
# iconBg      : 아이콘 배경색
# label       : 수요기관 표시명
# title       : 프로젝트 제목
# color       : 배지 색상 (blue|teal|amber|purple|green|gray|coral)
PROJECTS_META = [
    {
        "folder": "daewon",
        "id": "daewon",
        "icon": "🏭",
        "iconBg": "#E6F1FB",
        "label": "수요기관 · 대원공업㈜",
        "title": "자동 분체 도장라인 멀티모달 AI 불량예방 시스템",
        "color": "blue",
    },
    {
        "folder": "safety",
        "id": "safety",
        "icon": "⚠️",
        "iconBg": "#FAEEDA",
        "label": "중소 제조현장",
        "title": "사고 실시간 탐지 시스템",
        "color": "amber",
    },
    # 새 프로젝트 추가 시 여기에 딕셔너리 하나 추가
]

# 파일 확장자 → 표시 여부 (False = 숨김)
ALLOWED_EXTENSIONS = {".html", ".pdf", ".md"}

# 파일명 키워드 → type 자동 분류
TYPE_RULES = [
    (["보고서", "report", "결과", "최종"], "report"),
    (["연구노트", "note", "노트", "실험"],  "note"),
    (["설계", "spec", "architecture"],     "spec"),
    (["데이터", "data", "dataset"],         "data"),
    (["발표", "슬라이드", "ppt", "slide"],  "etc"),
]

# 파일명 키워드 → tags 자동 추출
TAG_RULES = [
    "YOLO", "ByteTrack", "Optical Flow", "GRU", "CNN",
    "Edge AI", "멀티모달", "불량예방", "발표자료", "실증저변확대형",
    "딥러닝", "객체탐지", "분류", "세그멘테이션",
]

# 정렬 우선순위: type 순서
TYPE_ORDER = ["report", "spec", "note", "data", "etc"]

# ── 헬퍼 ──────────────────────────────────────────────────────────

def infer_type(name: str) -> str:
    lower = name.lower()
    for keywords, t in TYPE_RULES:
        if any(k.lower() in lower for k in keywords):
            return t
    return "etc"

def infer_tags(name: str) -> list[str]:
    found = []
    for tag in TAG_RULES:
        if tag.lower() in name.lower():
            found.append(tag)
    return found

def infer_date(name: str) -> str:
    m = re.search(r"(20\d{2})[-_]?(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return datetime.now().strftime("%Y-%m")

def make_title(name: str) -> str:
    """파일명 → 사람이 읽기 좋은 제목으로 변환"""
    stem = Path(name).stem
    # 앞 숫자 + 언더스코어 제거 (예: 09_발표자료...)
    stem = re.sub(r"^\d+_", "", stem)
    # 버전 태그 보존하면서 언더스코어/하이픈 → 공백
    stem = stem.replace("_", " ").replace("-", " ")
    # 연속 공백 정리
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem

def infer_desc(name: str, tags: list[str]) -> str:
    parts = []
    if tags:
        parts.append(" · ".join(tags[:3]))
    return ", ".join(parts) if parts else ""

def scan_folder(folder: str) -> list[dict]:
    """폴더 내 허용 확장자 파일을 스캔하여 file 객체 리스트 반환"""
    p = Path(folder)
    if not p.exists():
        return []

    files = []
    for f in sorted(p.iterdir()):
        if f.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        if f.name.startswith("."):
            continue

        name   = f.name
        tags   = infer_tags(name)
        entry  = {
            "title": make_title(name),
            "desc":  infer_desc(name, tags),
            "file":  f"{folder}/{name}",
            "type":  infer_type(name),
            "date":  infer_date(name),
            "tags":  tags,
        }
        files.append(entry)

    # type 우선순위로 정렬
    files.sort(key=lambda x: (TYPE_ORDER.index(x["type"]) if x["type"] in TYPE_ORDER else 99, x["title"]))
    return files

# ── JSON → JS 직렬화 ──────────────────────────────────────────────

def to_js_value(v, indent=0) -> str:
    pad  = "  " * indent
    pad1 = "  " * (indent + 1)
    if isinstance(v, dict):
        inner = ",\n".join(f'{pad1}{json.dumps(k)}: {to_js_value(val, indent+1)}' for k, val in v.items())
        return f"{{\n{inner}\n{pad}}}"
    if isinstance(v, list):
        if not v:
            return "[]"
        inner = ", ".join(json.dumps(i) for i in v)
        return f"[{inner}]"
    return json.dumps(v, ensure_ascii=False)

def build_projects_js(projects: list[dict]) -> str:
    lines = ["const projects = [", ""]
    for p in projects:
        meta   = {k: v for k, v in p.items() if k != "files"}
        files  = p.get("files", [])

        lines.append(f"  // ── {meta['title']} ──")
        lines.append("  {")
        for k, v in meta.items():
            lines.append(f"    {k}: {to_js_value(v)},")
        lines.append("    files: [")
        for f in files:
            inner = ", ".join(f"{json.dumps(k)}: {to_js_value(v)}" for k, v in f.items())
            lines.append(f"      {{ {inner} }},")
        if not files:
            lines.append("      // 파일 없음")
        lines.append("    ],")
        lines.append("  },")
        lines.append("")

    lines.append("];")
    return "\n".join(lines)

# ── index.html 패치 ───────────────────────────────────────────────

MARKER_START = "// ════════════════════════════════════════════════════════════════\n//  렌더링 (수정 불필요)"

def patch_index(html: str, new_js: str) -> str:
    """index.html 내 `const projects = [...]` 블록을 교체"""
    # projects 블록 시작 위치
    start = html.find("const projects = [")
    if start == -1:
        raise ValueError("index.html에서 'const projects = [' 를 찾을 수 없습니다.")

    # 렌더링 마커(교체 끝 경계) 위치
    end = html.find(MARKER_START, start)
    if end == -1:
        raise ValueError("렌더링 마커를 찾을 수 없습니다. index.html을 확인하세요.")

    return html[:start] + new_js + "\n\n\n" + html[end:]

# ── 메인 ──────────────────────────────────────────────────────────

def main():
    index_path = Path("index.html")
    if not index_path.exists():
        raise FileNotFoundError("index.html이 현재 디렉터리에 없습니다.")

    html = index_path.read_text(encoding="utf-8")

    # 프로젝트별 파일 스캔
    projects = []
    for meta in PROJECTS_META:
        folder = meta.pop("folder")
        meta["files"] = scan_folder(folder)
        projects.append(meta)

    new_js = build_projects_js(projects)
    patched = patch_index(html, new_js)

    index_path.write_text(patched, encoding="utf-8")
    print("✅ index.html 업데이트 완료")

    # 스캔 결과 요약 출력
    for p in projects:
        print(f"  {p['icon']} {p['title']} — {len(p['files'])}개 파일")

if __name__ == "__main__":
    main()
