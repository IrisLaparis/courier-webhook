from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, re, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=42717010-0635-4e8c-a9ce-d824676db0b1"

SHEET_ID = "1QVTiudmuuWV8M-U_zfmgBzcvogBlhOejB6ELXk6GIiQ"

GOOGLE_CREDS = {
    "type": "service_account",
    "project_id": "tcgwebhook",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDAFLohukrHpTI2\nCyM2tpo0y2nVProh7qVusO+OL+/a2JUqlihS/C0E8InbGRyUKznNh+e5a1X9PyAT\n1CgRaWcSCpL3bLnram4cDcqIRxIpAV4OHRuiBZgWnEz6Bd6xMHfh7+dxezUY5vdm\nffaigMFZXf3E5pcukBq+gU+/yjfrXyCUqWTNqScQMvVc7YqkfHfLzWHzENze0FeA\nZxRV9rlgE3eNT8idA4CoKb+NvSMp1mPmTofbspG4C5hTIjCpNePQUPL3hsAvtfEa\nTnC9UTf6vqXkCELNwhDB0Irj0c63iGhIReL2oggo9eYZeSHVWl6uimHo5thJsMb0\nrmTBARSNAgMBAAECggEAAsRJqhK04QtQHdcrOq6GqhwD+j5dEAAQAfgqezHVkqFs\nBKEFE6zuORP96FoEP14gBwXeIJ2bL3qpS5/Ss+2AvpHIbCf0xZ9S1rScJjpf2Jdc\nc3eX3k2WUz0NHszW2FaKY4bBHrFXonQxPBi0ZMLWBiOEdEGeC92nhPb33xtaktlV\nil68TmKcEB3rkMjoxTJxz1hZoGMOvmekK3hl0SCz0Pe73HYHcvixbk+VKeKo2noK\n3Ex1GcBy54X6Kj3XHPbDny48/sPtzzbfo20JLFtS+fPnzKWFOov/H8yOSkYvd7Vs\ntwov3e+5bTDrk7tJXZ22n4PZspyKRrEauRc9UEWYAQKBgQDlyTSjhAqsnkOQXtwL\noaU9TTEiyvA9ue+KGXND+RqpNQU7dEDg4r0jYTHi7GpJUVoe2wCCfqcZshy4DVqv\nph8v+6cuYFZ8GeJEEVpi863HxpFwBiuh5WYTIrXmiLQY2s0o3awZgV8/Gyt4tCrg\nJ/e8OkmaUHDSXv9zypesa9pLYQKBgQDV/l0/5h3QfD6qxHKzl6nwPxv7s9/FzF3v\nRSvfIq9VI5Waavx9JrX765MffH1/gOuiyDxJGnSC4NALmmNXCADZRPjoHXJHkmMs\naVAYQekK+edPwDc9F8GA7mCVfJ088RmBdb72++FUvOIVWsQyPv2wOQGJGPBb0elZ\nE9yTlXKkrQKBgFLZ/17N50NiNR5C9bhD6l52DLds0L6Q4iu7DXJ+yPwln+NWAWaU\nmnm9O82ETLZu3L2vXTmwDPQY4n4CYqZekXQtmpQALG7Grmy4jQyMrCYSFLJ9pxHS\nssFHjKq4s6cajUqk0r7HhN4uH7h/zc3Q22RE5/D5/BP+KMFJVPLYWHdBAoGBAJgR\nhlqeQJmjcTURHSGaqVzcvBoGHQMG08nwsdiDYW1zOCDf3kVhePlo0sgRQ22UQ98N\nxCl+70UCVVWphOaX/WJorSjlpAxQbsFkpVJXpC/0nvgBdD+p3gytWV1hjKt9+c4R\nyn7hR6NcBp1+PuYl9UmBeSHf4w6dAOIYRytpjGqRAoGAHMg0A/TjLUZEFktn1qAm\nEbsQrBObD/EBtRawf+3GuC8MBWMhMpj5g7MrLhOU1Fwb507/VZm6rCFc7stq4HFc\nBbTDjKHxITE0WuQ8vwKTozn4nSKQFyfSblc+zkaCkTGaoI65OQXKtzZHQtb1lvmD\njJP5xgI4xq94we9Ry5xeOQU=\n-----END PRIVATE KEY-----\n",
    "client_email": "tcg-webhook@tcgwebhook.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token",
}

app = Flask(__name__)
CORS(app)

