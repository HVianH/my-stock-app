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
    df = pd.read_csv(sheet_url)
    results = []
    status_text = st.empty()
    
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip().upper()
        status_text.text(f"📡 AI가 {ticker}의 뉴스 및 지표를 정밀 분석 중...")
        
        try:
            tk = yf.Ticker(ticker)
            # 1. 뉴스 감성 분석
            news = tk.news
            sentiment_score = 0
            if news:
                scores = [analyzer.polarity_scores(n['title'])['compound'] for n in news[:3]]
                sentiment_score = sum(scores) / len(scores)
            
            # 2. 지표 수집
            info = tk.info
            hist = tk.history(period="1d")
            curr = hist['Close'].iloc[-1] if not hist.empty else 0
            per = info.get('trailingPE') or info.get('forwardPE') or 0
            sector_en = info.get('sector', 'N/A')
            sector_kr = SECTOR_MAP.get(sector_en, sector_en)
            
            # 3. AI 종합 판정 (뉴스 + PER)
            if per == 0:
                opinion = "판단 유보 (지표 부족)"
            elif per > 55 and sentiment_score < 0:
                opinion = "🛑 강력 매도 (고평가+악재)"
            elif per > 55 and sentiment_score >= 0:
                opinion = "⚠️ 과열 주의 (고평가+호재지속)"
            elif per < 25 and sentiment_score > 0.15:
                opinion = "✅ 강력 매수 (저평가+호재)"
            elif per < 25:
                opinion = "💰 저평가 매수 구간"
            else:
                opinion = "⚖️ 적정 가치 유지"

            buy_price = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_price) / buy_price) * 100
            
            results.append({
                '종목': ticker,
                'AI 판정': opinion,
                '현재가($)': round(curr, 2),
                'PER': round(per, 2),
                '수익률(%)': round(profit_rate, 2),
                '평가금액(원)': int(curr * row['수량'] * 1450),
                '섹터': sector_kr,
                '뉴스지수': "긍정" if sentiment_score > 0.1 else "부정" if sentiment_score < -0.1 else "중립"
            })
            time.sleep(1) # 차단 방지
        except:
            continue
            
    status_text.empty()
    return pd.DataFrame(results)

data = fetch_ai_analysis()

if not data.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
    c2.metric("평균 수익률", f"{data['수익률(%)'].mean():.2f}%")
    c3.metric("최고 성과", data.loc[data['수익률(%)'].idxmax(), '종목'])

    st.subheader("📊 섹터 비중 및 실시간 진단")
    st.plotly_chart(px.pie(data, values='평가금액(원)', names='섹터', hole=0.4))

    # 상세 표 출력 (AI 판정 열 포함)
    st.subheader("🔍 AI 종합 분석 리스트")
    st.dataframe(
        data.sort_values('수익률(%)', ascending=False).style.format({
            '평가금액(원)': '{:,}',
            '수익률(%)': '{:+.2f}%',
            'PER': '{:.2f}'
        }), 
        use_container_width=True
    )
