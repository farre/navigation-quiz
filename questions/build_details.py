#!/usr/bin/env python3
"""Regenerate the <details> source block in each q*.html file.

For every q*.html, append (idempotently) a <details> showing the HTML markup
used to complete the instructions plus the page's JavaScript, both as escaped,
syntax-highlighted text. The functional markup/scripts in the file are left
untouched; only the trailing <details> block is (re)generated.
"""
import glob
import html
import os
import re
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))

KW = {
    "function", "const", "let", "var", "if", "else", "return", "null",
    "true", "false", "new", "void", "typeof", "for", "while", "do",
}

_JS_TOKEN = re.compile(r"//[^\n]*|/\*.*?\*/|\"[^\"]*\"|'[^']*'|[A-Za-z_$][\w$]*|\d+", re.S)


def hl_js(code):
    out, pos = [], 0
    for m in _JS_TOKEN.finditer(code):
        out.append(html.escape(code[pos:m.start()]))
        t = m.group()
        if t.startswith("//") or t.startswith("/*"):
            out.append('<span class="com">%s</span>' % html.escape(t))
        elif t[0] in "\"'":
            out.append('<span class="str">%s</span>' % html.escape(t))
        elif t[0].isdigit():
            out.append('<span class="num">%s</span>' % html.escape(t))
        elif t in KW:
            out.append('<span class="kw">%s</span>' % t)
        elif re.match(r"\s*\(", code[m.end():]):
            out.append('<span class="fn">%s</span>' % html.escape(t))
        else:
            out.append(html.escape(t))
        pos = m.end()
    out.append(html.escape(code[pos:]))
    return "".join(out)


def _hl_attrs(attrs):
    def repl(m):
        return '<span class="att">%s</span>=<span class="str">%s</span>' % (
            m.group(1), html.escape(m.group(2)))
    return re.sub(r'([a-zA-Z][\w-]*)=("[^"]*"|\'[^\']*\')', repl, attrs)


_TAG = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*)>")


def hl_html(markup):
    out, pos = [], 0
    for m in _TAG.finditer(markup):
        out.append(html.escape(markup[pos:m.start()]))
        out.append("&lt;%s<span class=\"tag\">%s</span>%s&gt;" % (
            m.group(1), m.group(2), _hl_attrs(m.group(3))))
        pos = m.end()
    out.append(html.escape(markup[pos:]))
    return "".join(out)


def strip_injected(text):
    text = re.sub(r'\n?<link rel="stylesheet" href="source\.css">', "", text)
    text = re.sub(r'<details class="src">.*?</details>\n?', "", text, flags=re.S)
    return text


def dedent_js(code):
    lines = code.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return textwrap.dedent("\n".join(lines))


def extract_js(text):
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.S | re.I)
    body = "\n\n".join(dedent_js(s) for s in scripts).strip()
    if body:
        return body
    # No <script>: fall back to the inline onclick handlers.
    handlers = re.findall(r'onclick="([^"]*)"', text)
    return "\n".join(handlers).strip()


def extract_markup(text):
    markup = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.S | re.I)
    markup = re.sub(r"<!--.*?-->", "", markup, flags=re.S)
    lines = []
    for line in markup.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.lower() == "<!doctype html>":
            continue
        if s.startswith("Instructions:"):
            continue
        lines.append(s)
    return "\n".join(lines)


def build_block(markup, js):
    parts = [
        '<link rel="stylesheet" href="source.css">',
        '<details class="src">',
        "  <summary>source</summary>",
        '  <div class="lbl">HTML</div>',
        "  <pre><code>%s</code></pre>" % hl_html(markup),
    ]
    if js:
        parts.append('  <div class="lbl">JavaScript</div>')
        parts.append("  <pre><code>%s</code></pre>" % hl_js(js))
    parts.append("</details>")
    return "\n".join(parts)


def main():
    for path in sorted(glob.glob(os.path.join(HERE, "q*.html"))):
        with open(path, encoding="utf-8") as f:
            original = f.read()
        base = strip_injected(original)
        markup = extract_markup(base)
        if not markup:
            continue  # nothing interactive to show
        js = extract_js(base)
        new = base.rstrip("\n") + "\n" + build_block(markup, js) + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print("updated", os.path.basename(path))


if __name__ == "__main__":
    main()
