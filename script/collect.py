import re
from pathlib import Path
import requests
import pandas as pd
from io import StringIO

SCRIPT_DIR = Path(__file__).parent
ETF_DATA_DIR = SCRIPT_DIR / "../etf_data"
ETF_LABEL_DATA_DIR = SCRIPT_DIR / "../label_data"

def fetch_daily_prices(code: str = "360750", page: int = 1) -> pd.DataFrame:
    """
    네이버 금융 일별시세 페이지에서 날짜, 종가, 전일비, 시가, 고가, 저가, 거래량을 DataFrame으로 반환.

    Args:
        code: 종목 코드 (기본값 360750)
        page: 조회할 페이지 번호
    """
    url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # 페이지 HTML 요청
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    # 테이블을 pandas로 파싱 (첫 번째 테이블이 일별 시세)
    raw_tables = pd.read_html(StringIO(resp.text))
    if not raw_tables:
        raise ValueError("일별 시세 테이블을 찾지 못했습니다.")

    # 각 테이블에서 NaN 행 제거 후 첫 번째 테이블 사용
    tables = [tbl.dropna(how="all") for tbl in raw_tables]
    df = tables[0].dropna(how="any")
    # 컬럼명 정리
    df.columns = ["날짜", "종가", "전일비", "시가", "고가", "저가", "거래량"]

    # 숫자 컬럼 정수 변환
    num_cols = ["종가", "전일비", "시가", "고가", "저가", "거래량"]
    for col in num_cols:
        if col == "전일비":
            df[col] = df[col].apply(parse_change_to_signed_number)
        else:
            df[col] = df[col].astype(str).str.replace(",", "", regex=False).astype(float)

    return df.reset_index(drop=True)


def fetch_daily_prices_csv(code: str = "360750", page: int = 1) -> str:
    """fetch_daily_prices 결과를 CSV 문자열로 반환."""
    df = fetch_daily_prices(code=code, page=page)
    return df.to_csv(index=False)


def save_daily_prices_all_pages_csv(code: str = "360750", filename: str | None = None) -> str:
    """모든 페이지를 합쳐 하나의 CSV로 저장. 기존 파일이 있으면 중복 체크 후 추가."""
    target_dir = Path(ETF_DATA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"{code}.csv"
    
    path = target_dir / filename

    # 기존 CSV 파일이 있으면 읽기
    existing_df = None
    if path.exists():
        existing_df = pd.read_csv(path)
        print(f"기존 파일 발견: {len(existing_df)}개 행")

    last_page = get_last_page(code)
    frames = []
    
    for page in range(1, last_page + 1):
        new_df = fetch_daily_prices(code=code, page=page)
        
        # 기존 데이터와 중복 체크
        if existing_df is not None:
            # 새로 가져온 데이터의 날짜가 기존 데이터에 있는지 확인
            existing_dates = set(existing_df['날짜'].values)
            new_dates = set(new_df['날짜'].values)
            
            # 중복이 있으면 중지
            if existing_dates & new_dates:  # 교집합이 있으면 중복
                print(f"페이지 {page}에서 중복 발견. 중지합니다.")
                frames.append(new_df)
                break
        
        frames.append(new_df)
        print(f"페이지 {page}/{last_page} 완료")

    # 모든 프레임 합치기
    if frames:
        merged = pd.concat(frames, ignore_index=True)
        
        # 기존 데이터와 합치기
        if existing_df is not None:
            merged = pd.concat([existing_df, merged], ignore_index=True)
        
        # 날짜 기준으로 중복 제거 (첫 번째 항목 유지)
        merged = merged.drop_duplicates(subset=['날짜'], keep='first')
        
        # 날짜 기준으로 정렬 (최신 날짜가 위로)
        merged = merged.sort_values('날짜', ascending=False).reset_index(drop=True)
        
        merged.to_csv(path, index=False)
        print(f"저장 완료: {len(merged)}개 행 (중복 제거 후)")
    else:
        print("추가할 데이터가 없습니다.")
    
    return str(path)


def parse_change_to_signed_number(value) -> float:
    """전일비 문자열을 상승/하락 기호에 맞춰 부호가 있는 숫자로 변환."""
    text = str(value)
    if text.lower() == "nan":
        return 0.0

    sign = 1
    if any(token in text for token in ["하락", "▼", "▽", "↓", "-"]):
        sign = -1
    elif any(token in text for token in ["상승", "▲", "△", "↑", "+"]):
        sign = 1

    match = re.search(r"([\d,.]+)", text)
    if not match:
        return 0.0

    number = float(match.group(1).replace(",", ""))
    return sign * number


def get_last_page(code: str = "360750") -> int:
    """맨뒤 페이지 번호 추출."""
    url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page=1"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    match = re.search(r'page=(\d+)"[^>]*>\s*맨뒤', resp.text)
    if match:
        return int(match.group(1))
    return 1

if __name__ == "__main__":
    code = "360750"
    merged_path = save_daily_prices_all_pages_csv(code)
    print(f"merged csv saved -> {merged_path}")
