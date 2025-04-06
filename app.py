import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

# CSV読み込み（定植・収穫情報込み）
df = pd.read_csv("野菜栽培条件データ.csv")
df.columns = df.columns.str.strip()

st.title("🌱 野菜の種まき・定植・収穫カレンダー（統合版）")
st.caption("地植え/プランターや成長スピードに応じたアドバイスを提供します")

# サイドバー：ユーザー設定
st.sidebar.header("🩴 栽培条件の設定")
plant_type = st.sidebar.radio("栽培方法", ["地植え", "鉢・プランター"])
speed_option = st.sidebar.selectbox("定植スピード", ["早め", "普通", "遅め"])
speed_offset = {"早め": -7, "普通": 0, "遅め": 7}[speed_option]

# 地名と野菜を選択
city = st.text_input("地域名（例：Tokyo、Osaka、Sapporoなど）")
veggies = st.multiselect("育てたい野菜を最大5つ選んでください", df["野菜名"].tolist(), max_selections=5)

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
if city and veggies:
    lat, lon, name = get_lat_lon(city)
    if lat:
        weather_df = get_openmeteo_weather(lat, lon)
        if weather_df is not None:
            for veggie in veggies:
                st.header(f"🥬 {veggie} の栽培アドバイス")
                veg = df[df["野菜名"] == veggie].iloc[0]
                base_days = int(veg["定植までの日数"])
                adjusted_days = max(base_days + speed_offset, 0)
                total_days = adjusted_days

                st.info(f"📌 {veggie} の定植までの日数は {base_days} 日 → {adjusted_days} 日（{speed_option}）")

                # 適性チェック（各日）
                results = []
                temp_ok_count = 0
                rain_ok_count = 0
                both_ok_count = 0
                suitable_dates = []

                for row in weather_df.itertuples(index=False):
                    tmin = row.最低気温
                    tmax = row.最高気温
                    rain = row.降水量
                    date_str = row.日付.strftime("%m/%d")

                    temp_ok = veg["種まき適温(最低)"] <= tmin and tmax <= veg["種まき適温(最高)"]
                    rain_ok = (
                        (veg["雨の好み"] == "好き" and rain >= 1) or
                        (veg["雨の好み"] == "普通") or
                        (veg["雨の好み"] == "嫌い" and rain == 0)
                    )

                    if temp_ok: temp_ok_count += 1
                    if rain_ok: rain_ok_count += 1
                    if temp_ok and rain_ok:
                        both_ok_count += 1
                        suitable_dates.append(date_str)

                    mark = "✅" if temp_ok and rain_ok else "❌"
                    results.append((date_str, mark))

                result_df = pd.DataFrame(results, columns=["日付", "適性"])
                st.subheader("📆 種まき適性チェック（14日間）")
                st.table(result_df)

                # 判定
                st.subheader("🧠 判定：今植えても大丈夫？")
                if both_ok_count > 0:
                    st.success(f"✅ 今は植えるのに適したタイミングです！（14日中 {both_ok_count} 日）")
                    st.markdown("**理由：**")
                    st.markdown(f"- 気温が適している日数：{temp_ok_count}日")
                    st.markdown(f"- 雨が条件に合っている日数：{rain_ok_count}日")
                    st.markdown(f"- 両方条件を満たす日数：{both_ok_count}日")
                    st.markdown(f"**おすすめ日：** {', '.join(suitable_dates)}")
                else:
                    st.warning("⚠️ 今後14日間に種まきに適した日はありません。")
                    st.markdown("**理由：**")
                    if temp_ok_count == 0:
                        st.markdown("- 気温が適正範囲外です。")
                    if rain_ok_count == 0:
                        st.markdown("- 降水条件が合いません。")
                    if temp_ok_count > 0 and rain_ok_count > 0:
                        st.markdown("- 条件は別々には合うが、同時に合う日がありません。")

                # グラフ表示
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

                # 定植までの進捗
                st.subheader("⏳ 発芽・定植までの進捗")
                sow_date = st.date_input(f"🌱 {veggie} の種まき日を選んでください", datetime.date.today())
                today = datetime.date.today()
                days_passed = (today - sow_date).days
                progress = min(max(days_passed / total_days, 0), 1.0)
                planting_date = sow_date + datetime.timedelta(days=total_days)
                st.info(f"🗓️ 定植予定日：**{planting_date.strftime('%Y年%m月%d日')}**（{speed_option}）")
                st.progress(progress)
                st.write(f"経過日数: {max(days_passed, 0)}日 / {total_days}日")

                # 収穫までの進捗（CSVの統合列から）
                if pd.notna(veg["収穫基準"]) and pd.notna(veg["収穫までの日数"]):
                    basis = veg["収穫基準"]
                    harvest_days = int(veg["収穫までの日数"])
                    st.subheader("🌾 収穫までの進捗状況")
                    base_date = st.date_input(f"📅 {veggie} の{basis}日を入力してください", datetime.date.today())
                    passed = (today - base_date).days
                    progress = min(max(passed / harvest_days, 0), 1.0)
                    harvest_date = base_date + datetime.timedelta(days=harvest_days)
                    st.info(f"🌿 収穫目安日: {harvest_date.strftime('%Y年%m月%d日')}")
                    st.progress(progress)
                    st.write(f"経過日数: {passed}日 / {harvest_days}日")
        else:
            st.error("Open-Meteoから天気を取得できませんでした。")
    else:
        st.error("地名が見つかりませんでした。市区町村を英語・ローマ字で入力してください。")