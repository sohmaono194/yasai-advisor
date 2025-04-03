import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

# APIキー
WEATHERBIT_API_KEY = "6acbf60d33334859a9be01f1d12dc4c7"
OWM_API_KEY = "593601d39e37635019eeb7ca5f49513e"

# CSV読み込み
df = pd.read_csv("野菜栽培条件データ.csv")
df.columns = df.columns.str.strip()  # 空白が入ってる列名対策

st.title("🌱 野菜の種まき・定植カレンダー（7日間天気＆進捗付き）")

# 地名と野菜を選択
location = st.text_input("地域（日本語）を入力してください（例：東京、大阪、札幌など）")
veggie = st.selectbox("育てたい野菜を選んでください", df["野菜名"].tolist())

# 地名 → 緯度経度
def get_lat_lon(city):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OWM_API_KEY}"
    res = requests.get(url).json()
    if res:
        lat = res[0]["lat"]
        lon = res[0]["lon"]
        name = res[0]["name"]
        st.info(f"📍 {city} → {name}（緯度: {lat}, 経度: {lon}）")
        return lat, lon
    else:
        st.error("地名が見つかりませんでした。市区町村で入力してください。")
        return None, None

# 緯度経度 → 天気予報取得（Weatherbit）
def get_weather(lat, lon):
    url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={lat}&lon={lon}&lang=ja&key={WEATHERBIT_API_KEY}"
    res = requests.get(url)
    data = res.json()
    return data.get("data", []) if "data" in data else []

# 絵文字変換
def weather_to_emoji(desc):
    if "雨" in desc:
        return "🌧️"
    elif "曇" in desc:
        return "☁️"
    elif "晴" in desc:
        return "☀️"
    elif "雪" in desc:
        return "❄️"
    else:
        return "🌤️"

# メイン処理
if location and veggie:
    lat, lon = get_lat_lon(location)
    if lat is not None:
        weather_data = get_weather(lat, lon)
        if weather_data:
            veg = df[df["野菜名"] == veggie].iloc[0]
            st.subheader(f"🗓️ 今後7日間の適性カレンダー（{location}）")
            
            # カレンダー表示
            cols = st.columns(7)
            for i in range(7):
                day = weather_data[i]
                date = day["datetime"]
                tmin = day["min_temp"]
                tmax = day["max_temp"]
                rain = day["precip"]
                desc = day["weather"]["description"]
                emoji = weather_to_emoji(desc)

                temp_ok = veg["種まき適温(最低)"] <= tmin and tmax <= veg["種まき適温(最高)"]
                rain_ok = (
                    (veg["雨の好み"] == "好き" and rain >= 1) or
                    (veg["雨の好み"] == "普通") or
                    (veg["雨の好み"] == "嫌い" and rain == 0)
                )
                mark = "✅" if temp_ok and rain_ok else "❌"

                with cols[i]:
                    st.markdown(f"**{date}**\n{emoji} {desc}\n🌡 {int(tmin)}–{int(tmax)}℃\n☔ {rain:.1f}mm\n{mark}")

            # グラフ用データ
            chart_df = pd.DataFrame({
                "日付": [day["datetime"] for day in weather_data[:7]],
                "最低気温": [day["min_temp"] for day in weather_data[:7]],
                "最高気温": [day["max_temp"] for day in weather_data[:7]],
                "降水量": [day["precip"] for day in weather_data[:7]],
            })

            st.subheader("📊 気温と降水量グラフ（7日間）")

            # 折れ線グラフ（気温）
            temp_chart = alt.Chart(chart_df).transform_fold(
                ["最低気温", "最高気温"],
                as_=["種別", "気温"]
            ).mark_line(point=True).encode(
                  x="日付:T",
                  y="気温:Q",
                color=alt.Color("種別:N",
                    scale=alt.Scale(
                        domain=["最低気温", "最高気温"],
                        range=["blue", "red"]
                    )
                )
            ).properties(width=700, height=300)

            # 棒グラフ（降水量）
            rain_chart = alt.Chart(chart_df).mark_bar(size=30,color="skyblue").encode(
                      x="日付:T",
                      y="降水量:Q"
            ).properties(width=700, height=200)

            st.altair_chart(temp_chart)
            st.altair_chart(rain_chart)

            # ⏳ 進捗バー（定植までの日数）
            st.subheader("⏳ 発芽・定植までの進捗")

            sow_date = st.date_input("🌱 種まき日を選んでください", datetime.date.today())
            today = datetime.date.today()
            days_passed = (today - sow_date).days
            total_days = int(veg["定植までの日数"])

            progress = min(max(days_passed / total_days, 0), 1.0)
            st.progress(progress)
            st.write(f"経過日数: {max(days_passed, 0)}日 / {total_days}日")
