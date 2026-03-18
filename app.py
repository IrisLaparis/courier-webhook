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

    # 真实字段名
    waybill    = data.get("short_tracking_reference", "未知")
    status     = data.get("status", "未知状态")
    event_time = data.get("event_time", "")[:19].replace("T", " ")
    from_hub   = data.get("collection_hub", "")
    to_hub     = data.get("delivery_hub", "")

    # 取最新一条 tracking event 的 message 和 location
    events  = data.get("tracking_events", [])
    latest_msg      = events[0].get("message", "") if events else ""
    latest_location = events[0].get("location", "") if events else ""

    status_map = {
        "delivered":           "✅ 已送达",
        "cancelled":           "❌ 已取消",
        "out_for_delivery":    "🚚 派送中",
        "collected":           "📦 已揽收",
        "returned-to-sender":  "↩️ 已退回",
        "in-transit":          "🔄 运输中",
        "at-hub":              "🏭 到达中转站",
        "at-destination-hub":  "🏁 到达目的地站",
        "delivery-assigned":   "👷 已分配派送员",
        "collection-assigned": "📋 已分配取件员",
        "submitted":           "📝 已提交",
    }
    status_label = status_map.get(status.lower(), f"📋 {status}")

    msg = f"**快递状态更新**\n> 运单号：`{waybill}`\n> 状态：{status_label}"
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
