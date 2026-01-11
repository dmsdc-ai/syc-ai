---
name: plc-connector
description: |
  PLC/설비 데이터 수집 스킬.
  OPC-UA 또는 Modbus 프로토콜로 실시간 데이터를 수집합니다.
  "PLC 데이터 수집", "설비 상태 확인" 요청 시 사용.
---

## 기능

1. PLC 연결 (OPC-UA / Modbus)
2. 실시간 데이터 수집
3. InfluxDB 저장
4. 이상 감지 알림

## 사용법

```bash
# OPC-UA 연결 테스트
python scripts/connectors/opcua_client.py --test

# 데이터 수집 시작
python scripts/connectors/opcua_client.py \
  --endpoint opc.tcp://192.168.1.100:4840 \
  --interval 1000

# Modbus 모드
python scripts/connectors/modbus_client.py \
  --host 192.168.1.101 \
  --port 502
```

## 수집 데이터

### 압출기
| 태그 | 설명 | 단위 |
|------|------|------|
| ZONE1_TEMP | 1구역 온도 | °C |
| ZONE2_TEMP | 2구역 온도 | °C |
| DIE_TEMP | 다이 온도 | °C |
| SCREW_RPM | 스크류 속도 | RPM |
| LINE_SPEED | 라인 속도 | m/min |
| POWER | 전력 소비 | kW |

### 권취기
| 태그 | 설명 | 단위 |
|------|------|------|
| TENSION | 장력 | N |
| WIND_SPEED | 권취 속도 | m/min |
| ROLL_DIAMETER | 롤 직경 | mm |

## 의존성

- opcua-asyncio (OPC-UA)
- pymodbus (Modbus)
- influxdb-client
- paho-mqtt (MQTT 브릿지)

## 설정

```python
# config.py
PLC_CONFIG = {
    "protocol": "opc-ua",  # or "modbus"
    "endpoint": "opc.tcp://192.168.1.100:4840",
    "polling_interval_ms": 1000,
    "tags": [
        "ns=2;s=Extruder.Zone1Temp",
        "ns=2;s=Extruder.ScrewRPM"
    ]
}

INFLUXDB_CONFIG = {
    "url": "http://localhost:8086",
    "token": "your-token",
    "org": "syc",
    "bucket": "factory"
}
```

## 덕영 형 검토 사항

- [ ] 현재 PLC에서 OPC-UA 지원하는지?
- [ ] 안 되면 Modbus나 다른 프로토콜은?
- [ ] Raspberry Pi로 충분한지, 산업용 게이트웨이 필요한지?
- [ ] 실시간 수집 주기는 어느 정도가 적당한지?