def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def log_to_sheet(waybill, msg_type, detail):
    try:
        sheet = get_sheet()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, waybill, msg_type, detail])
    except Exception as e:
        print(f"写入 Sheet 失败: {e}")

@app.route("/ping", methods=["GET"])
def ping():
    return "ok", 200

def send_to_wecom(text):
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    requests.post(WECOM_WEBHOOK, json=payload)

def parse_delivery_note(message):
    text = re.sub(r'<[^>]+>', '', message).strip()
    m = re.match(r'DELIVERY\s+(.+?)\s+CONFIRMED\s+(.+?)\s+([A-Z]{2,}[A-Z0-9]{6,}[A-Z0-9]*\s*[A-Z]{2,3})$', text)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return None, None, None

@app.route("/webhook", methods=["POST"])
def receive_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    # ── Shipment note──
    if "message" in data and data["message"]:
        waybill = data.get("shipment_short_tracking_reference", "未知")
        message = data.get("message", "")

        # PO 未指派
        if "Purchase Order (PO) has not been allocated" in message:
            msg = f"**快递异常**\n> 运单号：`{waybill}` ❗未指派❗"
            send_to_wecom(msg)
            log_to_sheet(waybill, "PO未指派", "PO未分配，货件已退回")
            return jsonify({"status": "ok"}), 200

        # 拒收退回 第一种
        if "parcel to be returned to the collection address" in message:
            clean = re.sub(r'<[^>]+>', '', message).strip()
            reason_match = re.search(r'due to (.+?),\s*parcel to be returned', clean, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else "未知原因"
            msg = f"**快递拒收**\n> 运单号：`{waybill}` 被 ❗❗拒收退回❗❗\n> 拒收原因：{reason}"
            send_to_wecom(msg)
            log_to_sheet(waybill, "拒收退回", reason)
            return jsonify({"status": "ok"}), 200

        # 拒收退回 第二种
        if "has been rejected by Takealot due to" in message and "returned to TCG" in message:
            clean = re.sub(r'<[^>]+>', '', message).strip()
            reason_match = re.search(r'rejected by Takealot due to (.+?) and subsequently returned to TCG', clean, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else "未知原因"
            msg = f"**快递拒收**\n> 运单号：`{waybill}` 被 ❗❗拒收退回❗❗\n> 拒收原因：{reason}"
            send_to_wecom(msg)
            log_to_sheet(waybill, "拒收退回", reason)
            return jsonify({"status": "ok"}), 200

        # 约仓通知
        date, time_range, booking_ref = parse_delivery_note(message)
        if date and time_range and booking_ref:
            msg = f"**快递状态更新**\n> 运单号：`{waybill}` ✅ 已指派约仓\n> 约仓时间：{date} {time_range}\n> 约仓号：`{booking_ref}`"
            send_to_wecom(msg)
            log_to_sheet(waybill, "已指派约仓", f"{date} {time_range} {booking_ref}")
            return jsonify({"status": "ok"}), 200

        return jsonify({"status": "ok"}), 200

    # ── Tracking event ──
    waybill    = data.get("short_tracking_reference", "未知")
    status     = data.get("status", "未知状态")
    event_time = data.get("event_time", "")[:19].replace("T", " ")
    from_hub   = data.get("collection_hub", "")
    to_hub     = data.get("delivery_hub", "")
    events          = data.get("tracking_events", [])
    latest_msg      = events[0].get("message", "") if events else ""
    latest_location = events[0].get("location", "") if events else ""

    alert_statuses = {"cancelled", "returned-to-sender", "collected"}
    if status.lower() not in alert_statuses:
        return jsonify({"status": "ok"}), 200

    status_map = {
        "cancelled":          "❌ 已取消",
        "returned-to-sender": "↩️ 已退回",
        "collected":          "📦 已揽收",
    }
    status_label = status_map.get(status.lower(), f"📋 {status}")

    msg = f"**⚠️ 快递异常状态通知**\n> 运单号：`{waybill}`\n> 状态：{status_label}"
    if from_hub and to_hub:
        msg += f"\n> 路线：{from_hub} → {to_hub}"
    if latest_location:
        msg += f"\n> 当前位置：{latest_location}"
    if latest_msg:
        msg += f"\n> 最新动态：{latest_msg}"
    if event_time:
        msg += f"\n> 时间：{event_time}"

    send_to_wecom(msg)
    log_to_sheet(waybill, status_label, f"{from_hub}→{to_hub} {latest_msg}")
    return jsonify({"status": "ok"}), 200
