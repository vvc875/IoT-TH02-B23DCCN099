import pandas as pd
from influxdb_client import InfluxDBClient
from sklearn.preprocessing import MinMaxScaler
import warnings

# Bỏ qua các cảnh báo không quan trọng của thư viện
warnings.filterwarnings('ignore')

# Cấu hình kết nối InfluxDB
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_TOKEN = "5xZeUpfIIJ-pOlfpx7Xc8cmqOuKHlOlVXEEd5OUsUZ48dEE4ASvA1HsM3CP_0aSBajNOC8wQ4qCAZU-qHi4K0g=="
INFLUX_ORG = "ptit"
INFLUX_BUCKET = "iot_data"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

print("Đang truy vấn dữ liệu từ InfluxDB...")

# Lấy dữ liệu trong 1 giờ gần nhất
query = f'''
from(bucket:"{INFLUX_BUCKET}") 
  |> range(start: -1h) 
  |> filter(fn: (r) => r._measurement == "sensor_dht22") 
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''

try:
    df = query_api.query_data_frame(query)

    if df.empty:
        print("Chưa có dữ liệu trong database. Hãy đảm bảo Wokwi và subscriber.py đang chạy!")
    else:
        # Giữ lại các cột quan trọng
        df = df[['_time', 'temperature', 'humidity', 'distance']].copy()
        df.set_index('_time', inplace=True)

        # Bước 1: Xử lý giá trị thiếu (Dùng Forward Fill để lấy giá trị liền trước điền vào chỗ trống)
        df.ffill(inplace=True)

        # Bước 2: Phát hiện và loại bỏ điểm dị thường (Outliers) cho Nhiệt độ bằng phương pháp IQR
        Q1 = df['temperature'].quantile(0.25)
        Q3 = df['temperature'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df_clean = df[(df['temperature'] >= lower_bound) & (df['temperature'] <= upper_bound)]

        # Bước 3: Resampling (Lấy mẫu lại) - Tính trung bình các giá trị trong mỗi khoảng 1 phút
        df_resampled = df_clean.resample('1min').mean().dropna()

        # Bước 4: Chuẩn hóa dữ liệu (Min-Max Scaling) đưa các biến về thang đo [0, 1]
        scaler = MinMaxScaler()
        df_resampled[['temp_norm', 'hum_norm', 'dist_norm']] = scaler.fit_transform(
            df_resampled[['temperature', 'humidity', 'distance']]
        )
        
        print("\n✅ DỮ LIỆU SAU KHI TIỀN XỬ LÝ (5 dòng cuối):")
        print(df_resampled.tail())

except Exception as e:
    print(f"Lỗi khi xử lý dữ liệu: {e}")