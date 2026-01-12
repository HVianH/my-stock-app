import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import time

st.set_page_config(page_title="AI 자산관리", layout="wide")
st.title("🚀 AI 자산 진단")

sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

# 섹터 한글 매핑 사전
SECTOR_KR = {
    'Technology': '기술주', 'Communication Services': '통신/서비스',
    'Consumer Cyclical': '경기소비재', 'Financial Services': '금융',
    'Healthcare': '헬스케어', 'Consumer Defensive': '필수소비재',
    'Energy': '에너지', 'Industrials': '산업재', 'Basic Materials': '기초소재',
    'Real Estate': '부동산', 'Utilities': '유틸리티', 'N/A': '기타/ETF'
}

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(sheet_url)
    results = []
    progress_bar = st.progress(0)
    
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip()
        stock = yf.Ticker(ticker)
        
        try:
            # 주가 데이터는 history로 안정적으로 가져옴
            hist = stock.history(period="1d")
            curr = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # 섹터와 PER 정보 수집 (에러 대비)
            try:
                info = stock.info
                per = info.get('trailingPE', 0)
                sector_en = info.get('sector', 'N/A')
                sector = SECTOR_KR.get(sector_en, sector_en)
            except:
                per, sector = 0, '기타/ETF'
            
            buy_krw = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_krw) / buy_krw) * 100
            total_val = int(curr * row['수량'] * 1450)
            
            results.append({
                '종목': ticker, '현재가($)': round(curr, 2), 'PER': round(per, 2),
                '수익률(%)': round(profit_rate, 2), '평가금액(원)': total_val, '섹터': sector
            })
            time.sleep(0.7) # 차단 방지를 위해 더 여유 있게 쉬기
        except:
            continue
        progress_bar.progress((i + 1) / len(df))
    return pd.DataFrame(results)

try:
    data = load_data()

    # 상단 지표 (천단위 쉼표 적용)
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
    c2.metric("평균 수익률", f"{data['수익률(%)'].mean():.2f}%")
    c3.metric("최고 수익", data.loc[data['수익률(%)'].idxmax(), '종목'])

    # 섹터별 비중 차트
    st.plotly_chart(px.pie(data, values='평가금액(원)', names='섹터', hole=0.4, title="내 돈이 어디에 쏠려 있나?"))
    
    # 상세 데이터 표 (포맷팅 적용)
    st.subheader("🔍 상세 현황")
    formatted_data = data.copy()
    formatted_data = formatted_data.sort_values('수익률(%)', ascending=False)
    
    # 출력용 데이터프레임 쉼표 포맷팅
    st.dataframe(
        formatted_data.style.format({
            '평가금액(원)': '{:,}',
            '현재가($)': '{:.2f}',
            'PER': '{:.2f}',
            '수익률(%)': '{:+.2f}%'
        }), 
        use_container_width=True
    )

    # T-로봇 독설 섹션
    st.subheader("🚨 경고")
    for _, r in formatted_data.iterrows():
        if r['수익률(%)'] > 100:
            st.error(f"🔥 {r['종목']}: 수익률 {r['수익률(%)']}%... 이건 운입니다. 제발 절반은 팔아서 익절하세요!")
        elif r['PER'] > 50:
            st.warning(f"⚠️ {r['종목']}: PER {r['PER']}. 기업 가치보다 꿈이 너무 큽니다. 거품 조심하세요.")

except Exception as e:
    st.error("데이터 로드 중 차단되었습니다. 5분 뒤에 새로고침하세요.")

