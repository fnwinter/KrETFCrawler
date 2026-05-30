import csv
import json
import re
from pathlib import Path
from typing import List

import requests

from collect import ETF_LABEL_DATA_DIR

SCRIPT_DIR = Path(__file__).parent

def fetch_etf_items(url: str | None = None) -> List[tuple[str, str]]:
    """itemname, itemcode 쌍을 반환."""
    if url is None:
        url = (
            "https://finance.naver.com/api/sise/etfItemList.nhn"
            "?etfType=0&targetColumn=market_sum&_callback=window.__jindo2_callback._7543"
        )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    text = resp.text.strip()
    match = re.search(r"\((\{.*\})\)\s*$", text)
    if not match:
        raise ValueError("JSONP 응답에서 본문을 찾지 못했습니다.")

    payload = json.loads(match.group(1))
    items = payload.get("result", {}).get("etfItemList", [])
    return [
        (item.get("itemname"), item.get("itemcode"))
        for item in items
        if "itemname" in item and "itemcode" in item
    ]


def save_etf_items_csv(filename: str = "etf_list.csv") -> str:
    """itemname, itemcode 쌍을 label_data 폴더 CSV로 저장하고 경로를 반환."""
    target_dir = Path(ETF_LABEL_DATA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    pairs = fetch_etf_items()
    # Code 기준 내림차순 정렬
    pairs = sorted(pairs, key=lambda x: x[1], reverse=False)

    path = target_dir / filename

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Code", "Name"])
        for name, code in pairs:
            writer.writerow([code, name])

    return str(path)


if __name__ == "__main__":
    output = save_etf_items_csv()
    print(f"CSV saved -> {output}")

