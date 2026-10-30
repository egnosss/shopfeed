"""카페24 기반 쇼핑몰 상품 수집기 (1단계).

shops.json에 적힌 몰의 상품 목록 페이지를 돌며 상품 정보를 products.json으로 저장한다.
"""
import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from classify import classify

HERE = Path(__file__).parent
HEADERS = {"User-Agent": "Mozilla/5.0 (personal shopfeed collector)"}
DELAY_SEC = 1.0  # 몰 서버 부담을 줄이려는 페이지 간 대기
NEW_DAYS = 3  # 처음 발견한 뒤 며칠 동안 "신상"으로 표시할지


def abs_url(base, src):
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return base + src
    return src


def parse_archive(html, shop):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("ul.prdList > li[id^=anchorBoxId_]"):
        no = li["id"].replace("anchorBoxId_", "")

        name_el = li.select_one(".description .name")
        price_el = li.select_one(".spec .item_content[rel='판매가']")
        img_el = li.select_one("img.thumb_Img")
        soldout_el = li.select_one(".soldout_area")

        name = name_el.get_text(strip=True) if name_el else ""
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = int(re.sub(r"[^\d]", "", price_text) or 0)
        image = abs_url(shop["base_url"], img_el["src"]) if img_el else ""
        # soldout_area 가 displaynone 이 아니면 품절 표시가 켜진 상태
        soldout = bool(soldout_el and "displaynone" not in soldout_el.get("class", []))

        items.append({
            "shop_id": shop["id"],
            "shop_name": shop["name"],
            "product_no": int(no),
            "name": name,
            "price": price,
            "image": image,
            "url": f"{shop['base_url']}/product/detail.html?product_no={no}",
            "soldout": soldout,
        })
    return items


def parse_thoughts(html, shop):
    """thoughts.ai.kr 형식: 상품 li 에 id만 있고, 판매가는 .ico_sale1, 링크는 한글 경로 주소."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("ul.prdList > li[id^=anchorBoxId_]"):
        no = li["id"].replace("anchorBoxId_", "")

        link_el = li.select_one(".thumbnail a[href]")
        name_el = li.select_one(".description .name")
        img_el = li.select_one("img.thumbs")
        sale_el = li.select_one(".ico_sale1")
        orig_el = li.select_one(".sale s")

        def won(el):
            return int(re.sub(r"[^\d]", "", el.get_text().split("(")[0]) or 0) if el else 0

        sale_price = won(sale_el)
        original = won(orig_el)
        price = sale_price or original  # 할인이 없는 상품은 정가가 판매가
        soldout = bool(li.select_one("img[alt*='품절'], img[src*='soldout']"))

        items.append({
            "shop_id": shop["id"],
            "shop_name": shop["name"],
            "product_no": int(no),
            "name": name_el.get_text(strip=True) if name_el else "",
            "price": price,
            "original_price": original if sale_price and original > sale_price else None,
            "image": abs_url(shop["base_url"], img_el["src"]) if img_el else "",
            "url": abs_url(shop["base_url"], link_el["href"]) if link_el else "",
            "soldout": soldout,
        })
    return items


def parse_reove(html, shop):
    """reove.kr 형식(카페24 스킨): 이름은 .name 안의 title 아닌 span, 가격은 li.product_price, 정가는 li.product_custom."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("ul.prdList > li[id^=anchorBoxId_]"):
        no = li["id"].replace("anchorBoxId_", "")

        name_el = li.select_one(".description .name a")
        img_el = li.select_one(".thumbnail img[id^=eListPrdImage]")
        sale_el = li.select_one("li.product_price")
        orig_el = li.select_one("li.product_custom")

        def won(el):
            m = re.search(r"([\d,]+)\s*원", el.get_text()) if el else None
            return int(m.group(1).replace(",", "")) if m else 0

        name = ""
        if name_el:
            for t in name_el.select(".title"):
                t.decompose()
            name = name_el.get_text(strip=True)
        sale_price = won(sale_el)
        original = won(orig_el)
        soldout = bool(li.select_one(".soldout_icon img, img[alt*='품절']"))

        items.append({
            "shop_id": shop["id"],
            "shop_name": shop["name"],
            "product_no": int(no),
            "name": name,
            "price": sale_price or original,
            "original_price": original if sale_price and original > sale_price else None,
            "image": abs_url(shop["base_url"], img_el["src"]) if img_el else "",
            "url": f"{shop['base_url']}/product/detail.html?product_no={no}",
            "soldout": soldout,
        })
    return items


