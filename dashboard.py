import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import altair as alt
import time

st.set_page_config(page_title="Hệ thống Giám sát IoT", page_icon="📡", layout="wide")

st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_TOKEN = "5xZeUpfIIJ-pOlfpx7Xc8cmqOuKHlOlVXEEd5OUsUZ48dEE4ASvA1HsM3CP_0aSBajNOC8wQ4qCAZU-qHi4K0g=="
INFLUX_ORG = "ptit"
INFLUX_BUCKET = "iot_data"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

def fetch_data(time_range="-30m"):
    start_time = time.time()
    query = f'''
    from(bucket:"{INFLUX_BUCKET}") 
      |> range(start: {time_range}) 
      |> filter(fn: (r) => r._measurement == "sensor_dht22") 
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    df = query_api.query_data_frame(query)
    latency = (time.time() - start_time) * 1000
    
    if not df.empty:
        df['_time'] = pd.to_datetime(df['_time'])
    return df, latency

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Logo_PTIT_University.png/320px-Logo_PTIT_University.png", width=100)
    st.title("⚙️ Tùy chỉnh Hệ thống")
    st.write("**Sinh viên:** Vũ Văn Chung")
    st.write("**Mã SV:** B23DCCN099")
    st.divider()
    time_filter = st.selectbox("⏳ Khung thời gian:", ["-15m", "-30m", "-1h", "-3h"], index=1)
    auto_refresh = st.checkbox("🔄 Cập nhật Real-time (5s)", value=True)

st.title("📊 Bảng điều khiển Giám sát Đa cảm biến IoT")
placeholder = st.empty()

while True:
    with placeholder.container():
        try:
            df, latency = fetch_data(time_filter)
            st.markdown(f"**⏱️ Độ trễ hệ thống:** `{latency:.2f} ms`")
            
            if not df.empty and 'temperature' in df.columns:
                latest = df.iloc[-1]
                
                # --- HÀNG THẺ CHỈ SỐ ---
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🌡️ Nhiệt độ", f"{latest['temperature']:.1f} °C")
                with col2:
                    st.metric("💧 Độ ẩm", f"{latest['humidity']:.1f} %")
                with col3:
                    st.metric("📏 Khoảng cách", f"{latest['distance']:.1f} cm")
                
                st.write("") 
                
                curr_rssi = latest.get('rssi', 0)
                curr_seq = latest.get('sequence', 0)
                device_name = latest.get('device_id', 'ESP32_B23DCCN099')
                
                col4, col5, col6 = st.columns(3)
                with col4:
                    st.metric("📶 Cường độ sóng (RSSI)", f"{curr_rssi:.0f} dBm", "Mạnh" if curr_rssi > -70 else "Yếu", delta_color="normal" if curr_rssi > -70 else "inverse")
                with col5:
                    st.metric("📦 Gói tin (Sequence)", f"#{curr_seq:.0f}")
                with col6:
                    st.metric("🖥️ Thiết bị hoạt động", f"{device_name}")

                st.divider()

                # --- KHU VỰC BIỂU ĐỒ (Lưới 2x2) ---
                st.subheader("📈 Phân tích Biến động Dữ liệu")
                
                # Hàng biểu đồ 1: Nhiệt độ & Độ ẩm
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    line_temp = alt.Chart(df).mark_line(color='#FF4B4B', strokeWidth=3).encode(
                        x=alt.X('_time:T', title='Thời gian'),
                        y=alt.Y('temperature:Q', title='Nhiệt độ (°C)')
                    )
                    st.altair_chart(line_temp, use_container_width=True)

                with chart_col2:
                    line_hum = alt.Chart(df).mark_area(color="lightblue", line={'color':'#118DFF'}).encode(
                        x=alt.X('_time:T', title='Thời gian'),
                        y=alt.Y('humidity:Q', title='Độ ẩm (%)', scale=alt.Scale(domain=[0, 100]))
                    )
                    st.altair_chart(line_hum, use_container_width=True)

                # Hàng biểu đồ 2: Khoảng cách & RSSI
                chart_col3, chart_col4 = st.columns(2)
                
                with chart_col3:
                    line_dist = alt.Chart(df).mark_area(color="lightgreen", line={'color':'#00C853'}).encode(
                        x=alt.X('_time:T', title='Thời gian'),
                        y=alt.Y('distance:Q', title='Khoảng cách (cm)')
                    )
                    st.altair_chart(line_dist, use_container_width=True)

                with chart_col4:
                    if 'rssi' in df.columns:
                        line_rssi = alt.Chart(df).mark_line(color='#7E57C2', strokeWidth=3).encode(
                            x=alt.X('_time:T', title='Thời gian'),
                            y=alt.Y('rssi:Q', title='RSSI (dBm)')
                        )
                        st.altair_chart(line_rssi, use_container_width=True)
                    else:
                        st.info("Chưa có dữ liệu sóng Wi-Fi (RSSI)")

                # --- BẢNG DỮ LIỆU ---
                with st.expander("📄 Xem chi tiết bảng dữ liệu thô toàn diện (Raw Data)"):
                    cols_to_show = ['_time', 'device_id', 'temperature', 'humidity', 'distance']
                    new_names = ['Thời gian', 'Mã Thiết bị', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'Khoảng cách (cm)']
                    
                    if 'rssi' in df.columns and 'sequence' in df.columns:
                        cols_to_show.extend(['rssi', 'sequence'])
                        new_names.extend(['Tín hiệu RSSI (dBm)', 'Số gói tin (Seq)'])
                        
                    df_display = df[cols_to_show].copy()
                    df_display.columns = new_names
                    st.dataframe(df_display.iloc[::-1], use_container_width=True)

            else:
                st.info("🕒 Đang đợi dữ liệu từ thiết bị...")

        except Exception as e:
            st.error(f"Lỗi truy xuất hệ thống: {e}")

    if auto_refresh:
        time.sleep(5)
    else:
        break