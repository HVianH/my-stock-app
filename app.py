import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# AI 감성 분석기 초기화
analyzer = SentimentIntensityAnalyzer()

st.set_page_config(page_title="AI 실시간 투자 분석기", layout="wide")
st.title("🤖 AI 뉴스-밸류에이션 통합 분석 시스템")
st.markdown("---")

# 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

# 섹터 한글 매핑
SECTOR_MAP = {
    'Technology': '기술주', 'Communication Services': '통신 서비스',
    'Consumer Cyclical': '경기 소비재', 'Financial Services': '금융',
    'Healthcare': '헬스케어', 'Consumer Defensive': '필수 소비재',
    'Energy': '에너지', 'Industrials': '산업재', 'Basic Materials': '기초 소재',
    'Real Estate': '부동산', 'Utilities': '유틸리티', 'N/A': '기타/ETF'
}

@st.cache_data(ttl=1800)
def fetch_ai_analysis():
    try:
        df = pd.read_csv(sheet_url)
    except:
        return pd.DataFrame()

    results = []
    # 사용자님을 위해 진행 상황을 표시합니다
    progress_text = st.empty()
    my_bar = st.progress(0)
    
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip().upper()
        # 현재 분석 중인 종목을 화면에 실시간으로 표시
        progress_text.text(f"📡 AI가 {ticker} 분석 중... ({i+1}/{len(df)})")
        my_bar.progress((i + 1) / len(df))
        
        try:
            tk = yf.Ticker(ticker)
            news = tk.news
            sentiment_score = 0
            if news:
                scores = [analyzer.polarity_scores(n['title'])['compound'] for n in news[:3]]
                sentiment_score = sum(scores) / len(scores)
            
            info = tk.info
            hist = tk.history(period="1d")
            curr = hist['Close'].iloc[-1] if not hist.empty else 0
            per = info.get('trailingPE') or info.get('forwardPE') or 0
            sector_en = info.get('sector', 'N/A')
            sector_kr = SECTOR_MAP.get(sector_en, sector_en)
            
            # AI 판정 로직
            if per == 0: opinion = "판단 유보 (지표 부족)"
            elif per > 55 and sentiment_score < 0: opinion = "🛑 강력 매도 (고평가+악재)"
            elif per > 55 and sentiment_score >= 0: opinion = "⚠️ 과열 주의 (고평가+호재지속)"
            elif per < 25 and sentiment_score > 0.15: opinion = "✅ 강력 매수 (저평가+호재)"
            elif per < 25: opinion = "💰 저평가 매수 구간"
            else: opinion = "⚖️ 적정 가치 유지"

            buy_price = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_price) / buy_price) * 100
            
            results.append({
                '종목': ticker, 'AI 판정': opinion, '현재가($)': round(curr, 2),
                'PER': round(per, 2), '수익률(%)': round(profit_rate, 2),
                '평가금액(원)': int(curr * row['수량'] * 1450), '섹터': sector_kr,
                '뉴스지수': "긍정" if sentiment_score > 0.1 else "부정" if sentiment_score < -0.1 else "중립"
            })
            time.sleep(1) # 차단 방지를 위한 1초 휴식
        except:
            continue
            
    # 분석 완료 후 진행바 제거
    progress_text.empty()
    my_bar.empty()
    return pd.DataFrame(results)

# 데이터 실행
data = fetch_ai_analysis()

if not data.empty:
    # 상단 요약 정보
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
    c2.metric("평균 수익률", f"{data['수익률(%)'].mean():.2f}%")
    c3.metric("최고 성과", data.loc[data['수익률(%)'].idxmax(), '종목'])

    # 섹터 비중 차트
    st.subheader("📊 섹터 비중")
    st.plotly_chart(px.pie(data, values='평가금액(원)', names='섹터', hole=0.4))

    # 상세 데이터 리스트
    st.subheader
