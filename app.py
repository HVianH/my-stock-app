import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# AI 감성 분석기 초기화
analyzer = SentimentIntensityAnalyzer()
API_KEY = "Emw5lXBk9txV2iOyNwWLRldmzqaLMxQm"

st.set_page_config(page_title="AI 실시간 투자 분석기", layout="wide")
st.title("🤖 AI 뉴스-밸류에이션 통합 분석 시스템 (FMP Engine)")
st.markdown("---")

# 1. 데이터 로딩 표시 (이게 보여야 정상 작동 중인 겁니다)
status_area = st.empty()
progress_bar = st.progress(0)

sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

# 섹터 한글 매핑
SECTOR_MAP = {
    'Technology': '기술주', 'Communication Services': '통신 서비스',
    'Consumer Cyclical': '경기 소비재', 'Financial Services': '금융',
    'Healthcare': '헬스케어', 'Consumer Defensive': '필수 소비재',
    'Energy': '에너지', 'Industrials': '산업재', 'Basic Materials': '기초 소재',
    'Real Estate': '부동산', 'Utilities': '유틸리티', 'Financial': '금융'
}

# 캐시 일시 해제 (디버깅을 위해 에러 확인용)
def fetch_fmp_data():
    try:
        df = pd.read_csv(sheet_url)
    except Exception as e:
        st.error(f"❌ 구글 시트를 읽을 수 없습니다: {e}")
        return pd.DataFrame()

    results = []
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip().upper()
        status_area.text(f"📡 AI 분석 중: {ticker} ({i+1}/{len(df)})")
        progress_bar.progress((i + 1) / len(df))
        
        try:
            # 주가/지표 호출
            q_res = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}").json()
            p_res = requests.get(f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}").json()
            
            # API 한도 초과 체크
            if isinstance(q_res, dict) and "Error Message" in q_res:
                st.error("⚠️ FMP API 일일 사용량을 모두 소진했습니다. 내일 다시 시도하거나 키를 확인하세요.")
                break

            if not q_res or not p_res: continue
            
            q, p = q_res[0], p_res[0]
            curr, per = q.get('price', 0), q.get('pe', 0) or 0
            sector = SECTOR_MAP.get(p.get('sector', 'N/A'), '기타/ETF')
            
            # 뉴스 분석
            n_res = requests.get(f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=3&apikey={API_KEY}").json()
            sentiment = 0
            if n_res and isinstance(n_res, list):
                scores = [analyzer.polarity_scores(n.get('title', ''))['compound'] for n in n_res]
                sentiment = sum(scores) / len(scores)
            
            # 판정 로직
            news_idx = "호재" if sentiment > 0.1 else "악재" if sentiment < -0.1 else "중립"
            if per == 0: val, op = "측정 불가", "⚖️ 판단 유보"
            elif per > 50: val, op = "⚠️ 고평가", ("🛑 강력 매도" if sentiment < 0 else "⚠️ 과열 주의")
            elif per < 20: val, op = "💰 저평가", ("✅ 강력 매수" if sentiment > 0.1 else "💰 분할 매수")
            else: val, op = "⚖️ 적정 가치", "⚖️ 보유/관망"

            results.append({
                '종목': ticker, '고/저평가': val, 'AI 판정': op,
                '현재가($)': round(curr, 2), 'PER': round(per, 2),
                '수익률(%)': round((((curr * 1450) - row['평단가_원']) / row['평단가_원']) * 100, 2),
                '평가금액(원)': int(curr * row['수량'] * 1450), '섹터': sector, '뉴스': news_idx
            })
            time.sleep(0.2)
        except: continue
            
    status_area.empty()
    progress_bar.empty()
    return pd.DataFrame(results)

# 실행
data = fetch_fmp_data()

if not data.empty:
    st.subheader("📊 포트폴리오 요약")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
    c2.metric("평균 수익률", f"{data['수익률(%)'].mean():.2f}%")
    c3.metric("최고 종목", data.loc[data['수익률(%)'].idxmax(), '종목'])
    
    st.plotly_chart(px.pie(data, values='평가금액(원)', names='섹터', hole=0.4), use_container_width=True)
    
    st.subheader("🔍 실시간 AI 종목 진단")
    st.dataframe(data.sort_values('수익률(%)', ascending=False), use_container_width=True)
else:
    st.info("데이터를 분석 중입니다. 위 진행바가 끝날 때까지 기다려 주세요. 만약 아무것도 안 뜨면 API 키 한도를 확인해야 합니다.")
