"""상품 이름만 보고 옷 종류를 나누는 규칙. 몰이 달라도 같은 규칙으로 판별한다.

위에서부터 차례로 검사하고 처음 맞는 종류로 정한다. 순서가 곧 우선순위다.
(예: "Denim Jacket" 은 데님이 있어도 자켓이 먼저 맞아서 아우터, "Sweat Pants" 는 팬츠라서 하의)
"""
import re

CATEGORIES = ["아우터", "니트·가디건", "상의", "하의", "원피스", "잡화", "기타"]


def _en(*words):
    # 영어 단어는 다른 단어 안에 들어 있는 경우(예: coated)를 피하려고 앞뒤가 알파벳이 아닐 때만 맞는 것으로 본다
    return [rf"(?<![a-z]){re.escape(w)}(?![a-z])" for w in words]


RULES = [
    ("원피스", _en("dress", "one-piece", "onepiece", "jumpsuit") + ["원피스", "드레스", "점프수트"]),
    ("아우터", _en("puffer", "padding", "jacket", "jk", "jumper", "coat", "blazer", "blouson", "parka",
                 "trench", "vest", "mustang", "duck-down", "goose-down", "down", "zip-up", "zipup", "cape")
     + ["패딩", "자켓", "재킷", "점퍼", "코트", "블레이저", "블루종", "파카", "트렌치", "베스트", "조끼",
        "무스탕", "다운", "집업", "케이프"]),
    ("니트·가디건", _en("knit", "cardigan", "pullover", "sweater") + ["니트", "가디건", "풀오버", "스웨터"]),
    ("상의", _en("tee", "t-shirt", "shirt", "blouse", "top", "sleeve", "long-sleeve", "hoodie", "sweatshirt",
               "polo", "henley", "camisole", "bustier")
     + ["티셔츠", "셔츠", "블라우스", "탑", "슬리브", "맨투맨", "후드", "카라티", "나시", "민소매", "캐미솔"]),
    ("하의", _en("pants", "pt", "denim", "jeans", "slacks", "trousers", "skirt", "shorts", "leggings", "joggers")
     + ["팬츠", "데님", "청바지", "슬랙스", "트라우저", "스커트", "치마", "쇼츠", "반바지", "레깅스", "조거"]),
    ("잡화", _en("bag", "cap", "hat", "beanie", "scarf", "muffler", "belt", "socks", "gloves", "shoes",
               "sneakers", "loafers", "boots", "sandals", "slippers", "wallet", "tote", "shoulder", "crossbody")
     + ["가방", "백", "모자", "비니", "머플러", "스카프", "목도리", "벨트", "양말", "장갑", "슈즈", "스니커즈",
        "로퍼", "부츠", "샌들", "슬리퍼", "지갑", "토트", "크로스", "주얼리", "목걸이", "귀걸이", "팔찌", "반지"]),
]
COMPILED = [(cat, re.compile("|".join(pats), re.IGNORECASE)) for cat, pats in RULES]


def classify(name):
    text = re.sub(r"\[[^\]]*\]", " ", name)  # [당일발송] 같은 말머리 제거
    text = re.sub(r"button[- ]?down", " ", text, flags=re.IGNORECASE)  # 버튼다운 셔츠가 다운(아우터)으로 잡히지 않게
    text = re.sub(r"부츠\s*컷|bootcut|boot-cut", " ", text, flags=re.IGNORECASE)  # 부츠컷 바지가 부츠(잡화)로 잡히지 않게
    for cat, rx in COMPILED:
        if rx.search(text):
            return cat
    return "기타"
