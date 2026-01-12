import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# AI 감성 분석기 및 API 설정
analyzer = SentimentIntensityAnalyzer()
API_KEY = "Emw5lXBk9txV2iOyNwWLRldmzqaLMxQm" # 사용자님이 발급받은 키

st.set_page_config(page_title="AI 실시간 투자 분석기", layout="wide")
st.title("🤖 AI 뉴스-밸류에이션 통합 분석 시스템 (FMP Engine)")
st.markdown("---")

sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

# 섹터 한글 매핑
SECTOR_MAP = {
    'Technology': '기술주', 'Communication Services': '통신 서비스',
    'Consumer Cyclical': '경기 소비재', 'Financial Services': '금융',
    'Healthcare': '헬스케어', 'Consumer Defensive': '필수 소비재',
    'Energy': '에너지', 'Industrials': '산업재', 'Basic Materials': '기초 소재',
    'Real Estate': '부동산', 'Utilities': '유틸리티', 'Financial': '금융'
}

@st.cache_data(ttl=3600) # 1시간 캐시 (API 사용량 절약)
def fetch_fmp_data():
    try:
        df = pd.read_csv(sheet_url)
    except:
        return pd.DataFrame()

    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip().upper()
        status_text.text(f"📡 AI가 {ticker} 분석 중... ({i+1}/{len(df)})")
        progress_bar.progress((i + 1) / len(df))
        
        try:
            # 1. 주가 및 지표 가져오기 (Quote & Profile)
            quote_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
            
            quote_data = requests.get(quote_url).json()[0]
            profile_data = requests.get(profile_url).json()[0]
            
            curr = quote_data.get('price', 0)
            per = quote_data.get('pe', 0) or 0
            sector_en = profile_data.get('sector', '기타/ETF')
            sector_kr = SECTOR_MAP.get(sector_en, sector_en)
            
            # 2. 실시간 뉴스 가져오기 및 감성 분석
            news_url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=3&apikey={API_KEY}"
            news_data = requests.get(news_url).json()
            
            sentiment_score = 0
            if news_data:
                scores = [analyzer.polarity_scores(n.get('title', ''))['compound'] for n in news_data]
                sentiment_score = sum(scores) / len(scores)
            
            # 3. AI 종합 판정 및 고/저평가 항목 (사용자 요구사항 반영)
            news_label = "호재" if sentiment_score > 0.1 else "악재" if sentiment_score < -0.1 else "중립"
            
            if per == 0:
                opinion = "⚖️ 판단 유보 (지표 부족)"
                valuation = "측정 불가"
            elif per > 50:
                valuation = "⚠️ 고평가 영역"
                opinion = "🛑 강력 매도 권고" if sentiment_score < 0 else "⚠️ 과열 주의 (보유)"
            elif per < 20:
                valuation = "💰 저평가 영역"
                opinion = "✅ 강력 매수 추천" if sentiment_score > 0.1 else "💰 분할 매수 구간"
            else:
                valuation = "⚖️ 적정 가치"
                opinion = "⚖️ 보유 및 관망"

            # 4. 수익률 및 환율(1450원) 계산
            buy_price = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_price) / buy_price) * 100
            total_val = int(curr * row['수량'] * 1450)
            
            results.append({
                '종목': ticker,
                '고/저평가': valuation,
                'AI 판정': opinion,
                '현재가($)': round(curr, 2),
                'PER': round(per, 2),
                '수익률(%)': round(profit_rate, 2),
                '평가금액(원)': total_val,
                '섹터': sector_kr,
                '뉴스지수': news_label
            })
        except:
            continue
            
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(results)

data = fetch_fmp_data()

