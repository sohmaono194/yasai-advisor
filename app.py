import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

# CSV読み込み
df = pd.read_csv("野菜栽培条件データ.csv")
df.columns = df.columns.str.strip()

st.title("\U0001F331 野菜の種まき・定植カレンダー（Open-Meteo対応）")

# 地名と野菜を選択
city = st.text_input("地域名（例：東京、札幌、大阪など）")
veggie = st.selectbox("育てたい野菜を選んでください", df["野菜名"].tolist())

# 地名 → 緯度経度（OpenWeatherMapで変換）
def get_lat_lon(city_name):
    OWM_API_KEY = "593601d39e37635019eeb7ca5f49513e"
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OWM_API_KEY}"
    res = requests.get(url).json()
    if res:
        return res[0]["lat"], res[0]["lon"], res[0]["name"]
    else:
        return None, None, None

# Open-Meteo APIから天気データ取得
@st.cache_data(ttl=3600)
def get_openmeteo_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=Asia%2FTokyo"
    )
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        daily = data["daily"]
        return pd.DataFrame({
            "日付": daily["time"],
            "最低気温": daily["temperature_2m_min"],
            "最高気温": daily["temperature_2m_max"],
            "降水量": daily["precipitation_sum"]
        })
    else:
        return None

# 絵文字簡易変換（降水量に応じて）
def rain_to_emoji(rain):
    if rain == 0:
        return "☀️"
    elif rain < 5:
        return "🌤️"
    elif rain < 15:
        return "🌧️"
    else:
        return "⛈️"

# メイン処理
if city and veggie:
    lat, lon, name = get_lat_lon(city)
    if lat:
        weather_df = get_openmeteo_weather(lat, lon)
        if weather_df is not None:
            veg = df[df["野菜名"] == veggie].iloc[0]
            st.subheader(f"\U0001F5D3️ 14日間の天気と適性チェック（{name}）")

            # カレンダー表示（7日分）
            cols = st.columns(7)
            for i in range(7):
                row = weather_df.iloc[i]
                tmin = row["最低気温"]
                tmax = row["最高気温"]
                rain = row["降水量"]
                emoji = rain_to_emoji(rain)

                temp_ok = veg["種まき適温(最低)"] <= tmin and tmax <= veg["種まき適温(最高)"]
                rain_ok = (
                    (veg["雨の好み"] == "好き" and rain >= 1) or
                    (veg["雨の好み"] == "普通") or
                    (veg["雨の好み"] == "嫌い" and rain == 0)
                )
                mark = "✅" if temp_ok and rain_ok else "❌"

                with cols[i]:
                    st.markdown(
                        f"**{row['日付']}**\n"
                        f"{emoji}\n🌡 {int(tmin)}–{int(tmax)}℃\n☔ {rain:.1f}mm\n{mark}"
                    )

            st.subheader("\U0001F4CA 気温と降水量グラフ（14日間）")

            # 折れ線グラフ（気温）
            temp_chart = alt.Chart(weather_df).transform_fold(
                ["最低気温", "最高気温"], as_=["種別", "気温"]
            ).mark_line(point=True).encode(
                x="日付:T",
                y="気温:Q",
                color=alt.Color("種別:N", scale=alt.Scale(
                    domain=["最低気温", "最高気温"],
                    range=["blue", "red"]
                ))
            ).properties(width=700, height=300)

            # 棒グラフ（降水量）
            rain_chart = alt.Chart(weather_df).mark_bar(size=30, color="skyblue").encode(
                x="日付:T",
                y="降水量:Q"
            ).properties(width=700, height=200)

            st.altair_chart(temp_chart)
            st.altair_chart(rain_chart)

            # 進捗バー
            st.subheader("⏳ 発芽・定植までの進捗")
            sow_date = st.date_input("🌱 種まき日を選んでください", datetime.date.today())
            today = datetime.date.today()
            days_passed = (today - sow_date).days
            total_days = int(veg["定植までの日数"])
            progress = min(max(days_passed / total_days, 0), 1.0)
            st.progress(progress)
            st.write(f"経過日数: {max(days_passed, 0)}日 / {total_days}日")
        else:
            st.error("Open-Meteoから天気を取得できませんでした。")
    else:
        st.error("地名が見つかりませんでした。市区町村を英語・ローマ字で入力してください。")
