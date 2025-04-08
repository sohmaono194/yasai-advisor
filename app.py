import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

# CSV読み込み
df = pd.read_csv("野菜栽培条件データ.csv")
df.columns = df.columns.str.strip()

st.title("🌱 野菜の種まき・定植カレンダー（複数野菜対応）")

# 地名を入力
city = st.text_input("地域名（例：Tokyo、Osaka、Sapporoなど）")

# 複数野菜選択
selected_veggies = st.multiselect("育てたい野菜を選んでください（複数選択可）", df["野菜名"].tolist())

# 緯度経度取得（OpenWeatherMap API）
def get_lat_lon(city_name):
    OWM_API_KEY = "593601d39e37635019eeb7ca5f49513e"
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OWM_API_KEY}"
    res = requests.get(url).json()
    if res:
        return res[0]["lat"], res[0]["lon"], res[0]["name"]
    else:
        return None, None, None

# 天気データ取得（Open-Meteo）
@st.cache_data(ttl=3600)
def get_openmeteo_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_min,temperature_2m_max,precipitation_sum"
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
        return None

# 実行
if city and selected_veggies:
    lat, lon, name = get_lat_lon(city)
    if lat:
        weather_df = get_openmeteo_weather(lat, lon)
        if weather_df is not None:
            st.success(f"{name} の天気データを取得しました。")

            # 📋 判定結果を横軸＝野菜、縦軸＝日付の形式に構築
            result_dict = {"日付": weather_df["日付"].dt.strftime("%m/%d")}

            for veggie in selected_veggies:
                veg = df[df["野菜名"] == veggie].iloc[0]
                marks = []

                for row in weather_df.itertuples(index=False):
                    tmin = row.最低気温
                    tmax = row.最高気温
                    rain = row.降水量

                    temp_ok = veg["種まき適温(最低)"] <= tmin and tmax <= veg["種まき適温(最高)"]
                    rain_ok = (
                        (veg["雨の好み"] == "好き" and rain >= 1) or
                        (veg["雨の好み"] == "普通") or
                        (veg["雨の好み"] == "嫌い" and rain == 0)
                    )
                    total_ok = temp_ok and rain_ok
                    marks.append("○" if total_ok else "×")

                result_dict[veggie] = marks

            # 表として表示
            result_df = pd.DataFrame(result_dict)
            st.subheader("📋 種まき適性チェック表（横軸：野菜）")
            st.dataframe(result_df, use_container_width=True)
        else:
            st.error("天気データの取得に失敗しました。")
    else:
        st.error("地名が見つかりませんでした。英語またはローマ字で入力してください。")
