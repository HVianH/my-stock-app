import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import time

st.set_page_config(page_title="T-로봇 자산관리", layout="wide")
st.title("🚀 T-로봇의 냉정한 자산 진단 (안정모드)")

sheet_url = "https://docs.google.com/spreadsheets/d/1gkYeOJzu_T02sA2h01ukIT7pipvSj_iHqJMgtqKC4mk/export?format=csv"

@st.cache_data(ttl=3600) # 1시간 동안 데이터 기억 (차단 방지)
def load_data():
    df = pd.read_csv(sheet_url)
    results = []
    
    progress_bar = st.progress(0)
    total_stocks = len(df)
    
    for i, row in df.iterrows():
        ticker = str(row['티커']).strip()
        stock = yf.Ticker(ticker)
        
        # 차단 방지를 위한 약간의 휴식과 데이터 수집
        try:
            # 실시간 info 대신 history 사용 (차단 확률이 훨씬 낮음)
            hist = stock.history(period="1d")
            curr = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # PER 등 상세 정보는 에러 나면 0으로 처리
            try:
                per = stock.info.get('trailingPE', 0)
                sector = stock.info.get('sector', 'N/A')
            except:
                per, sector = 0, 'N/A'
            
            buy_krw = row['평단가_원']
            profit_rate = (((curr * 1450) - buy_krw) / buy_krw) * 100
            total_val = curr * row['수량'] * 1450
            
            results.append({
                '종목': ticker, '현재가($)': round(curr, 2), 'PER': per,
                '수익률(%)': round(profit_rate, 2), '평가금액(원)': int(total_val), '섹터': sector
            })
            time.sleep(0.5) # 야후 형님 눈치 보기 (0.5초 쉬기)
        except Exception as e:
            st.warning(f"⚠️ {ticker} 데이터를 가져오지 못했습니다.")
            
        progress_bar.progress((i + 1) / total_stocks)
        
    return pd.DataFrame(results)

try:
    data = load_data()

    # 상단 지표
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{data['평가금액(원)'].sum():,} 원")
    c2.metric("평균 수익률", f"{data['수익률(%)'].mean():.2f}%")
    c3.metric("최고 수익", data.loc[data['수익률(%)'].idxmax(), '종목'])

    # 차트와 표
    st.plotly_chart(px.pie(data, values='평가금액(원)', names='섹터', hole=0.4))
    
    st.subheader("⚠️ T-로봇의 독설 경고")
    for _, r in data.iterrows():
        if r['수익률(%)'] > 100:
            st.error(f"🚨 {r['종목']}: 수익률 {r['수익률(%)']}%? 이건 운입니다. 당장 반이라도 파세요.")
        elif r['PER'] > 50:
            st.warning(f"🧐 {r['종목']}: PER {r['PER']:.1f}. 숫자가 미쳤습니다. 거품 터지면 책임 안 집니다.")

    st.subheader("🔍 상세 리스트 (수익률 순)")
    st.dataframe(data.sort_values('수익률(%)', ascending=False), use_container_width=True)

except Exception as e:
    st.error("데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 새로고침하세요.")
