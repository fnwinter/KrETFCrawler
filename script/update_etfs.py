import csv
from pathlib import Path

from collect import save_daily_prices_all_pages_csv, ETF_LABEL_DATA_DIR


def load_itemcodes_from_csv(filename: str | None = None) -> list[str]:
    """etf_list.csv에서 Code 컬럼을 읽어 itemcode 리스트 반환."""
    base_dir = Path(ETF_LABEL_DATA_DIR)
    if filename is None:
        filename = "etf_list.csv"
    path = base_dir / filename

    if not path.exists():
        raise FileNotFoundError(f"ETF 리스트 파일이 없습니다: {path}")

    codes: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("Code") or row.get("itemcode")
            if code:
                codes.append(code.strip())
    return codes


def update_all_etf_prices():
    """etf_list.csv 기준으로 모든 ETF의 일별 시세를 수집/저장."""
    codes = load_itemcodes_from_csv()
    for code in codes:
        try:
            path = save_daily_prices_all_pages_csv(code)
            print(f"{code}: saved -> {path}")
        except Exception as exc:
            print(f"{code}: 실패 ({exc})")


if __name__ == "__main__":
    update_all_etf_prices()
