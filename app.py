import subprocess
import sys
import os
import telebot
import uuid
from flask import Flask, request, jsonify
import Pycodz.ai as z44o
# قراءة التوكن ومعرف الدردشة من البيئة
BOTTOKEN = '7207961885:AAGRf5GZTCOGL5QSBe56xTs7C1d8kpM-R5s'
ADMINID = '1090494697'

# إنشاء كائن البوت
admin_bot = telebot.TeleBot(BOTTOKEN)

# قاعدة بيانات مؤقتة (تستخدم ذاكرة البوت)
user_db = {}  # تخزين بيانات المستخدمين {user_id: is_blocked}

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
        # الحصول على معرف المستخدم من ملفات تعريف الارتباط (Cookies)
        user_id = request.cookies.get('user_id')

        # إذا لم يكن هناك معرف مستخدم، قم بإنشاء واحد جديد
        if not user_id:
            user_id = str(uuid.uuid4())  # إنشاء معرف فريد
            response = jsonify({"response": "تم إنشاء معرف مستخدم جديد.", "user_id": user_id})
            response.set_cookie('user_id', user_id)  # تعيين ملف تعريف الارتباط
            return response, 200

        msg = request.args.get('msg', '').strip()  # الحصول على الرسالة

        if not msg:
            return jsonify({"error": "❌ يجب إرسال رسالة عبر ?msg="}), 400

        # التحقق من حالة المستخدم
        if user_id in user_db and user_db[user_id] == 1:  # إذا كان المستخدم محظورًا
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
        admin_bot.send_message(ADMINID, message_to_admin, parse_mode="Markdown")

        return jsonify({"response": response, "status": "success"}), 200

    except Exception as e:
        # إرسال خطأ إلى الإدمن
        admin_bot.send_message(ADMINID, f"❌ *حدث خطأ:*\n{str(e)}", parse_mode="Markdown")
        return jsonify({"error": "❌ خطأ داخلي في السيرفر", "details": str(e), "status": "error"}), 500

# أوامر البوت للتحكم في المستخدمين
@admin_bot.message_handler(commands=['ban'])
def block_user(message):
    """حظر مستخدم"""
    try:
        user_id = message.text.split()[1]  # الحصول على معرف المستخدم من الرسالة
        user_db[user_id] = 1  # حظر المستخدم
        admin_bot.reply_to(message, f"✅ تم حظر المستخدم ذو المعرف {user_id}.")
    except IndexError:
        admin_bot.reply_to(message, "❌ يجب إرسال معرف المستخدم مع الأمر. مثال: /block user123")
    except Exception as e:
        admin_bot.reply_to(message, f"❌ حدث خطأ أثناء حظر المستخدم: {e}")

@admin_bot.message_handler(commands=['unban'])
def unblock_user(message):
    """إلغاء حظر مستخدم"""
    try:
        user_id = message.text.split()[1]  # الحصول على معرف المستخدم من الرسالة
        if user_id in user_db:
            del user_db[user_id]  # إلغاء حظر المستخدم
            admin_bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم ذو المعرف {user_id}.")
        else:
            admin_bot.reply_to(message, f"ℹ️ المستخدم ذو المعرف {user_id} غير محظور.")
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
