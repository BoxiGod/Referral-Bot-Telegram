import mysql.connector
from datetime import datetime
import bot_consts as const
import telebot
import cherrypy


def __enter__(self):
    if self.get_autocommit():
        self.query("BEGIN")
    return self.cursor()

def __exit__(self, exc, value, tb):
    if exc:
        self.rollback()
    else:
        self.commit()

        
bot = telebot.TeleBot('')

kbrd_final = telebot.types.ReplyKeyboardMarkup(True, True)
kbrd_start = telebot.types.InlineKeyboardMarkup()
kbrd_sub = telebot.types.InlineKeyboardMarkup()

key_start = telebot.types.InlineKeyboardButton(text='Принять участие', callback_data='start_reg')
key_subscribe1 = telebot.types.InlineKeyboardButton(text='Перейти к @interaliex', url="t.me/interaliex")
key_subscribe2 = telebot.types.InlineKeyboardButton(text='Перейти к @hotcoupons', url="t.me/hotcoupons")
key_subscribe3 = telebot.types.InlineKeyboardButton(text='Перейти к @daysale', url="t.me/daysale")
key_check = telebot.types.InlineKeyboardButton(text='Проверить', callback_data="check_sub")

kbrd_final.row('Друзья', 'До окончания', 'Информация')
kbrd_start.add(key_start)
kbrd_sub.add(key_subscribe1, key_subscribe2)
kbrd_sub.add(key_subscribe3)
kbrd_sub.add(key_check)

mydb = mysql.connector.connect(
    host="localhost",
    user="",
    password="",
    auth_plugin='mysql_native_password',
   #database='SalesContestUsers'
)
with mydb as cursor:
    cursor.execute("CREATE DATABASE IF NOT EXISTS SalesContestUsers")
    cursor.execute("CREATE TABLE IF NOT EXISTS Users (id INT PRIMARY KEY, subs_done BIT, referrer INT)")
    mydb.commit()


def update_col(user_id, col, new_val):
    with mydb as cursor:
        sql = "UPDATE Users SET " + str(col) + "= " + str(new_val) + " WHERE id=" + str(user_id)
        cursor.execute(sql)
        mydb.commit()


def get_col(user_id, column):
    with mydb as cursor:
        sql = "SELECT " + str(column) + " FROM Users WHERE id = '" + str(user_id) + "'"
        cursor.execute(sql)
        result = cursor.fetchall()
        try:
            return result[0][0]
        except IndexError:
            return result


def get_amount_of_refs(user_id, subs_done):
    with mydb as cursor:
        if subs_done == 1:
            sql = "SELECT * FROM Users WHERE referrer = '" + str(user_id) + "'" " and subs_done = " + str(subs_done)
        else:
            sql = "SELECT * FROM Users WHERE referrer = '" + str(user_id) + "'"
        cursor.execute(sql)
        result = cursor.fetchall()
        return len(result)


def check_sub(channel, user_id):
    if bot.get_chat_member(channel, user_id).status == 'left':
        return False
    return True


