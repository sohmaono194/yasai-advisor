import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

# CSV読み込み
df = pd.read_csv("野菜栽培条件データ.csv")
df.columns = df.columns.str.strip()

st.title("🌱 野菜の種まき・定植カレンダー（Open-Meteo対応）")

# 地名と野菜を選択
city = st.text_input("地域名（例：東京、札幌、大阪など）")
veggie = st.selectbox("育てたい野菜を選んでください", df["野菜名"].tolist())

# 緯度経度取得（OpenWeatherMapのAPI使用）
def get_lat_lon(city_name):
    OWM_API_KEY = "593601d39e37635019eeb7ca5f49513e"
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OWM_API_KEY}"
    res = requests.get(url).json()
    if res:
        return res[0]["lat"], res[0]["lon"], res[0]["name"]
    else:
        return None, None, None

# Open-Meteo APIから14日間の天気取得
@st.cache_data(ttl=3600)
def get_openmeteo_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&forecast_days=14"
        f"&timezone=Asia%2FTokyo"
    )
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        daily = data["daily"]
        df = pd.DataFrame({
            "日付": pd.to_datetime(daily["time"]),
            "最低気温": daily["temperature_2m_min"],
            "最高気温": daily["temperature_2m_max"],
            "降水量": daily["precipitation_sum"]
        })
        return df
    else:
        st.error(f"天気データの取得に失敗しました（{response.status_code}）")
        return None

# 降水量に応じた簡易天気絵文字
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
            st.subheader(f"📅 14日間の天気と適性チェック（{name}）")

            # 14日を7日×2行で表示
            for i in range(0, min(14, len(weather_df)), 7):
                week_df = weather_df.iloc[i:i+7]
                cols = st.columns(len(week_df))
                for j, row in enumerate(week_df.itertuples(index=False)):
                    tmin = row.最低気温
                    tmax = row.最高気温
                    rain = row.降水量
                    emoji = rain_to_emoji(rain)

                    temp_ok = veg["種まき適温(最低)"] <= tmin and tmax <= veg["種まき適温(最高)"]
                    rain_ok = (
                        (veg["雨の好み"] == "好き" and rain >= 1) or
                        (veg["雨の好み"] == "普通") or
                        (veg["雨の好み"] == "嫌い" and rain == 0)
                    )
                    mark = "✅" if temp_ok and rain_ok else "❌"

                    with cols[j]:
                        st.markdown(
                            f"**{row.日付.strftime('%m/%d')}**\n"
                            f"{emoji}\n🌡 {int(tmin)}–{int(tmax)}℃\n{rain:.1f}mm\n{mark}"
                        )

            st.subheader("📊 気温と降水量グラフ（14日間）")

            # 折れ線グラフ（気温）
            temp_chart = alt.Chart(weather_df).transform_fold(
                ["最低気温", "最高気温"], as_=["種別", "気温"]
            ).mark_line(point=True).encode(
                x=alt.X("日付:T", axis=alt.Axis(format="%m/%d")),
                y="気温:Q",
                color=alt.Color("種別:N", legend=None, scale=alt.Scale(range=["blue", "red"]))
            ).properties(width=700, height=300)

            # 棒グラフ（降水量）
            rain_chart = alt.Chart(weather_df).mark_bar(size=30, color="skyblue").encode(
                x=alt.X("日付:T", axis=alt.Axis(format="%m/%d")),
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
