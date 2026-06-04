import os
import sys

# script/keyword.py 실행 시 stdlib keyword 모듈 가림 방지
_script_dir = os.path.dirname(os.path.abspath(__file__))
if sys.path and os.path.abspath(sys.path[0]) == _script_dir:
    sys.path.pop(0)

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from wordcloud import WordCloud

sys.path.insert(0, _script_dir)
from collect import ETF_LABEL_DATA_DIR

ETF_LIST_CSV = ETF_LABEL_DATA_DIR / "etf_list.csv"
OUTPUT_IMAGE = ETF_LABEL_DATA_DIR / "etf_keyword_cloud.png"

# ETF 이름에서 매칭할 테마 키워드 (긴 키워드 우선 매칭)
THEME_KEYWORDS = sorted(
    [
        "휴머노이드로봇", "양자컴퓨팅", "전고체배터리", "2차전지", "반도체", "바이오시밀러",
        "바이오", "헬스케어", "의료", "제약", "원자력", "SMR", "전기차", "배터리",
        "AI", "인공지능", "소프트웨어", "클라우드", "데이터센터", "사이버보안",
        "로봇", "자동차", "조선", "방산", "항공", "해운", "철도", "건설", "부동산",
        "리츠", "REIT", "은행", "금융", "핀테크", "보험", "증권",
        "배당", "고배당", "커버드콜", "머니마켓", "TDF", "레버리지", "인버스",
        "채권", "국채", "회사채", "종합채권", "하이일드",
        "금", "은", "원자재", "석유", "가스", "천연가스", "에너지", "태양광", "ESS", "수소",
        "ESG", "친환경", "탄소", "전력", "전력설비",
        "게임", "엔터", "미디어", "K-POP", "화장품", "뷰티", "소비", "유통", "식품",
        "통신", "5G", "6G", "메타버스", "블록체인", "비트코인", "가상자산",
        "나스닥", "S&P500", "다우존스", "밸류체인", "성장",
        "미국", "한국", "코리아", "중국", "차이나", "일본", "인도", "베트남",
        "글로벌", "유럽", "신흥국", "선진국", "대만", "홍콩",
        "테슬라", "엔비디아", "애플", "마이크로소프트", "팔란티어", "아마존",
        "반도체장비", "디스플레이", "IT", "테크",
    ],
    key=len,
    reverse=True,
)


def load_etf_names(csv_path: Path = ETF_LIST_CSV) -> list[str]:
    """etf_list.csv에서 Name 컬럼을 읽어 반환."""
    with csv_path.open(encoding="utf-8", newline="") as f:
        return [row["Name"] for row in csv.DictReader(f) if row.get("Name")]


def classify_name(name: str, keywords: list[str] = THEME_KEYWORDS) -> list[str]:
    """ETF 이름에 포함된 키워드를 반환."""
    return [kw for kw in keywords if kw in name]


def build_keyword_lists(names: list[str]) -> tuple[dict[str, list[str]], Counter]:
    """키워드별 ETF 이름 리스트와 빈도를 생성."""
    keyword_to_names: dict[str, list[str]] = defaultdict(list)
    counts: Counter = Counter()

    for name in names:
        matched = classify_name(name)
        for kw in matched:
            keyword_to_names[kw].append(name)
            counts[kw] += 1

    return dict(keyword_to_names), counts


def find_korean_font() -> str:
    """워드클라우드용 한글 폰트 경로를 찾는다."""
    for font in font_manager.fontManager.ttflist:
        if any(token in font.name for token in ("Malgun", "Nanum", "Noto Sans CJK", "AppleGothic")):
            return font.fname

    windows_font = Path(r"C:\Windows\Fonts\malgun.ttf")
    if windows_font.exists():
        return str(windows_font)

    raise FileNotFoundError("한글 폰트를 찾지 못했습니다. malgun.ttf 또는 Nanum 폰트를 설치해 주세요.")


def generate_word_cloud(counts: Counter, output_path: Path = OUTPUT_IMAGE) -> Path:
    """키워드 빈도로 워드클라우드 이미지를 저장."""
    if not counts:
        raise ValueError("워드클라우드를 만들 키워드가 없습니다.")

    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        font_path=find_korean_font(),
    ).generate_from_frequencies(dict(counts))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    return output_path


def print_keyword_lists(keyword_to_names: dict[str, list[str]], counts: Counter) -> None:
    """키워드별 분류 결과를 출력."""
    print(f"총 ETF 수: {sum(len(v) for v in keyword_to_names.values())}건 (중복 매칭 포함)")
    print(f"키워드 수: {len(keyword_to_names)}")
    print("-" * 60)

    for kw, count in counts.most_common():
        names = keyword_to_names[kw]
        print(f"[{kw}] {count}건")
        for name in names[:5]:
            print(f"  - {name}")
        if len(names) > 5:
            print(f"  ... 외 {len(names) - 5}건")
        print()


if __name__ == "__main__":
    etf_names = load_etf_names()
    keyword_lists, keyword_counts = build_keyword_lists(etf_names)

    print_keyword_lists(keyword_lists, keyword_counts)

    output = generate_word_cloud(keyword_counts)
    print(f"워드클라우드 저장: {output}")
