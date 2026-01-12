import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import time

# 간단한 감성 분석 로직 (VADER 활용)
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()

st.set_page_config(page_title="AI 실시간 분석기", layout="wide")
st.title("🤖 AI 뉴스-밸류에이션 통합 분석 시스템")

sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

@st.cache_data(ttl=1800)
def fetch_ai_analysis():
    df = pd.read_csv(sheet_url)
    results = []
    status_text = st.empty()
    
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip().upper()
        status_text.text(f"📡 {ticker} 실시간 뉴스 및 지표 분석 중...")
        
        try:
            tk = yf.Ticker(ticker)
            # 1. 뉴스 데이터 가져오기 및 분석
            news = tk.news
            news_sentiment = 0
            if news:
                # 최근 3개 뉴스의 제목으로 감정 점수 평균 계산
                scores = [analyzer.polarity_scores(n['title'])['compound'] for n in news[:3]]
                news_sentiment = sum(scores) / len(scores)
            
            # 2. 기본 지표 수집
            info = tk.info
            curr = tk.history(period="1d")['Close'].iloc[-1]
            per = info.get('trailingPE', 0) or 0
            
            # 3. AI 종합 판정 로직 (뉴스 + PER)
            if per == 0:
                opinion = "판단 유보 (지표 부족)"
            elif per > 60 and news_sentiment < 0:
                opinion = "🛑 강력 매도 (고평가+악재)"
            elif per > 60 and news_sentiment >= 0:
                opinion = "⚠️ 과열 주의 (고평가+호재지속)"
            elif per < 20 and news_sentiment > 0.2:
                opinion = "✅ 강력 매수 (저평가+호재)"
            elif per < 20:
                opinion = "💰 저평가 매수 구간"
            else:
                opinion = "⚖️ 적정 가치 유지"

            # 4. 환율 반영 계산
            buy_price = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_price) / buy_price) * 100
            
            results.append({
                '종목': ticker,
                'AI 판정': opinion,
                '현재가($)': round(curr, 2),
                'PER': round(per, 2),
                '수익률(%)': round(profit_rate, 2),
                '평가금액(원)': int(curr * row['수량'] * 1450),
                '뉴스지수': "긍정" if news_sentiment > 0.1 else "부정" if news_sentiment < -0.1 else "중립"
            })
            time.sleep(1)
        except:
            continue
            
    status_text.empty()
    return pd.DataFrame(results)

data = fetch_ai_analysis()

if not data.empty:
    st.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
    
    # AI 판정 결과 요약
    st.subheader("💡 AI 실시간 종목 진단")
    for _, r in data.iterrows():
        with st.expander(f"{r['종목']} : {r['AI 판정']}"):
            st.write(f"현재 PER: {r['PER']} / 뉴스 심리: {r['뉴스지수']}")
            st.write(f"수익률: {r['수익률(%)']}%")

    st.subheader("📊 상세 데이터")
    st.dataframe(data.sort_values('수익률(%)', ascending=False), use_container_width=True)
