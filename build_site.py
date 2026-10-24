"""feed_template.html + products.json -> site/ (GitHub Pages 로 올라가는 폴더).

site/ 안의 manifest, 아이콘은 저장소에 그대로 들어 있고, 이 스크립트는 index.html 과 products.json 만 만든다.
"""
import shutil
from pathlib import Path

HERE = Path(__file__).parent
SITE = HERE / "site"

HEAD_TOP = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#EEF0EE" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111312" media="(prefers-color-scheme: dark)">
<meta name="color-scheme" content="light dark">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="모아보기">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" href="icon-192.png">
<style>
html { padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
body { margin: 0; font-size: 14px; }
img { max-width: 100%; }
[hidden] { display: none !important; }
</style>
"""


def main():
    tpl = (HERE / "feed_template.html").read_text(encoding="utf-8")
    tpl = tpl.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    tpl = tpl.replace("__DATA__", "null")

    split = tpl.index("</style>") + len("</style>")
    head_rest, body = tpl[:split], tpl[split:]
    html = HEAD_TOP + head_rest + "\n</head>\n<body>" + body + "\n</body>\n</html>\n"

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(HERE / "products.json", SITE / "products.json")
    print(f"site/index.html {len(html) / 1024:.0f}KB 생성")


if __name__ == "__main__":
    main()
