import os
import re

DOCS_DIR = "docs"
OUTPUT = os.path.join(DOCS_DIR, "SUMMARY.md")

# 收集所有 md 文件，排除 SUMMARY.md 和 _sidebar.md 本身
md_files = sorted([
    f for f in os.listdir(DOCS_DIR)
    if f.endswith(".md") and f not in ("SUMMARY.md", "_sidebar.md")
])

# docsify@4 的 slugify 精确复刻：
# 小写A-Z -> 去HTML标签 -> 去以下范围标点（全角标点保留）
# -> 空白转- -> 合并- -> 数字开头加下划线
RE_PUNCT = re.compile("[\u2000-\u206F\u2E00-\u2E7F\\\\'!\"#$%&()*+,./:;<=>?@\\[\\]^`{|}~]")


def docsify_slug(text):
    # marked 内联解析：反斜杠转义的 ASCII 标点还原为字面量
    s = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", text)
    s = s.strip()
    s = re.sub(r"[A-Z]+", lambda m: m.group(0).lower(), s)
    s = re.sub(r"<[^>]+>", "", s)
    s = RE_PUNCT.sub("", s)
    s = re.sub(r"\s", "-", s)
    s = re.sub(r"-+", "-", s)
    s = re.sub(r"^(\d)", r"_\1", s)
    return s


def make_anchor(number, title):
    """按 Docsify 规则生成锚点"""
    text = (f"{number} {title}").strip() if number else title
    return docsify_slug(text)


lines = []

for fname in md_files:
    path = os.path.join(DOCS_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 找所有标题（跳过 ``` / ~~~ 代码围栏内部）
    in_fence = False
    fence = ""
    for line in content.split("\n"):
        mf = re.match(r"^\s*(```+|~~~+)", line)
        if mf:
            marker = mf.group(1)[0]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        # 侧边栏只收录一~三级标题（#### 及更深层级不进入目录）
        m = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if not m:
            continue
        level = len(m.group(1))
        raw_title = m.group(2).strip()

        # 拆出编号和标题文字
        num_match = re.match(r"^(\d+(?:\.\d+)*)\s+(.+)$", raw_title)
        if num_match:
            number = num_match.group(1)
            title = num_match.group(2).strip()
        else:
            number = ""
            title = raw_title

        # 去掉标题里的 Markdown 特殊符号（仅用于侧边栏显示）
        clean_title = re.sub(r"[*_`]", "", title)

        indent = "  " * (level - 1)

        if number:
            display = f"{number} {clean_title}"
        else:
            display = clean_title

        # 锚点用标题原文计算（与 docsify 实际渲染一致），不使用清洗后的文本
        anchor = make_anchor(number, title)

        lines.append(f"{indent}* [{display}]({fname}#{anchor})")

# 使用平台默认换行（Windows 输出 CRLF，Linux/CI 输出 LF），保证本地与 CI 生成结果一致
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"已生成 {OUTPUT}，共 {len(lines)} 个条目。")
