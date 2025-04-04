import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

# CSV読み込み
df = pd.read_csv("野菜栽培条件データ.csv")
df.columns = df.columns.str.strip()

st.title("🌱 野菜の種まき・定植カレンダー（Open-Meteo対応）")
st.caption("地植え/プランターや成長スピードに応じたアドバイスを提供します")

# サイドバー：ユーザー設定
st.sidebar.header("🪴 栽培条件の設定")
plant_type = st.sidebar.radio("栽培方法", ["地植え", "鉢・プランター"])
speed_option = st.sidebar.selectbox("定植スピード", ["早め", "普通", "遅め"])
speed_offset = {"早め": -7, "普通": 0, "遅め": 7}[speed_option]

# 地名と野菜を選択
city = st.text_input("地域名（例：Tokyo、Osaka、Sapporoなど）")
veggie = st.selectbox("育てたい野菜を選んでください", df["野菜名"].tolist())

# 緯度経度取得
def get_lat_lon(city_name):
    OWM_API_KEY = "593601d39e37635019eeb7ca5f49513e"
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OWM_API_KEY}"
    res = requests.get(url).json()
    if res:
        return res[0]["lat"], res[0]["lon"], res[0]["name"]
    else:
        return None, None, None

# Open-Meteo天気データ取得
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

# 絵文字関数
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

            # 選択された野菜のデータ取得
            veg = df[df["野菜名"] == veggie].iloc[0]

            # ✅ CSVから定植までの日数（基本）を取得してスピード調整
            base_days = int(veg["定植までの日数"])
            adjusted_days = max(base_days + speed_offset, 0)
            total_days = adjusted_days  # この変数を以降で使用

            # 日数表示
            st.info(f"📌 この野菜の基本の定植日数は {base_days} 日です。")
            st.info(f"⏱️ 選択されたスピード（{speed_option}）により、目標は **{adjusted_days} 日** になります。")

            st.subheader(f"📅 14日間の天気と適性チェック（{name}）")

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

            temp_chart = alt.Chart(weather_df).transform_fold(
                ["最低気温", "最高気温"], as_=["種別", "気温"]
            ).mark_line(point=True).encode(
                x=alt.X("日付:T", axis=alt.Axis(format="%m/%d")),
                y="気温:Q",
                color=alt.Color("種別:N", legend=None, scale=alt.Scale(range=["blue", "red"]))
            ).properties(width=700, height=300)

            rain_chart = alt.Chart(weather_df).mark_bar(size=30, color="skyblue").encode(
                x=alt.X("日付:T", axis=alt.Axis(format="%m/%d")),
                y="降水量:Q"
            ).properties(width=700, height=200)

            st.altair_chart(temp_chart)
            st.altair_chart(rain_chart)

            # ✅ 今植えるのに適しているか評価
            st.subheader("🧠 判定：今植えても大丈夫？")

            avg_temp = weather_df["最低気温"].mean() + weather_df["最高気温"].mean() / 2
            total_rain = weather_df["降水量"].sum()

            temp_ok = veg["種まき適温(最低)"] <= avg_temp <= veg["種まき適温(最高)"]
            rain_ok = (
                (veg["雨の好み"] == "好き" and total_rain >= 5) or
                (veg["雨の好み"] == "普通") or
                (veg["雨の好み"] == "嫌い" and total_rain <= 2)
            )

            if temp_ok and rain_ok:
                st.success("✅ 今は植えるのに適したタイミングです！")
                st.markdown("**理由**：")
                if temp_ok:
                    st.markdown("- 気温が適正範囲内です。")
                if rain_ok:
                    st.markdown("- 降水量も条件に合っています。")
            else:
                st.warning("⚠️ 植えるにはあまり適していない可能性があります。")
                st.markdown("**理由**：")
                if not temp_ok:
                    st.markdown("- 平均気温が適正範囲外です。")
                if not rain_ok:
                    st.markdown("- 雨の条件に合っていません。")

            # 定植予定日を自動計算して表示

            # ✅ 進捗バー
            st.subheader("⏳ 発芽・定植までの進捗")
            sow_date = st.date_input("🌱 種まき日を選んでください", datetime.date.today())
            today = datetime.date.today()
            days_passed = (today - sow_date).days
            progress = min(max(days_passed / total_days, 0), 1.0)
            planting_date = sow_date + datetime.timedelta(days=total_days)
            st.info(f"📅 定植予定日：**{planting_date.strftime('%Y年%m月%d日')}**（{speed_option}）")
            st.progress(progress)
            st.write(f"経過日数: {max(days_passed, 0)}日 / {total_days}日")


        else:
            st.error("Open-Meteoから天気を取得できませんでした。")
    else:
        st.error("地名が見つかりませんでした。市区町村を英語・ローマ字で入力してください。")
