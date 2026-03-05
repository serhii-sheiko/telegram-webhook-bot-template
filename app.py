import logging
import os
import sys
import time

import flask
from flask import Flask
import telebot
from pymongo import MongoClient
from pymongo.server_api import ServerApi

ENV_NAME = os.getenv("ENV")
ENV_PRODUCTION = "prod"
MONGO_URI = os.environ.get("MONGO_URI")

DB_NAME = os.environ.get("DB_NAME")
DB_COLLECTION = os.environ.get("DB_COLLECTION")
TELEGRAM_API_TOKEN = os.environ.get("TELEGRAM_API_TOKEN")
BASE_URL = os.environ.get("BASE_URL")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
WEBHOOK_URL = f"{BASE_URL}/{WEBHOOK_SECRET}"
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

if ENV_NAME == ENV_PRODUCTION:
    client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
else:
    client = MongoClient(
        MONGO_URI, server_api=ServerApi("1"), tls=True, tlsAllowInvalidCertificates=True
    )

db = client[DB_NAME]
db_collection = db[DB_COLLECTION]

# Configure logging to stdout
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_API_TOKEN)


@app.route("/")
def hello_world():
    return "Hello World!"


@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook_handler():
    if flask.request.headers.get("content-type") == "application/json":
        json_string = flask.request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ""
    else:
        flask.abort(403)


@bot.message_handler(commands=["start"])
def bot_wellcome(message):
    bot.reply_to(message, "Welcome to telegram bot!")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, message.text)


if __name__ == "__main__":
    if ENV_NAME == ENV_PRODUCTION:
        # Remove webhook, it fails sometimes the set if there is a previous webhook
        webhook_info = bot.get_webhook_info()
        if WEBHOOK_URL != webhook_info.url:
            logging.info("webhook url changed")
            bot.remove_webhook()
            time.sleep(0.1)
            # Set webhook
            bot.set_webhook(url=WEBHOOK_URL)
        else:
            logging.info("leave webhook url unchanged")

        from waitress import serve

        serve(app, host="0.0.0.0", port=PORT)
    else:
        bot.infinity_polling()
        # app.run(debug=True)
