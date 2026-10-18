import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 1. Cấu hình InfluxDB 
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com" 
INFLUX_TOKEN = "5xZeUpfIIJ-pOlfpx7Xc8cmqOuKHlOlVXEEd5OUsUZ48dEE4ASvA1HsM3CP_0aSBajNOC8wQ4qCAZU-qHi4K0g=="
INFLUX_ORG = "ptit" 
INFLUX_BUCKET = "iot_data"

db_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = db_client.write_api(write_options=SYNCHRONOUS)

# 2. Cấu hình MQTT Broker
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "ptit/b23dccn099/iot/sensor_data"

def on_connect(client, userdata, flags, rc):
    print("Đã kết nối tới HiveMQ! Đang chờ dữ liệu từ Wokwi...")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        temp = payload.get("temperature")
        hum = payload.get("humidity")
        dist = payload.get("distance_cm")
        rssi = payload.get("rssi")         
        seq = payload.get("sequence")      
        device_id = payload.get("device_id")
        
        if temp is not None:
            print(f"📥 Nhận: Nhiệt={temp}°C, Ẩm={hum}%, Khoảng cách={dist}cm, RSSI={rssi}, Seq={seq}")
            
          
            point = Point("sensor_dht22") \
                .tag("device_id", device_id) \
                .tag("student_id", "b23dccn099") \
                .field("temperature", float(temp)) \
                .field("humidity", float(hum)) \
                .field("distance", float(dist)) \
                .field("rssi", int(rssi) if rssi is not None else 0) \
                .field("sequence", int(seq) if seq is not None else 0)
            
            write_api.write(bucket=INFLUX_BUCKET, record=point)
    except Exception as e:
        print(f"Lỗi xử lý: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_forever()