name: Update Document Archive

on:
  push:
    paths:
      # ── 주제 폴더 ──────────────────────────────
      - 'computer-vision/**'
      - 'machine-learning/**'
      # 새 주제 폴더 추가 시 여기에도 추가

      # ── 프로젝트 폴더 (하위 전체 자동 감지) ────
      - 'projects/**'

      # ── 스크립트 자체가 바뀌면 재실행 ──────────
      - 'scripts/update_archive.py'

  workflow_dispatch: # Actions 탭에서 수동 실행 가능

jobs:
  update-index:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run archive updater
        run: python scripts/update_archive.py

      - name: Commit & Push if changed
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add index.html
          git diff --cached --quiet && echo "No changes — skip commit" || \
            (git commit -m "chore: auto-update archive index [skip ci]" && git push)
