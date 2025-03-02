from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api', methods=['GET'])
def api():
    # الحصول على المعاملات من الطلب
    msg = request.args.get('msg', '')

    # معالجة الطلب
    response = {"response": f"You said: {msg}"}

    # إرجاع الرد
    return jsonify(response)

def start_api(host="0.0.0.0", port=5000):
    """
    دالة لبدء تشغيل الـ API.
    """
    app.run(host=host, port=port)

if __name__ == "__main__":
    start_api()
