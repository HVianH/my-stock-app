import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()
API_KEY = "Emw5lXBk9txV2iOyNwWLRldmzqaLMxQm"

st.set_page_config(page_title="AI 투자 분석기 (최적화)", layout="wide")
st.title("🤖 AI 뉴스-밸류에이션 통합 분석 시스템 (FMP Bulk)")

sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

@st.cache_data(ttl=3600)
def fetch_bulk_data():
    try:
        df = pd.read_csv(sheet_url)
        tickers = ",".join(df['티커'].str.strip().str.upper().tolist())
    except: return pd.DataFrame()

    results = []
    
    # 1. 벌크 호출 (여러 종목을 한 번에 가져와서 API 낭비를 막음)
    try:
        quote_res = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{tickers}?apikey={API_KEY}").json()
        
        # API 한도 초과 시 메시지
        if isinstance(quote_res, dict) and "Error Message" in quote_res:
            st.error("⚠️ API 한도를 모두 소진했습니다. (무료 버전은 하루 250회)")
            return pd.DataFrame()

        # 데이터를 빠르게 찾기 위해 사전(Dict) 형태로 변환
        quote_dict = {q['symbol']: q for q in quote_res}
        
        for i, row in df.iterrows():
            ticker = str(row['티커']).strip().upper()
            q = quote_dict.get(ticker, {})
            
            curr = q.get('price', 0)
            per = q.get('pe', 0) or 0
            
            # 뉴스 분석 (뉴스는 벌크가 안 되므로 꼭 필요한 종목만 가져오거나 횟수 조절)
            sentiment_score = 0
            # 뉴스 호출을 줄이기 위해 평단가 대비 수익률이 높은 애들 위주로만 분석하거나 제한적으로 호출
            try:
                n_res = requests.get(f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=2&apikey={API_KEY}").json()
                if n_res and isinstance(n_res, list):
                    scores = [analyzer.polarity_scores(n.get('title', ''))['compound'] for n in n_res]
                    sentiment_score = sum(scores) / len(scores)
            except: pass

            news_label = "호재" if sentiment_score > 0.1 else "악재" if sentiment_score < -0.1 else "중립"
            buy_price = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_price) / buy_price) * 100
            
            # 판정 로직
            if per == 0: val, op = "측정 불가", "⚖️ 판단 유보"
            elif per > 55: val, op = "⚠️ 고평가", "🛑 강력 매도" if sentiment_score < 0 else "⚠️ 과열 주의"
            elif per < 20: val, op = "💰 저평가", "✅ 강력 매수" if sentiment_score > 0.1 else "💰 분할 매수"
            else: val, op = "⚖️ 적정 가치", "⚖️ 보유/관망"

            results.append({
                '종목': ticker, '고/저평가': val, 'AI 판정': op,
                '현재가($)': round(curr, 2), 'PER': round(per, 2),
                '수익률(%)': round(profit_rate, 2), '평가금액(원)': int(curr * row['수량'] * 1450),
                '뉴스지수': news_label
            })
    except Exception as e:
        st.error(f"데이터 분석 중 오류 발생: {e}")
        
    return pd.DataFrame(results)

data = fetch_bulk_data()

# (이후 출력 코드는 이전과 동일)
if not data.empty:
    st.subheader("📊 실시간 AI 종목 진단 리스트")
    st.dataframe(data.sort_values('수익률(%)', ascending=False), use_container_width=True)
