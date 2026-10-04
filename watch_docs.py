# -*- coding: utf-8 -*-
"""
本地编辑辅助：监测 docs/ 正文变化，自动重建侧边栏（docs/SUMMARY.md）

用法:
    python watch_docs.py    # 常驻监测，Ctrl+C 退出

说明:
- 每秒检查一次 docs/*.md 的修改时间，任一正文文件变化就运行 gen_toc_from_docs.py；
- 只重建侧边栏，不改动正文；建议与本地预览同时使用（见 CONTRIBUTING「六、本地预览」）；
- 仅为编辑方便：不运行时行为不变，合并后 CI 仍会自动重建。
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def snapshot():
    """记录 docs/*.md（不含 SUMMARY.md）的修改时间"""
    out = {}
    for f in os.listdir(DOCS):
        if f.endswith(".md") and f != "SUMMARY.md":
            try:
                out[f] = os.path.getmtime(os.path.join(DOCS, f))
            except OSError:
                pass
    return out


def main():
    print("监测中：修改 docs/ 下的正文后会自动重建侧边栏（Ctrl+C 退出）...", flush=True)
    last = snapshot()
    while True:
        time.sleep(1)
        cur = snapshot()
        if cur != last:
            changed = [f for f in cur if last.get(f) != cur.get(f)]
            subprocess.run(
                [sys.executable, os.path.join(ROOT, "gen_toc_from_docs.py")],
                cwd=ROOT,
            )
            print(f"  已重建侧边栏（触发: {'、'.join(changed) or '文件变化'}）", flush=True)
            last = cur


if __name__ == "__main__":
    main()
