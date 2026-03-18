from flask import Flask, request, jsonify
import requests

WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=42717010-0635-4e8c-a9ce-d824676db0b1"

app = Flask(__name__)

def send_to_wecom(text):
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    requests.post(WECOM_WEBHOOK, json=payload)

@app.route("/webhook", methods=["POST"])
def receive_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    waybill    = data.get("waybill_number", data.get("waybillNumber", "未知"))
    status     = data.get("status", "未知状态")
    note       = data.get("note", "")
    recipient  = data.get("recipient_name", data.get("recipientName", ""))
    event_time = data.get("timestamp", data.get("eventDate", ""))

    status_map = {
        "delivered":        "✅ 已送达",
        "cancelled":        "❌ 已取消",
        "out_for_delivery": "🚚 派送中",
        "collected":        "📦 已揽收",
        "returned":         "↩️ 已退回",
    }
    status_label = status_map.get(status.lower(), f"📋 {status}")

    msg = f"**快递状态更新**\n> 运单号：`{waybill}`\n> 状态：{status_label}"
    if recipient:
        msg += f"\n> 收件人：{recipient}"
    if event_time:
        msg += f"\n> 时间：{event_time}"
    if note:
        msg += f"\n> 备注：{''.join(note.split())}"

    send_to_wecom(msg)
    return jsonify({"status": "ok"}), 200
