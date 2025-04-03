# app.py
import streamlit as st
import pandas as pd
import requests
import datetime

API_KEY = "593601d39e37635019eeb7ca5f49513e"

df = pd.read_csv("野菜栽培条件データ.csv")

st.title("🌱 野菜の種まき・定植時期カレンダー")

location = st.text_input("地域を入力してください（例：東京都新宿区）")
veggie = st.selectbox("育てたい野菜を選んでください", df["野菜名"].tolist())

def get_lat_lon(place, api_key):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={place}&limit=1&appid={api_key}"
    res = requests.get(url).json()
    if res:
        return res[0]["lat"], res[0]["lon"]
    return None, None

def get_weather(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude=current,minutely,hourly,alerts&units=metric&lang=ja&appid={api_key}"
    res = requests.get(url).json()
    return res["daily"]

def weather_to_emoji(description):
    if "雨" in description:
        return "🌧️"
    elif "曇" in description:
        return "☁️"
    elif "晴" in description:
        return "☀️"
    elif "雪" in description:
        return "❄️"
    else:
        return "🌤️"

if location and veggie:
    lat, lon = get_lat_lon(location, API_KEY)
    if lat is None:
        st.error("場所が見つかりませんでした。")
    else:
        weather_data = get_weather(lat, lon, API_KEY)
        veg = df[df["野菜名"] == veggie].iloc[0]

        st.subheader(f"📅 今後7日間のカレンダー（{location}）")

        days = []
        for day in weather_data[:7]:
            date = datetime.datetime.fromtimestamp(day["dt"]).strftime('%m/%d（%a）')
            temp_min = day["temp"]["min"]
            temp_max = day["temp"]["max"]
            rain = day.get("rain", 0)
            weather = day["weather"][0]["description"]
            emoji = weather_to_emoji(weather)

            temp_ok = veg["種まき適温(最低)"] <= temp_min and temp_max <= veg["種まき適温(最高)"]
            rain_ok = (
                (veg["雨の好み"] == "好き" and rain >= 1) or
                (veg["雨の好み"] == "普通") or
                (veg["雨の好み"] == "嫌い" and rain == 0)
            )
            mark = "🟢✅" if (temp_ok and rain_ok) else "🔴❌"

            days.append(
                f"**{date}**\n{emoji} {weather}\n🌡 {int(temp_min)}–{int(temp_max)}℃\n☔ {rain}mm\n{mark}"
            )

        cols = st.columns(7)
        for i in range(7):
            with cols[i]:
                st.markdown(days[i])