def parse_roysbrown(html, shop):
    """roysbrown.com 형식: 이름은 strong.name, 가격은 .description 안의 판매가/소비자가 li(위쪽 .description3 는 숨김 사본)."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("ul.prdList > li[id^=anchorBoxId_]"):
        no = li["id"].replace("anchorBoxId_", "")

        name_el = li.select_one(".description .name a")
        img_el = li.select_one(".prdImg img")
        link_el = li.select_one(".prdImg a[href]")
        sale_el = li.select_one(".description li[rel='판매가']")
        orig_el = li.select_one(".description li[rel='소비자가']")

        def won(el):
            return int(re.sub(r"[^\d]", "", el.get_text().replace("원", " ").split("(")[0]) or 0) if el else 0

        sale_price = won(sale_el)
        original = won(orig_el)
        soldout = bool(li.select_one("img[alt*='품절'], img[src*='soldout'], img[src*='sold_out']"))

        items.append({
            "shop_id": shop["id"],
            "shop_name": shop["name"],
            "product_no": int(no),
            "name": name_el.get_text(strip=True) if name_el else "",
            "price": sale_price or original,
            "original_price": original if sale_price and original > sale_price else None,
            "image": abs_url(shop["base_url"], img_el["src"]) if img_el else "",
            "url": abs_url(shop["base_url"], link_el["href"]) if link_el else "",
            "soldout": soldout,
        })
    return items


PARSERS = {"archive": parse_archive, "thoughts": parse_thoughts, "reove": parse_reove, "roysbrown": parse_roysbrown}


MAX_PAGES_DEFAULT = 100  # 끝을 못 찾는 경우를 막는 안전장치. 몰이 끝 페이지를 주면 그 전에 멈춘다


def fetch(url, tries=3):
    for attempt in range(1, tries + 1):
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            res.raise_for_status()
            return res.text
        except requests.RequestException:
            if attempt == tries:
                raise
            time.sleep(2 * attempt)


def collect_shop(shop):
    """list_paths(없으면 list_path)에 적힌 목록을 끝 페이지까지 모두 읽는다. 상품이 겹치면 한 번만 담는다."""
    parse = PARSERS[shop.get("parser", "archive")]
    paths = shop.get("list_paths") or [shop["list_path"]]
    limit = shop.get("max_pages") or MAX_PAGES_DEFAULT
    products, seen = [], set()
    for path in paths:
        before = len(products)
        for page in range(1, limit + 1):
            html = fetch(f"{shop['base_url']}{path}&page={page}")
            items = [p for p in parse(html, shop) if p["product_no"] not in seen]
            if not items:
                break
            for p in items:
                seen.add(p["product_no"])
            products.extend(items)
            time.sleep(DELAY_SEC)
        print(f"  {shop['name']} {path}: {len(products) - before}개 (페이지 {page - 1 if not items else page})")
    return products


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def mark_new(products, shop_id, seen, today):
    """seen: {product_no: 처음 본 날짜}. 이 몰을 처음 수집하는 날은 기준선만 만들고 신상 표시는 하지 않는다."""
    first_run = shop_id not in seen
    shop_seen = seen.setdefault(shop_id, {})
    for p in products:
        key = str(p["product_no"])
        if key not in shop_seen:
            shop_seen[key] = None if first_run else today.isoformat()
        first_seen = shop_seen[key]
        p["first_seen"] = first_seen
        p["is_new"] = bool(
            first_seen and (today - date.fromisoformat(first_seen)).days < NEW_DAYS
        )


def main():
    shops = json.loads((HERE / "shops.json").read_text(encoding="utf-8"))
    seen = load_json(HERE / "seen.json", {})
    previous = load_json(HERE / "products.json", {})
    previous = previous["products"] if isinstance(previous, dict) else previous
    today = datetime.now(timezone(timedelta(hours=9))).date()  # 한국 날짜 기준

    all_products = []
    for shop in shops:
        print(f"[{shop['name']}] 수집 시작")
        try:
            items = collect_shop(shop)
            if not items:
                raise RuntimeError("상품을 하나도 못 읽음 (페이지 구조 변경 의심)")
            mark_new(items, shop["id"], seen, today)
            all_products.extend(items)
        except Exception as e:  # 한 몰이 실패해도 나머지는 계속, 실패한 몰은 이전 결과 유지
            print(f"  실패: {e}", file=sys.stderr)
            all_products.extend(p for p in previous if p["shop_id"] == shop["id"])

    for p in all_products:
        p["category"] = classify(p["name"])  # 이전 결과를 유지한 몰의 상품도 같은 규칙으로 다시 분류

    (HERE / "seen.json").write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
    out = HERE / "products.json"
    payload = {"collected": today.isoformat(), "products": all_products}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    new_count = sum(p["is_new"] for p in all_products)
    print(f"총 {len(all_products)}개 저장 (신상 {new_count}개) -> {out}")


if __name__ == "__main__":
    main()
