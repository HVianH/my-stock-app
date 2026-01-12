import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="AI 자산관리", layout="wide")

st.title("🚀 AI 자산 진단")
st.markdown("---")

# 1. 데이터 로드 (사용자님의 시트 주소)
sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

@st.cache_data(ttl=600) # 10분마다 데이터 갱신
def load_data():
    df = pd.read_csv(sheet_url)
    results = []
    for _, row in df.iterrows():
        ticker = str(row['티커']).strip()
        stock = yf.Ticker(ticker)
        info = stock.info
        curr = info.get('currentPrice', 0)
        per = info.get('trailingPE', 0)
        
        buy_krw = row['평단가_원']
        profit_rate = (((curr * 1450) - buy_krw) / buy_krw) * 100
        total_val = curr * row['수량'] * 1450
        
        results.append({
            '종목': ticker,
            '현재가($)': curr,
            'PER': per,
            '수익률(%)': round(profit_rate, 2),
            '평가금액(원)': int(total_val),
            '섹터': info.get('sector', 'N/A')
        })
    return pd.DataFrame(results)

data = load_data()

# 2. 요약 지표 (상단 대시보드)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
with col2:
    avg_profit = data['수익률(%)'].mean()
    st.metric("평균 수익률", f"{avg_profit:.2f}%")
with col3:
    st.metric("최고 수익 종목", data.loc[data['수익률(%)'].idxmax(), '종목'])

# 3. 시각화 (차트)
st.subheader("📊 섹터별 자산 비중")
fig = px.pie(data, values='평가금액(원)', names='섹터', hole=0.4)
st.plotly_chart(fig)

# 4. T-로봇의 독설 (알림창)
st.subheader("⚠️ T-로봇의 긴급 진단")
overvalued = data[data['PER'] > 50]['종목'].tolist()
if overvalued:
    st.error(f"🚨 고평가 주의보: {', '.join(overvalued)} 종목은 PER이 미쳤습니다. 거품 터지기 전에 탈출하세요.")
    
high_profit = data[data['수익률(%)'] > 50]['종목'].tolist()
if high_profit:
    st.warning(f"💰 익절 타이밍: {', '.join(high_profit)} 수익률이 50%를 넘었습니다. 세금 무서워하다 본전 옵니다.")

# 5. 상세 데이터 표
st.subheader("🔍 상세 현황")
st.dataframe(data.sort_values('수익률(%)', ascending=False), use_container_width=True)