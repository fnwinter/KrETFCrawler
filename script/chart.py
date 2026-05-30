import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import numpy as np
import platform

from collect import ETF_DATA_DIR, ETF_LABEL_DATA_DIR

# 한글 폰트 설정
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
else:  # Linux
    plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

SCRIPT_DIR = Path(__file__).parent
ETF_LIST_PATH = ETF_LABEL_DATA_DIR / "etf_list.csv"


def get_available_etfs():
    """etf_data 폴더에서 사용 가능한 종목 목록을 반환합니다."""
    if not ETF_DATA_DIR.exists():
        return []
    
    csv_files = list(ETF_DATA_DIR.glob("*.csv"))
    codes = [f.stem for f in csv_files]
    return sorted(codes)


def load_etf_list():
    """etf_list.csv 파일을 읽어서 종목 정보를 반환합니다."""
    if not ETF_LIST_PATH.exists():
        return pd.DataFrame(columns=['Code', 'Name'])
    
    return pd.read_csv(ETF_LIST_PATH)


def search_etf_by_keyword(keyword: str, multiple_keywords: bool = False):
    """키워드로 ETF 종목을 검색합니다.
    
    Args:
        keyword: 검색할 키워드 (쉼표로 구분된 여러 키워드 가능)
        multiple_keywords: True일 경우 쉼표로 구분된 키워드를 AND 조건으로 검색
    """
    etf_list = load_etf_list()
    if etf_list.empty:
        return []
    
    # 여러 키워드 처리
    if multiple_keywords and ',' in keyword:
        keywords = [k.strip() for k in keyword.split(',') if k.strip()]
        if not keywords:
            return []
        
        # 모든 키워드가 포함된 항목만 검색 (AND 조건)
        matched = etf_list.copy()
        for kw in keywords:
            matched = matched[matched['Name'].str.contains(kw, case=False, na=False)]
    else:
        # 단일 키워드 검색
        matched = etf_list[etf_list['Name'].str.contains(keyword, case=False, na=False)]
    
    # 데이터 파일이 실제로 존재하는지 확인
    available_codes = set(get_available_etfs())
    result = []
    for _, row in matched.iterrows():
        code = str(row['Code'])
        if code in available_codes:
            result.append((code, row['Name']))
    
    return result


def load_etf_data(code: str) -> pd.DataFrame:
    """특정 종목의 데이터를 로드합니다."""
    csv_path = ETF_DATA_DIR / f"{code}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"종목 코드 {code}에 해당하는 데이터 파일을 찾을 수 없습니다.")
    
    df = pd.read_csv(csv_path)
    # 날짜 컬럼을 datetime으로 변환
    df['날짜'] = pd.to_datetime(df['날짜'], format='%Y.%m.%d')
    return df


