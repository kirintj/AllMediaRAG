"""批量抓取技术文档，保存为 Markdown 文件供 RAG 使用

用法：
    python backend/scripts/fetch_docs.py                    # 抓取全部源
    python backend/scripts/fetch_docs.py --source langchain # 只抓 LangChain
    python backend/scripts/fetch_docs.py --source python    # 只抓 Python 官方文档
    python backend/scripts/fetch_docs.py --source huggingface  # 只抓 HuggingFace
    python backend/scripts/fetch_docs.py --max-pages 50     # 限制每个源最多 50 页
"""

import os
import re
import sys
import time
import argparse
import hashlib
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

# 文档源配置：(名称, 起始URL, 链接前缀过滤)
DOC_SOURCES = {
    "langchain": {
        "name": "LangChain 官方文档",
        "base_url": "https://python.langchain.com/docs/",
        "link_prefix": "/docs/",
        "max_pages": 100,
    },
    "langgraph": {
        "name": "LangGraph 官方文档",
        "base_url": "https://langchain-ai.github.io/langgraph/",
        "link_prefix": "/langgraph/",
        "max_pages": 60,
    },
    "python": {
        "name": "Python 官方教程",
        "base_url": "https://docs.python.org/zh-cn/3/tutorial/",
        "link_prefix": "/zh-cn/3/tutorial/",
        "max_pages": 40,
    },
    "huggingface": {
        "name": "HuggingFace Transformers 文档",
        "base_url": "https://huggingface.co/docs/transformers/index",
        "link_prefix": "/docs/transformers/",
        "max_pages": 80,
    },
    "fastapi": {
        "name": "FastAPI 官方文档",
        "base_url": "https://fastapi.tiangolo.com/zh/",
        "link_prefix": "/zh/",
        "max_pages": 60,
    },
    "python_library": {
        "name": "Python 标准库",
        "base_url": "https://docs.python.org/zh-cn/3/library/",
        "link_prefix": "/zh-cn/3/library/",
        "max_pages": 60,
    },
    "openai_api": {
        "name": "OpenAI API 文档",
        "base_url": "https://platform.openai.com/docs/",
        "link_prefix": "/docs/",
        "max_pages": 50,
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def html_to_markdown(html_content: str, url: str) -> str:
    """将 HTML 转换为 Markdown（轻量实现，不依赖额外库）"""
    from html.parser import HTMLParser

    class MarkdownConverter(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
            self.current_tag = None
            self.tag_stack = []
            self.in_code = False
            self.code_lang = ""
            self.skip_tags = {"script", "style", "nav", "footer", "header", "noscript", "svg"}
            self.skip_depth = 0

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag in self.skip_tags:
                self.skip_depth += 1
                return
            if self.skip_depth > 0:
                return

            self.tag_stack.append(tag)
            self.current_tag = tag

            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag[1])
                self.result.append("\n" + "#" * level + " ")
            elif tag == "p":
                self.result.append("\n\n")
            elif tag == "br":
                self.result.append("\n")
            elif tag == "pre":
                lang = attrs_dict.get("class", "")
                if "language-" in lang:
                    self.code_lang = lang.split("language-")[-1].split()[0]
                else:
                    self.code_lang = ""
                self.in_code = True
                self.result.append(f"\n```{self.code_lang}\n")
            elif tag == "code" and not self.in_code:
                self.result.append("`")
            elif tag == "li":
                self.result.append("\n- ")
            elif tag == "a":
                href = attrs_dict.get("href", "")
                if href and not href.startswith("#"):
                    self.result.append("[")
            elif tag == "strong" or tag == "b":
                self.result.append("**")
            elif tag == "em" or tag == "i":
                self.result.append("*")
            elif tag == "table":
                self.result.append("\n\n")
            elif tag == "tr":
                self.result.append("| ")
            elif tag in ("td", "th"):
                pass

        def handle_endtag(self, tag):
            if tag in self.skip_tags:
                self.skip_depth = max(0, self.skip_depth - 1)
                return
            if self.skip_depth > 0:
                return

            if self.tag_stack and self.tag_stack[-1] == tag:
                self.tag_stack.pop()

            if tag == "pre":
                self.in_code = False
                self.result.append("\n```\n")
            elif tag == "code" and not self.in_code:
                self.result.append("`")
            elif tag in ("strong", "b"):
                self.result.append("**")
            elif tag in ("em", "i"):
                self.result.append("*")
            elif tag == "a":
                self.result.append("]")
            elif tag in ("td", "th"):
                self.result.append(" | ")
            elif tag == "tr":
                self.result.append("\n")

        def handle_data(self, data):
            if self.skip_depth > 0:
                return
            text = data
            if not self.in_code:
                text = re.sub(r'\s+', ' ', text)
            self.result.append(text)

        def get_markdown(self):
            md = "".join(self.result)
            md = re.sub(r'\n{3,}', '\n\n', md)
            return md.strip()

    try:
        converter = MarkdownConverter()
        converter.feed(html_content)
        md = converter.get_markdown()

        # 在文件头部添加来源信息
        source_header = f"<!-- 来源: {url} -->\n\n"
        return source_header + md
    except Exception:
        return f"<!-- 来源: {url} -->\n\n解析失败"


def fetch_page(url: str, session: requests.Session, retries: int = 3) -> str | None:
    """获取页面 HTML 内容（带重试）"""
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))
            else:
                print(f"  [FAIL] {urlparse(url).path}")
                return None


