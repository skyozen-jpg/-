# - import telebot
import requests
import re
from urllib.parse import quote
from telebot import types

# ====== ВСТАВЬ СВОИ ДАННЫЕ ======
TG_TOKEN = '9012251753:AAGJQG8PRRP0ZMiABjcepGWaTR2IcfykLI0'
YANDEX_TOKEN = 'y0__wgBEI_KorwGGNWzQiDFiqziGTDDpYDxBzedhXimLElRolsAjxMLFGMSoTnD'
PLACE_ID = '806451'
# ================================

bot = telebot.TeleBot(TG_TOKEN)

# --- Кнопки внизу экрана ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('🎁 Получить скидку')
    btn2 = types.KeyboardButton('📋 Мои скидки')
    btn3 = types.KeyboardButton('🔥 Скидки других')
    btn4 = types.KeyboardButton('🧮 Калькулятор скидки')
    btn5 = types.KeyboardButton('ℹ️ Как это работает')
    markup.add(btn1)
    markup.add(btn2, btn3)
    markup.add(btn4, btn5)
    return markup

# 1. Команда START
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋\n\nЯ помогу тебе получить скидку на товары с Яндекс Маркета.\n\nВыбери действие на кнопках ниже 👇",
        reply_markup=get_main_keyboard()
    )

# 2. Кнопка "Как это работает"
@bot.message_handler(func=lambda message: message.text == 'ℹ️ Как это работает')
def how_it_works(message):
    text = (
        "ℹ️ **Как получить скидку**\n\n"
        "1. Нажмите «🎁 Получить скидку».\n"
        "2. Отправьте ссылку на товар с Яндекс Маркета.\n"
        "3. Бот проверит товар через Яндекс API.\n"
        "4. Если дополнительная скидка доступна, вы получите размер скидки и ссылку на товар.\n\n"
        "Фактическую цену и условия всегда проверяйте на Яндекс Маркете: они могут измениться."
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_keyboard())

# 3. Кнопка "Получить скидку"
@bot.message_handler(func=lambda message: message.text == '🎁 Получить скидку')
def get_discount(message):
    text = (
        "🎁 Пришлите ссылку на товар с Яндекс Маркета.\n"
        "Я проверю, доступна ли дополнительная скидка, и верну партнёрскую ссылку."
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())

# 4. Остальные кнопки (заглушки)
@bot.message_handler(func=lambda message: message.text in ['📋 Мои скидки', '🔥 Скидки других', '🧮 Калькулятор скидки'])
def other_buttons(message):
    bot.send_message(
        message.chat.id,
        "Эта функция пока в разработке 🛠\nСкоро здесь появится много всего интересного!",
        reply_markup=get_main_keyboard()
    )

# 5. Обработка ссылок (Главная логика)
@bot.message_handler(func=lambda message: "market.yandex.ru" in message.text or "market.yandex" in message.text)
def handle_link(message):
    url = message.text.strip()
    
    if "?" in url:
        url = url.split("?")[0]

    bot.send_message(message.chat.id, "Секунду, проверяю товар...", reply_markup=get_main_keyboard())
    
    product_info = None
    try:
        match = re.search(r'/product/[^/]+/(\d+)', url)
        if not match:
             match = re.search(r'/product/(\d+)', url)
             
        if match:
            product_id = match.group(1)
            info_url = f"https://api.content.market.yandex.ru/v3/products/{product_id}?format=json&clid=2310490"
            headers_info = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
            resp_info = requests.get(info_url, headers=headers_info)
            
            if resp_info.status_code == 200:
                info_data = resp_info.json()
                if info_data.get('status') == 'OK':
                    product_info = info_data.get('product', {})
    except Exception as e:
        print(f"Ошибка при получении инфо о товаре: {e}")
        pass 
    
    encoded_url = quote(url, safe='')
    api_url = f"https://api.content.market.yandex.ru/v3/affiliate/partner/article/create?marketUrl={encoded_url}&place_id={PLACE_ID}&isUseDiscount=1&format=json"
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    
    try:
        response = requests.post(api_url, headers=headers)
        
        if response.status_code != 200:
             bot.send_message(message.chat.id, f"Яндекс временно недоступен (код {response.status_code}). Попробуйте позже.")
             return

        data = response.json()
        
        if data.get('status') == 'OK' and 'link' in data:
            link = data.get('link')
            discount = data.get('discount', 0)
            
            if product_info and product_info.get('price'):
                name = product_info.get('name', 'Товар без названия')
                price = product_info.get('price', {}).get('value', 0)
                picture = product_info.get('picture', '')
                
                final_price = "?"
                if isinstance(price, (int, float)) and isinstance(discount, (int, float)):
                     final_price = price - discount
                
                text = (
                    f"**{name}**\n\n"
                    f"Цена: {price} ₽\n"
                    f"Скидку, которую получили: {discount} ₽\n"
                    f"Цена после скидки (расчётная): **{final_price} ₽**\n\n"
                    f"Фактическую цену проверь на Яндекс Маркете 👇"
                )
                
                if picture:
                    bot.send_photo(message.chat.id, picture, caption=text, parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, text, parse_mode='Markdown')
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🛍 Проверить цену на Яндекс Маркете", url=link))
                bot.send_message(message.chat.id, "Переходи по ссылке 👇", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, f"Готово! Ваша скидка: {discount} ₽\n\nПартнёрская ссылка:\n{link}")
        else:
            error_msg = data.get('error', {}).get('message', 'Неизвестная ошибка')
            bot.send_message(message.chat.id, f"Не удалось создать ссылку. Ответ Яндекса: {error_msg}")
            
    except requests.exceptions.RequestException as e:
        bot.send_message(message.chat.id, "Ошибка соединения с Яндексом. Проверьте интернет.")
        print(f"Network error: {e}")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла непредвиденная ошибка. Попробуйте еще раз.")
        print(f"Error: {e}")

# 6. Обработка всего остального
@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.send_message(message.chat.id, "Пожалуйста, отправьте ссылку с Яндекс Маркета или воспользуйтесь кнопками меню 👇", reply_markup=get_main_keyboard())

bot.polling(none_stop=True)
