import subprocess
import sys
import os
import telebot
import uuid
from flask import Flask, request, jsonify
import Pycodz.ai as z44o
import threading
import psycopg2
from psycopg2 import sql

# الاتصال بقاعدة البيانات

# قراءة التوكن ومعرف الدردشة من البيئة
BOTTOKEN = '7207961885:AAGRf5GZTCOGL5QSBe56xTs7C1d8kpM-R5s'
ADMINID = '1090494697'

# إنشاء كائن البوت
admin_bot = telebot.TeleBot(BOTTOKEN)

# قاعدة بيانات مؤقتة (تستخدم ذاكرة البوت)

def get_db_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))  # DATABASE_URL من متغيرات البيئة
    return conn

# إنشاء جدول إذا لم يكن موجودًا
def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_users (
            user_id TEXT PRIMARY KEY,
            is_blocked BOOLEAN NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# حظر مستخدم
def block_user_db(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO blocked_users (user_id, is_blocked)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET is_blocked = EXCLUDED.is_blocked
    """, (user_id, True))
    conn.commit()
    cur.close()
    conn.close()

# إلغاء حظر مستخدم
def unblock_user_db(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM blocked_users
        WHERE user_id = %s
    """, (user_id,))
    conn.commit()
    cur.close()
    conn.close()

# التحقق من حالة الحظر
def is_user_blocked(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT is_blocked FROM blocked_users
        WHERE user_id = %s
    """, (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else False





def install_missing_packages():
    required_libs = ["flask", "Pycodz", "gunicorn", "pyTelegramBotAPI", "python-dotenv"]  # ضع أي مكتبات تستخدمها هنا
    for lib in required_libs:
        try:
            __import__(lib)  # محاولة استيراد المكتبة
        except ImportError:
            print(f"📦 تثبيت المكتبة المفقودة: {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])  # تثبيت المكتبة

# تشغيل التثبيت قبل أي شيء آخر
install_missing_packages()

# باقي كود Flask العادي
app = Flask(__name__)

@app.after_request
def add_headers(response):
    """ضمان أن يكون الرد دائماً بصيغة JSON"""
    response.headers["Content-Type"] = "application/json"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route('/api', methods=['GET'])
def chat():
    try:
        user_id = request.cookies.get('user_id')
        if not user_id:
            user_id = str(uuid.uuid4())
            response = jsonify({"response": "تم إنشاء معرف مستخدم جديد.", "user_id": user_id})
            response.set_cookie('user_id', user_id)
            return response, 200

        msg = request.args.get('msg', '').strip()
        if not msg:
            return jsonify({"error": "❌ يجب إرسال رسالة عبر ?msg="}), 400

        # التحقق من حالة الحظر
        if is_user_blocked(user_id):  # التحقق من قاعدة البيانات
            return jsonify({"error": "❌ تم حظرك من استخدام الخدمة.", "status": "blocked"}), 403

        # معالجة الطلب
        bot = z44o.PHIND()
        response = bot.chat(prompt=msg)

        # إرسال الطلب والرد معًا إلى الإدمن
        message_to_admin = f"""
📩 *طلب جديد من المستخدم:*
User ID: {user_id}
الرسالة: {msg}

📤 *الرد من API:*
{response}
        """
        admin_bot.send_message(ADMINID, message_to_admin)

        return jsonify({"response": response, "status": "success"}), 200

    except Exception as e:
        admin_bot.send_message(ADMINID, f"❌ *حدث خطأ:*\n{str(e)}")
        return jsonify({"error": "❌ خطأ داخلي في السيرفر", "details": str(e), "status": "error"}), 500

@admin_bot.message_handler(commands=['block'])
def block_user(message):
    try:
        user_id = message.text.split()[1]
        block_user_db(user_id)  # حظر المستخدم في قاعدة البيانات
        admin_bot.reply_to(message, f"✅ تم حظر المستخدم ذو المعرف {user_id}.")
    except IndexError:
        admin_bot.reply_to(message, "❌ يجب إرسال معرف المستخدم مع الأمر. مثال: /block user123")
    except Exception as e:
        admin_bot.reply_to(message, f"❌ حدث خطأ أثناء حظر المستخدم: {e}")

@admin_bot.message_handler(commands=['unblock'])
def unblock_user(message):
    try:
        user_id = message.text.split()[1]
        unblock_user_db(user_id)  # إلغاء حظر المستخدم في قاعدة البيانات
        admin_bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم ذو المعرف {user_id}.")
    except IndexError:
        admin_bot.reply_to(message, "❌ يجب إرسال معرف المستخدم مع الأمر. مثال: /unblock user123")
    except Exception as e:
        admin_bot.reply_to(message, f"❌ حدث خطأ أثناء إلغاء حظر المستخدم: {e}")


if __name__ == '__main__':
    # تشغيل البوت في خيط منفصل
    import threading
    bot_thread = threading.Thread(target=admin_bot.polling)
    bot_thread.start()

    # تشغيل Flask
    app.run(host='0.0.0.0', port=5000)
