import os
import sys

# script/ 실행 시 stdlib keyword 모듈 가림 방지
_script_dir = os.path.dirname(os.path.abspath(__file__))
if sys.path and os.path.abspath(sys.path[0]) == _script_dir:
    sys.path.pop(0)

import re
import sqlite3
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, _script_dir)
from collect import ETF_DATA_DIR, ETF_LABEL_DATA_DIR

SCRIPT_DIR = Path(__file__).parent
SQLITE_DIR = (SCRIPT_DIR / "../docs/sqlite").resolve()
LABEL_DB_PATH = SQLITE_DIR / "kr_etf_lable.db"
ETF_LIST_CSV = ETF_LABEL_DATA_DIR / "etf_list.csv"

PRICE_COLUMNS = ["날짜", "종가", "전일비", "시가", "고가", "저가", "거래량"]
CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
SHARD_DIVISOR = 100_000


def validate_code(code: str) -> str:
    """종목 코드가 안전한 SQL 식별자인지 확인."""
    if not CODE_PATTERN.match(code):
        raise ValueError(f"유효하지 않은 종목 코드: {code}")
    return code


def quote_table(code: str) -> str:
    """숫자로 시작하는 종목 코드를 SQLite 테이블명으로 변환."""
    return f'"{validate_code(code)}"'


def code_to_shard(code: str) -> int:
    """종목 코드를 100000으로 나눈 몫으로 DB 샤드 번호를 반환."""
    validate_code(code)
    if code.isdigit():
        return int(code) // SHARD_DIVISOR

    match = re.match(r"^(\d+)", code)
    if not match:
        raise ValueError(f"샤드 계산 불가 종목 코드: {code}")
    return int(match.group(1)) // SHARD_DIVISOR


def get_etf_db_path(code: str) -> Path:
    """종목 코드에 해당하는 ETF 시세 DB 경로를 반환."""
    shard = code_to_shard(code)
    return SQLITE_DIR / f"kr_etf_sqlite_{shard:02d}.db"


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def build_etf_list(conn: sqlite3.Connection, csv_path: Path = ETF_LIST_CSV) -> int:
    """etf_list.csv를 읽어 etf_list(CODE, NAME) 테이블을 생성."""
    df = pd.read_csv(csv_path)
    df = df.rename(columns={"Code": "CODE", "Name": "NAME"})
    df["CODE"] = df["CODE"].astype(str)
    df["NAME"] = df["NAME"].astype(str)

    conn.execute("DROP TABLE IF EXISTS etf_list")
    conn.execute(
        """
        CREATE TABLE etf_list (
            CODE TEXT PRIMARY KEY,
            NAME TEXT NOT NULL
        )
        """
    )
    df[["CODE", "NAME"]].to_sql("etf_list", conn, if_exists="append", index=False)
    conn.commit()
    return len(df)


def upsert_etf_prices(conn: sqlite3.Connection, code: str, csv_path: Path) -> int:
    """종목 CSV를 읽어 코드명 테이블에 반영 (날짜 기준 upsert)."""
    validate_code(code)
    df = pd.read_csv(csv_path)

    missing = [col for col in PRICE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{csv_path.name}: 필수 컬럼 누락 {missing}")

    df = df[PRICE_COLUMNS].copy()
    df = df.drop_duplicates(subset=["날짜"], keep="first")
    df = df.sort_values("날짜", ascending=False).reset_index(drop=True)

    table = quote_table(code)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            날짜 TEXT PRIMARY KEY,
            종가 INTEGER,
            전일비 INTEGER,
            시가 INTEGER,
            고가 INTEGER,
            저가 INTEGER,
            거래량 INTEGER
        )
        """
    )

    rows = [
        (
            row["날짜"],
            row["종가"],
            row["전일비"],
            row["시가"],
            row["고가"],
            row["저가"],
            row["거래량"],
        )
        for _, row in df.iterrows()
    ]
    conn.executemany(
        f"""
        INSERT OR REPLACE INTO {table}
        (날짜, 종가, 전일비, 시가, 고가, 저가, 거래량)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def build_all_etf_prices(data_dir: Path = ETF_DATA_DIR) -> tuple[list[Path], int, int]:
    """docs/etf_data 내 모든 CSV를 샤드별 DB의 종목 테이블로 적재."""
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        return [], 0, 0

    by_shard: dict[int, list[tuple[str, Path]]] = defaultdict(list)
    for csv_path in csv_files:
        code = csv_path.stem
        by_shard[code_to_shard(code)].append((code, csv_path))

    db_paths: list[Path] = []
    total_rows = 0
    total_tables = 0

    for shard in sorted(by_shard):
        db_path = SQLITE_DIR / f"kr_etf_sqlite_{shard:02d}.db"
        db_paths.append(db_path)
        items = by_shard[shard]
        print(f"  [{db_path.name}] {len(items)}개 종목")

        with get_connection(db_path) as conn:
            for code, csv_path in items:
                row_count = upsert_etf_prices(conn, code, csv_path)
                total_rows += row_count
                total_tables += 1
                print(f"    {code}: {row_count}행")

    return db_paths, total_tables, total_rows


def build_database(
    label_db_path: Path = LABEL_DB_PATH,
    etf_list_csv: Path = ETF_LIST_CSV,
    data_dir: Path = ETF_DATA_DIR,
) -> tuple[Path, list[Path]]:
    """CSV 데이터를 읽어 label DB와 샤드별 ETF 시세 DB를 생성/갱신."""
    print(f"Label DB 경로: {label_db_path}")
    with get_connection(label_db_path) as conn:
        list_count = build_etf_list(conn, etf_list_csv)
        print(f"etf_list: {list_count}건")

    print("종목별 시세 테이블 적재:")
    etf_db_paths, table_count, row_count = build_all_etf_prices(data_dir)
    print(f"완료: {table_count}개 테이블, 총 {row_count}행, DB {len(etf_db_paths)}개")

    return label_db_path, etf_db_paths


if __name__ == "__main__":
    label_db, etf_dbs = build_database()
    print(f"Label DB 저장: {label_db}")
    for db_path in etf_dbs:
        print(f"ETF DB 저장: {db_path}")