def filter_by_date_range(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """지정된 기간의 데이터만 필터링합니다."""
    start = pd.to_datetime(start_date, format='%Y.%m.%d')
    end = pd.to_datetime(end_date, format='%Y.%m.%d')
    
    filtered = df[(df['날짜'] >= start) & (df['날짜'] <= end)]
    return filtered.sort_values('날짜')


def plot_etf_chart(df: pd.DataFrame, code: str, title: str = None):
    """ETF 차트를 그립니다."""
    if df.empty:
        print("해당 기간에 데이터가 없습니다.")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
    
    # 날짜를 인덱스로 설정
    df_sorted = df.sort_values('날짜').set_index('날짜')
    
    # 상단 차트: 가격 정보
    ax1.plot(df_sorted.index, df_sorted['종가'], label='종가', linewidth=2, color='blue')
    ax1.plot(df_sorted.index, df_sorted['시가'], label='시가', linewidth=1, alpha=0.7, color='green')
    ax1.plot(df_sorted.index, df_sorted['고가'], label='고가', linewidth=1, alpha=0.5, color='red', linestyle='--')
    ax1.plot(df_sorted.index, df_sorted['저가'], label='저가', linewidth=1, alpha=0.5, color='orange', linestyle='--')
    
    ax1.fill_between(df_sorted.index, df_sorted['저가'], df_sorted['고가'], 
                     alpha=0.2, color='gray', label='고저가 범위')
    
    # 마지막 데이터 포인트에 종목 코드 표시
    last_date = df_sorted.index[-1]
    last_price = df_sorted['종가'].iloc[-1]
    ax1.text(last_date, last_price, f" {code}", 
            fontsize=10, color='blue', va='center', alpha=0.9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor='blue', alpha=0.7))
    
    ax1.set_ylabel('가격 (원)', fontsize=12)
    ax1.set_title(title or f'ETF 종목 {code} 차트', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 날짜 포맷 설정
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 하단 차트: 거래량
    ax2.bar(df_sorted.index, df_sorted['거래량'], alpha=0.6, color='purple', width=1)
    ax2.set_ylabel('거래량', fontsize=12)
    ax2.set_xlabel('날짜', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()


def plot_multiple_etf_comparison(etf_data_dict: dict, title: str = None):
    """여러 ETF 종목의 주가를 겹쳐서 비교하는 차트를 그립니다.
    
    Args:
        etf_data_dict: {종목코드: DataFrame} 형태의 딕셔너리
        title: 차트 제목
    """
    if not etf_data_dict:
        print("비교할 데이터가 없습니다.")
        return
    
    # 색상 팔레트 생성
    colors = plt.cm.tab10(np.linspace(0, 1, len(etf_data_dict)))
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # 각 종목의 종가를 정규화하여 비교 (첫 날 기준 100으로 설정)
    for idx, ((code, name), df) in enumerate(etf_data_dict.items()):
        df_sorted = df.sort_values('날짜').copy()
        if df_sorted.empty:
            continue
        
        # 첫 날 종가를 기준으로 정규화 (수익률 비교)
        first_price = df_sorted.iloc[0]['종가']
        if first_price > 0:
            df_sorted['normalized_price'] = (df_sorted['종가'] / first_price) * 100
            ax.plot(df_sorted['날짜'], df_sorted['normalized_price'], 
                   label=f"{code} ({name})", linewidth=2, color=colors[idx], alpha=0.8)
            
            # 마지막 데이터 포인트에 종목 이름 표시
            last_date = df_sorted['날짜'].iloc[-1]
            last_price = df_sorted['normalized_price'].iloc[-1]
            ax.text(last_date, last_price, f" {code}", 
                   fontsize=9, color=colors[idx], va='center', alpha=0.9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                            edgecolor=colors[idx], alpha=0.7))
    
    ax.set_ylabel('정규화된 가격 (첫날 기준 100)', fontsize=12)
    ax.set_xlabel('날짜', fontsize=12)
    ax.set_title(title or 'ETF 종목 비교 차트', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 날짜 포맷 설정
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()


def main():
    """메인 함수: 사용자 입력을 받아 차트를 그립니다."""
    print("\n=== ETF 차트 프로그램 ===")
    print("1. 단일 종목 차트 보기")
    print("2. 키워드로 여러 종목 비교하기")
    
    while True:
        try:
            mode = input("\n모드를 선택하세요 (1 또는 2): ").strip()
            if mode in ['1', '2']:
                break
            else:
                print("1 또는 2를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            return
    
    if mode == '1':
        # 단일 종목 차트 모드
        single_etf_mode()
    else:
        # 여러 종목 비교 모드
        multiple_etf_comparison_mode()


def single_etf_mode():
    """단일 종목 차트 모드"""
    print("\n종목 선택 방법:")
    print("1. 키워드로 검색하기")
    print("2. 종목 코드 직접 입력하기")
    
    while True:
        try:
            search_method = input("\n선택하세요 (1 또는 2): ").strip()
            if search_method in ['1', '2']:
                break
            else:
                print("1 또는 2를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            return
    
    selected_code = None
    
    if search_method == '1':
        # 키워드 검색 모드
        while True:
            try:
                keyword = input("\n검색할 키워드를 입력하세요 (예: 방산, 반도체, 미국 등): ").strip()
                if keyword:
                    break
                else:
                    print("키워드를 입력해주세요.")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                return
        
        # 키워드로 검색
        matched_etfs = search_etf_by_keyword(keyword)
        
        if not matched_etfs:
            print(f"\n'{keyword}' 키워드로 검색된 종목이 없습니다.")
            return
        
        print(f"\n=== '{keyword}' 키워드로 검색된 종목 ({len(matched_etfs)}개) ===")
        for i, (code, name) in enumerate(matched_etfs, 1):
            print(f"{i:3d}. {code} - {name}")
        
        # 종목 선택
        while True:
            try:
                selection = input("\n종목을 선택하세요 (번호 입력): ").strip()
                selected_idx = int(selection) - 1
                if 0 <= selected_idx < len(matched_etfs):
                    selected_code, selected_name = matched_etfs[selected_idx]
                    print(f"\n선택된 종목: {selected_code} - {selected_name}")
                    break
                else:
                    print(f"1부터 {len(matched_etfs)} 사이의 번호를 입력해주세요.")
            except ValueError:
                print("올바른 번호를 입력해주세요.")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                return
    else:
        # 종목 코드 직접 입력 모드
        available_codes = get_available_etfs()
        
        if not available_codes:
            print("etf_data 폴더에 데이터 파일이 없습니다.")
            return
        
        print("\n=== 사용 가능한 ETF 종목 ===")
        for i, code in enumerate(available_codes[:50], 1):
            print(f"{i:3d}. {code}")
        
        if len(available_codes) > 50:
            print(f"... 외 {len(available_codes) - 50}개 종목")
        
        # 종목 선택
        while True:
            try:
                code_input = input("\n종목 코드를 입력하세요: ").strip()
                if code_input in available_codes:
                    selected_code = code_input
                    break
                else:
                    print(f"'{code_input}'는 사용 가능한 종목이 아닙니다. 다시 입력해주세요.")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                return
    
    # 데이터 로드
    try:
        df = load_etf_data(selected_code)
        print(f"\n종목 {selected_code} 데이터 로드 완료: {len(df)}개 행")
        
        min_date = df['날짜'].min().strftime('%Y.%m.%d')
        max_date = df['날짜'].max().strftime('%Y.%m.%d')
        print(f"데이터 기간: {min_date} ~ {max_date}")
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {e}")
        return
    
    # 기간 입력
    while True:
        try:
            start_date = input(f"\n시작일을 입력하세요 (형식: YYYY.MM.DD, 예: {min_date}): ").strip()
            end_date = input(f"종료일을 입력하세요 (형식: YYYY.MM.DD, 예: {max_date}): ").strip()
            
            pd.to_datetime(start_date, format='%Y.%m.%d')
            pd.to_datetime(end_date, format='%Y.%m.%d')
            
            filtered_df = filter_by_date_range(df, start_date, end_date)
            
            if filtered_df.empty:
                print("해당 기간에 데이터가 없습니다. 다시 입력해주세요.")
                continue
            
            break
        except ValueError as e:
            print(f"날짜 형식이 올바르지 않습니다. YYYY.MM.DD 형식으로 입력해주세요. (오류: {e})")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            return
    
    title = f"ETF {selected_code} ({start_date} ~ {end_date})"
    print(f"\n차트를 그리는 중... ({len(filtered_df)}개 데이터 포인트)")
    plot_etf_chart(filtered_df, selected_code, title)


def multiple_etf_comparison_mode():
    """여러 종목 비교 모드"""
    # 키워드 입력
    while True:
        try:
            keyword = input("\n검색할 키워드를 입력하세요 (예: 방산, 반도체, 미국 등)\n쉼표로 구분하여 여러 키워드를 입력하면 AND 조건으로 검색됩니다 (예: 방산,국방): ").strip()
            if keyword:
                break
            else:
                print("키워드를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            return
    
    # 키워드로 검색 (여러 키워드 지원)
    matched_etfs = search_etf_by_keyword(keyword, multiple_keywords=True)
    
    if not matched_etfs:
        print(f"\n'{keyword}' 키워드로 검색된 종목이 없습니다.")
        return
    
    # 검색 조건 표시
    if ',' in keyword:
        keywords = [k.strip() for k in keyword.split(',') if k.strip()]
        search_condition = " AND ".join(keywords)
        print(f"\n=== '{search_condition}' (AND 조건) 키워드로 검색된 종목 ({len(matched_etfs)}개) ===")
    else:
        print(f"\n=== '{keyword}' 키워드로 검색된 종목 ({len(matched_etfs)}개) ===")
    for i, (code, name) in enumerate(matched_etfs, 1):
        print(f"{i:3d}. {code} - {name}")
    
    # 종목 선택
    print("\n비교할 종목을 선택하세요 (번호를 쉼표로 구분하여 입력, 예: 1,2,3 또는 'all' 입력 시 전체 선택):")
    while True:
        try:
            selection = input("선택: ").strip()
            
            if selection.lower() == 'all':
                selected_indices = list(range(len(matched_etfs)))
            else:
                selected_indices = [int(x.strip()) - 1 for x in selection.split(',')]
                # 유효성 검사
                if not all(0 <= idx < len(matched_etfs) for idx in selected_indices):
                    print(f"1부터 {len(matched_etfs)} 사이의 번호를 입력해주세요.")
                    continue
            
            selected_etfs = [matched_etfs[idx] for idx in selected_indices]
            break
        except (ValueError, IndexError):
            print("올바른 형식으로 입력해주세요. (예: 1,2,3)")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            return
    
    print(f"\n선택된 종목: {len(selected_etfs)}개")
    for code, name in selected_etfs:
        print(f"  - {code}: {name}")
    
    # 데이터 로드 및 1년 기간 설정
    etf_data_dict = {}
    all_min_dates = []
    all_max_dates = []
    
    for code, name in selected_etfs:
        try:
            df = load_etf_data(code)
            if not df.empty:
                etf_data_dict[(code, name)] = df
                all_min_dates.append(df['날짜'].min())
                all_max_dates.append(df['날짜'].max())
                print(f"  {code} 데이터 로드 완료: {len(df)}개 행")
        except Exception as e:
            print(f"  {code} 데이터 로드 실패: {e}")
    
    if not etf_data_dict:
        print("\n로드된 데이터가 없습니다.")
        return
    
    # 공통 기간 계산 (최근 1년)
    if all_min_dates and all_max_dates:
        common_max_date = min(all_max_dates)  # 모든 종목이 가진 가장 최근 날짜
        common_min_date = common_max_date - timedelta(days=365*5)  # 1년 전
        
        # 실제 데이터 범위 내로 조정
        actual_min_date = max(all_min_dates)
        if common_min_date < actual_min_date:
            common_min_date = actual_min_date
        
        start_date = common_min_date.strftime('%Y.%m.%d')
        end_date = common_max_date.strftime('%Y.%m.%d')
        
        print(f"\n비교 기간: {start_date} ~ {end_date} (최근 1년)")
    else:
        print("\n기간을 자동으로 설정할 수 없습니다.")
        return
    
    # 각 종목 데이터 필터링
    filtered_data_dict = {}
    for (code, name), df in etf_data_dict.items():
        filtered_df = filter_by_date_range(df, start_date, end_date)
        if not filtered_df.empty:
            filtered_data_dict[(code, name)] = filtered_df
    
    if not filtered_data_dict:
        print("\n선택한 기간에 데이터가 없습니다.")
        return
    
    # 차트 그리기
    if ',' in keyword:
        keywords = [k.strip() for k in keyword.split(',') if k.strip()]
        search_condition = " AND ".join(keywords)
        title = f"ETF 종목 비교: '{search_condition}' ({start_date} ~ {end_date})"
    else:
        title = f"ETF 종목 비교: '{keyword}' ({start_date} ~ {end_date})"
    print(f"\n차트를 그리는 중... ({len(filtered_data_dict)}개 종목)")
    plot_multiple_etf_comparison(filtered_data_dict, title)


if __name__ == "__main__":
    main()
