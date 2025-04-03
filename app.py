import streamlit as st
import pandas as pd
import requests
import datetime

# APIキー
WEATHERBIT_API_KEY = "6acbf60d33334859a9be01f1d12dc4c7"
OWM_API_KEY = "593601d39e37635019eeb7ca5f49513e"

# CSV読み込み
df = pd.read_csv("野菜栽培条件データ.csv")

st.title("🌱 野菜の種まき・定植カレンダー（日本語地名＋14日対応）")

# 入力フォーム
location = st.text_input("地域を日本語で入力（例：東京、札幌、大阪など）")
veggie = st.selectbox("育てたい野菜を選んでください", df["野菜名"].tolist())

# 地名→緯度経度（日本語対応）
def get_lat_lon_japanese_name(japanese_name):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={japanese_name}&limit=1&appid={OWM_API_KEY}"
    res = requests.get(url).json()
    if res:
        lat = res[0]["lat"]
        lon = res[0]["lon"]
        name = res[0]["name"]
        st.info(f"📍 入力地名: {japanese_name} → {name}（緯度: {lat}, 経度: {lon}）")
        return lat, lon
    else:
        st.error("地名が見つかりませんでした。市や区レベルで入力してみてください。")
        return None, None

# 緯度経度→Weatherbit天気
def get_weatherbit_by_latlon(lat, lon, api_key):
    url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={lat}&lon={lon}&lang=ja&key={api_key}"
    res = requests.get(url)
    if res.status_code != 200:
        st.error(f"APIエラー: {res.status_code} - {res.text}")
        return None
    data = res.json()
    return data.get("data", None)

# 天気→絵文字
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

# 実行ロジック
if location and veggie:
    lat, lon = get_lat_lon_japanese_name(location)
    if lat is not None:
        weather_data = get_weatherbit_by_latlon(lat, lon, WEATHERBIT_API_KEY)
        if weather_data:
            veg = df[df["野菜名"] == veggie].iloc[0]
            st.subheader(f"📅 今後14日間のカレンダー（{location}）")

            for row in range(2):  # 2行 × 7列
                cols = st.columns(7)
                for i in range(7):
                    index = row * 7 + i
                    if index >= len(weather_data):
                        continue
                    day = weather_data[index]
                    date = day["datetime"]
                    temp_min = day["min_temp"]
                    temp_max = day["max_temp"]
                    rain = day["precip"]
                    weather = day["weather"]["description"]
                    emoji = weather_to_emoji(weather)

                    temp_ok = veg["種まき適温(最低)"] <= temp_min and temp_max <= veg["種まき適温(最高)"]
                    rain_ok = (
                        (veg["雨の好み"] == "好き" and rain >= 1) or
                        (veg["雨の好み"] == "普通") or
                        (veg["雨の好み"] == "嫌い" and rain == 0)
                    )
                    mark = "✅" if (temp_ok and rain_ok) else "❌"

                    with cols[i]:
                        st.markdown(
                            f"**{date}**\n{emoji} {weather}\n🌡 {int(temp_min)}–{int(temp_max)}℃\n☔ {rain:.1f}mm\n{mark}"
                        )