def insert_user(tg_id, referrer, subs_done):
    with mydb as cursor:
        sql = "INSERT INTO Users (id, subs_done, referrer) VALUES (%s, %s, %s)"
        val = (str(tg_id), referrer, subs_done)
        cursor.execute(sql, val)
        mydb.commit()


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, message.text)
    if not get_col(message.chat.id, 'id'):
        insert_user(message.chat.id, 0, 0)
        args = telebot.util.extract_arguments(message.text)  # get args when /start
        if args and get_col(message.chat.id, "referrer") != int(message.chat.id):
            update_col(message.chat.id, 'referrer', args)
            try:
                bot.send_message(get_col(message.chat.id, "referrer"), const.NEW_REF +
                                 "@" + message.chat.username + const.NO_NEW_REF)
            except TypeError:
                bot.send_message(get_col(message.chat.id, "referrer"), const.NEW_REF
                                 + message.chat.first_name + " " + message.chat.last_name + const.NO_NEW_REF)
    if get_col(message.chat.id, 'subs_done') == 0:
        bot.send_message(message.chat.id, const.START, reply_markup=kbrd_final, parse_mode="Markdown")
        bot.send_message(message.chat.id, 'Хочешь принять участие?', reply_markup=kbrd_start)
    else:
        bot.send_message(message.chat.id, 'Ты уже участвуешь')


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == "start_reg":  # pressed button start
        bot.send_message(call.message.chat.id, const.START_REG, reply_markup=kbrd_sub)
    if call.data == "check_sub":  # pressed button "check sub"
        sub_to_text = "К сожалению, ты ещё не подписался на "
        not_subscribed = False
        if not check_sub('@interaliex', call.message.chat.id):
            sub_to_text = sub_to_text + "@interaliex"
            not_subscribed = True
        if not check_sub('@daysale', call.message.chat.id):
            if not_subscribed:
                sub_to_text = sub_to_text + ", @daysale"
            else:
                sub_to_text = sub_to_text + "@daysale"
            not_subscribed = True
        if not check_sub('@hotcoupons', call.message.chat.id):
            if not_subscribed:
                sub_to_text = sub_to_text + "и @hotcoupons"
            else:
                sub_to_text = sub_to_text + "@hotcoupons"
        if not_subscribed:
            bot.send_message(call.message.chat.id, sub_to_text, reply_markup=kbrd_sub)
        else:
            bot.send_message(call.message.chat.id, const.FINISH_REG, parse_mode="Markdown", reply_markup=kbrd_final)
            update_col(call.message.chat.id, 'subs_done', 1)
            if get_col(call.message.chat.id, "referrer") > 0:
                if get_col(call.message.chat.id, "referrer") != int(call.message.chat.id):
                    try:
                        bot.send_message(get_col(call.message.chat.id, "referrer"), const.NEW_REF +
                                         "@" + call.message.chat.username + const.REG_REF)
                    except TypeError:
                        bot.send_message(get_col(call.message.chat.id, "referrer"), const.NEW_REF
                                         + call.message.chat.first_name + " "
                                         + call.message.chat.last_name + const.REG_REF)


@bot.message_handler(content_types=['text'])
def start(message):
    if message.text.lower() == "друзья" and get_col(message.chat.id, 'id'):
        bot.send_message(message.chat.id, "🙋‍♂️Количество "
                                          "твоих приглашённых друзей: "
                         + str(get_amount_of_refs(message.chat.id, 0)) +
                         "\n\n🙋‍♂️Количество друзей,"
                         " завершивших регистрацию: "
                         + str(get_amount_of_refs(message.chat.id, 1))
                         + const.REF_LINK + str(message.chat.id), reply_markup=kbrd_final,
                         disable_web_page_preview=True)
    elif message.text.lower() == "до окончания" and get_col(message.chat.id, 'id'):
        end_time = datetime(2019, 10, 31)
        till_end = end_time - datetime.now()
        bot.send_message(message.chat.id, "👉Дней до окончания: "
                         + str(till_end.days), reply_markup=kbrd_final)
    elif message.text.lower() == "информация" and get_col(message.chat.id, 'id'):
        bot.send_message(message.chat.id, const.INFO, reply_markup=kbrd_final, parse_mode="Markdown")
    else:
        if get_col(message.chat.id, 'subs_done') != 1:
            bot.send_message(message.chat.id, const.NOT_PARTICIPATE)
        else:
            bot.send_message(message.chat.id, const.PARTICIPATE, reply_markup=kbrd_final)


WEBHOOK_HOST = ''
WEBHOOK_PORT = 443
WEBHOOK_LISTEN = '0.0.0.0'  

WEBHOOK_SSL_CERT = './webhook_cert.pem' 
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % ('')


class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
                        'content-type' in cherrypy.request.headers and \
                        cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)


bot.remove_webhook()

bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

cherrypy.config.update({
    'server.socket_host': WEBHOOK_LISTEN,
    'server.socket_port': WEBHOOK_PORT,
    'server.ssl_module': 'builtin',
    'server.ssl_certificate': WEBHOOK_SSL_CERT,
    'server.ssl_private_key': WEBHOOK_SSL_PRIV
})


cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})