def discover_links(html: str, base_url: str, link_prefix: str) -> list[str]:
    """从 HTML 中发现子页面链接"""
    links = set()
    base_domain = urlparse(base_url).netloc

    for match in re.finditer(r'href=["\']([^"\']+)["\']', html):
        href = match.group(1)
        full_url = urljoin(base_url, href)

        parsed = urlparse(full_url)
        # 只保留同域名、匹配前缀、非锚点的链接
        if (parsed.netloc == base_domain
                and link_prefix in parsed.path
                and not parsed.fragment
                and not full_url.endswith(('.zip', '.tar.gz', '.png', '.jpg', '.svg'))
                and full_url not in links):
            links.add(full_url)

    return list(links)


def sanitize_filename(url: str) -> str:
    """将 URL 转为安全文件名"""
    parsed = urlparse(url)
    path = parsed.path.strip('/').replace('/', '_')
    if not path:
        path = hashlib.md5(url.encode()).hexdigest()[:12]
    # 清理非法字符
    path = re.sub(r'[<>:"|?*]', '_', path)
    if len(path) > 120:
        path = path[:120]
    return path + ".md"


def crawl_source(source_key: str, source_config: dict, output_dir: str,
                 max_pages: int | None = None, depth: int = 2) -> int:
    """抓取一个文档源

    Args:
        source_key: 源标识
        source_config: 源配置
        output_dir: 输出目录
        max_pages: 最大页面数（覆盖配置）
        depth: 爬取深度（1=只抓首页链接，2=两层链接）

    Returns:
        抓取的页面数
    """
    name = source_config["name"]
    base_url = source_config["base_url"]
    link_prefix = source_config["link_prefix"]
    limit = max_pages or source_config.get("max_pages", 50)

    print(f"\n{'='*50}")
    print(f"抓取: {name}")
    print(f"起始: {base_url}")
    print(f"上限: {limit} 页")
    print(f"{'='*50}")

    session = requests.Session()
    visited = set()
    all_links = []

    # 第一层：获取起始页，发现链接
    print(f"\n[1/{depth}] 发现链接...")
    html = fetch_page(base_url, session)
    if not html:
        print("  [FAIL] start page, skip")
        return 0

    links = discover_links(html, base_url, link_prefix)
    print(f"  发现 {len(links)} 个链接")

    # 第二层：获取子页面，发现更多链接
    if depth >= 2:
        print(f"\n[2/{depth}] 深度发现...")
        deeper_links = set()
        for link in links[:20]:  # 只从前 20 个链接深入
            sub_html = fetch_page(link, session)
            if sub_html:
                sub_links = discover_links(sub_html, base_url, link_prefix)
                deeper_links.update(sub_links)
            time.sleep(0.2)
        links = list(set(links) | deeper_links)
        print(f"  深度发现后共 {len(links)} 个链接")

    # 去重并限制数量
    all_links = list(set(links))[:limit]

    # 抓取并转换
    count = 0
    for i, url in enumerate(all_links):
        if url in visited:
            continue
        visited.add(url)

        print(f"  [{i+1}/{len(all_links)}] {urlparse(url).path}")

        html = fetch_page(url, session)
        if not html:
            continue

        md = html_to_markdown(html, url)

        # 跳过内容太少的页面
        if len(md) < 100:
            continue

        filename = sanitize_filename(url)
        filepath = os.path.join(output_dir, filename)

        # 去重：同名文件跳过
        if os.path.exists(filepath):
            continue

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        count += 1
        time.sleep(0.3)  # 礼貌延迟

    print(f"\n[OK] {name}: {count} pages")
    return count


def main():
    parser = argparse.ArgumentParser(description="批量抓取技术文档")
    parser.add_argument(
        "--source",
        choices=list(DOC_SOURCES.keys()) + ["all"],
        default="all",
        help="指定抓取源 (default: all)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="每个源最多抓取的页面数"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/knowledge-base",
        help="输出目录 (default: ./data/knowledge-base)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="爬取深度 (default: 2)"
    )
    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(args.output, exist_ok=True)

    # 确定要抓取的源
    if args.source == "all":
        sources = DOC_SOURCES
    else:
        sources = {args.source: DOC_SOURCES[args.source]}

    total = 0
    for key, config in sources.items():
        count = crawl_source(
            key, config, args.output,
            max_pages=args.max_pages,
            depth=args.depth
        )
        total += count

    print(f"\n{'='*50}")
    print(f"Done! {total} pages fetched")
    print(f"Output: {args.output}")
    print(f"\n[INFO] Next: rebuild index")
    print(f"  python backend/scripts/rebuild_index.py")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
