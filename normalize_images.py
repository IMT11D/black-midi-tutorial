# -*- coding: utf-8 -*-
"""
图片位置命名转正（Release 工作流自动调用，也可本地手动运行）

规则:
- 扫描 docs/*.md 正文（跳过代码围栏内的示例），按图片在文中首次出现的顺序，
  将 docs/media 中的图片重命名为「章_节_小节_序号」：
    04_00_00_NN  第 4 章开篇（不隶属任何节）
    04_01_00_NN  4.1 节本文中（不隶属任何小节）
    04_01_02_NN  4.1.2 小节中
- 序号在同一位置内按首次出现顺序从 01 递增；
- 同一张图被多处引用时，以首次出现的位置命名（其余引用改为同一文件名）；
- 未被任何正文引用的图片保持原样，并在报告中单独列出；
- 扩展名保持不变；重复执行幂等（已转正的文件不会被再次改动）。

用法:
    python normalize_images.py          # 仅预演（列出将发生的重命名）
    python normalize_images.py --apply  # 执行：重命名文件并改写全部引用
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
MEDIA = os.path.join(DOCS, "media")
APPLY = "--apply" in sys.argv

HEAD_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
CHAPTER_NUM_RE = re.compile(r"^(\d+)")
SECTION_NUM_RE = re.compile(r"^(\d+)\.(\d+)")
SUBSECTION_NUM_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")
MD_REF_RE = re.compile(r"(!\[[^\]]*\]\()media/([^)\s]+)([^)]*\))")
IMG_REF_RE = re.compile(r"(<img[^>]*\bsrc=[\"'])media/([^\"']+)([\"'])")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")


def docs_files():
    """正文文件（按 00-11 顺序，排除 SUMMARY.md）"""
    return sorted(
        f for f in os.listdir(DOCS) if f.endswith(".md") and f != "SUMMARY.md"
    )


def scan_refs():
    """按章节顺序收集图片引用。

    返回 (first_loc, loc_images, missing_refs):
    - first_loc: {图片名: 'CC_SS_TT'} 首次出现位置
    - loc_images: {'CC_SS_TT': [该位置首次出现的图片名, ...]}（出现顺序）
    - missing_refs: [(文件名, 行号, 图片名), ...] 引用了不存在的文件
    """
    first_loc = {}
    loc_images = {}
    missing_refs = []
    for fn in docs_files():
        fm = CHAPTER_NUM_RE.match(fn)
        ch = int(fm.group(1)) if fm else 0
        sec, sub = 0, 0
        in_fence = False
        fence = ""
        with open(os.path.join(DOCS, fn), encoding="utf-8") as f:
            lines = f.read().split("\n")
        for i, ln in enumerate(lines, 1):
            mf = FENCE_RE.match(ln)
            if mf:
                marker = mf.group(1)[0]
                if not in_fence:
                    in_fence, fence = True, marker
                elif marker == fence:
                    in_fence = False
                continue
            if in_fence:
                continue
            hm = HEAD_RE.match(ln)
            if hm:
                level, text = len(hm.group(1)), hm.group(2)
                if level == 1:
                    m = CHAPTER_NUM_RE.match(text)
                    if m:
                        ch = int(m.group(1))
                    sec = sub = 0
                elif level == 2:
                    m = SECTION_NUM_RE.match(text)
                    sec = int(m.group(2)) if m else 0
                    sub = 0
                else:
                    m = SUBSECTION_NUM_RE.match(text)
                    sub = int(m.group(3)) if m else 0
                continue
            for rx in (MD_REF_RE, IMG_REF_RE):
                for m in rx.finditer(ln):
                    name = m.group(2)
                    if not os.path.isfile(os.path.join(MEDIA, name)):
                        missing_refs.append((fn, i, name))
                        continue
                    if name not in first_loc:
                        loc = f"{ch:02d}_{sec:02d}_{sub:02d}"
                        first_loc[name] = loc
                        loc_images.setdefault(loc, []).append(name)
    return first_loc, loc_images, missing_refs


def build_mapping(loc_images):
    """位置内按首次出现顺序编号，返回 {旧名: 新名}"""
    mapping = {}
    for loc in sorted(loc_images):
        for n, old in enumerate(loc_images[loc], 1):
            ext = os.path.splitext(old)[1]
            mapping[old] = f"{loc}_{n:02d}{ext}"
    return mapping


def rewrite_refs(mapping):
    """改写全部正文引用，返回改动行数"""
    total = 0
    for fn in docs_files():
        path = os.path.join(DOCS, fn)
        with open(path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        eol = "\r\n" if "\r\n" in content else "\n"
        norm = content.replace("\r\n", "\n") if eol == "\r\n" else content
        out = []
        in_fence = False
        fence = ""
        n_file = 0

        def repl_md(m):
            return m.group(1) + "media/" + mapping.get(m.group(2), m.group(2)) + m.group(3)

        def repl_img(m):
            return m.group(1) + "media/" + mapping.get(m.group(2), m.group(2)) + m.group(3)

        for ln in norm.split("\n"):
            mf = FENCE_RE.match(ln)
            if mf:
                marker = mf.group(1)[0]
                if not in_fence:
                    in_fence, fence = True, marker
                elif marker == fence:
                    in_fence = False
                out.append(ln)
                continue
            if not in_fence:
                new_ln = MD_REF_RE.sub(repl_md, ln)
                new_ln = IMG_REF_RE.sub(repl_img, new_ln)
                if new_ln != ln:
                    n_file += 1
                    ln = new_ln
            out.append(ln)
        if n_file:
            total += n_file
            if APPLY:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(eol.join(out))
    return total


def main():
    if not os.path.isdir(MEDIA):
        sys.exit("未找到 docs/media 目录")

    _, loc_images, missing_refs = scan_refs()
    mapping = build_mapping(loc_images)
    renames = {o: n for o, n in mapping.items() if o != n}

    print("=== 图片位置命名转正 ===")
    print(f"正文引用的图片: {len(mapping)} 张；需重命名: {len(renames)} 张")
    for old, new in sorted(renames.items()):
        print(f"  {old}  ->  {new}")

    all_files = {
        f for f in os.listdir(MEDIA) if os.path.isfile(os.path.join(MEDIA, f))
    }
    unused = sorted(all_files - set(mapping.keys()))
    if unused:
        print("未被正文引用的图片（保持原样）:")
        for f in unused:
            print(f"  {f}")

    if missing_refs:
        print("引用了不存在的图片:")
        for fn, i, name in missing_refs:
            print(f"  !! {fn}:{i} media/{name}")

    conflicts = [
        new for old, new in renames.items()
        if new in all_files and new not in mapping
    ]
    if conflicts:
        sys.exit("目标文件名被未引用的文件占用，已中止: " + "、".join(sorted(conflicts)))

    if not APPLY:
        print("完成。 (未写入, 加 --apply 生效)")
        return

    if renames:
        temps = {}
        for k, (old, new) in enumerate(sorted(renames.items())):
            ext = os.path.splitext(old)[1]
            tmp = os.path.join(MEDIA, f"__norm_tmp_{k:04d}{ext}")
            os.replace(os.path.join(MEDIA, old), tmp)
            temps[tmp] = new
        for tmp, new in temps.items():
            os.replace(tmp, os.path.join(MEDIA, new))

    n_refs = rewrite_refs(mapping)
    print(f"已重命名 {len(renames)} 张，改写引用 {n_refs} 行。")
    print("完成。")


if __name__ == "__main__":
    main()
