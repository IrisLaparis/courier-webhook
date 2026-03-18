from flask import Flask, request, jsonify
import requests, re

WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=42717010-0635-4e8c-a9ce-d824676db0b1"

app = Flask(__name__)

def send_to_wecom(text):
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    requests.post(WECOM_WEBHOOK, json=payload)

def parse_delivery_note(message):
    """解析约仓通知：DELIVERY{date}CONFIRMED{time}{ref}"""
    text = re.sub(r'<[^>]+>', '', message).strip()
    m = re.match(r'DELIVERY(.+?)CONFIRMED(.+?)([A-Z]{2,}[A-Z0-9]{6,}[A-Z]{2,3})$', text)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return None, None, None

@app.route("/webhook", methods=["POST"])
def receive_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    # ── Shipment note（有 message 字段）──
    if "message" in data and data["message"]:
        waybill = data.get("shipment_short_tracking_reference", "未知")
        message = data.get("message", "")

        # PO 未指派
        if "Purchase Order (PO) has not been allocated" in message:
            msg = (
                f"**快递状态更新**\n"
                f"> 运单号：`{waybill}` 未指派"
            )
            send_to_wecom(msg)
            return jsonify({"status": "ok"}), 200

        # 约仓通知
        date, time_range, booking_ref = parse_delivery_note(message)
        if date and time_range and booking_ref:
            msg = (
                f"**快递状态更新**\n"
                f"> 运单号：`{waybill}` 已指派约仓\n"
                f"> 约仓时间：{date} {time_range}\n"
                f"> 约仓号：`{booking_ref}`"
            )
            send_to_wecom(msg)

        # 其他 note 类型不通知
        return jsonify({"status": "ok"}), 200

    # ── Tracking event（有 tracking_events 字段）──
    waybill    = data.get("short_tracking_reference", "未知")
    status     = data.get("status", "未知状态")
    event_time = data.get("event_time", "")[:19].replace("T", " ")
    from_hub   = data.get("collection_hub", "")
    to_hub     = data.get("delivery_hub", "")
    events          = data.get("tracking_events", [])
    latest_msg      = events[0].get("message", "") if events else ""
    latest_location = events[0].get("location", "") if events else ""

    # 只通知取消和退回
    alert_statuses = {"cancelled", "returned-to-sender"}
    if status.lower() not in alert_statuses:
        return jsonify({"status": "ok"}), 200

    status_map = {
        "cancelled":          "❌ 已取消",
        "returned-to-sender": "↩️ 已退回",
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
    return jsonify({"status": "ok"}), 200
