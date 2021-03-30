import telebot
import psycopg2
import os
import random
from config import TOKEN


DATABASE_URL = os.environ['DATABASE_URL']


con = psycopg2.connect(DATABASE_URL, sslmode="require")

print("Database opened")
cur = con.cursor()

bot = telebot.TeleBot(TOKEN)


def get_training_comment(correct, wrong):
    excelent_comments = [
        'Сеньор(а), вы великолепны!',
        "Замечательный результат!",
        "Да вы знаток испанского."
    ]
    not_good_comments = [
        'Подучите слова',
        "Нехорошо, амиго, нехорошо..."
    ]
    good_comments = [
        "Вы молодец. Но вам нужно еще подучить слова",
        'Так держать.',
        "Еще чуть-чуть, амиго! Еще чуть-чуть!"
    ]
    bad_comments = [
        'Увы, но вам нужно еще подучить слова',
        "Как же так, амиго?",
        "Ты меня расстроил, амиго. Сначала подучи слова",
        "Амиго, не хочешь ли ты для начала повторить слова? Вижу, ты ничего не запомнил."
    ]

    total = correct + wrong
    if correct / total >= 0.8:
        rand = random.randint(0, len(excelent_comments) - 1)
        return excelent_comments[rand]
    elif 0.5 < correct / total < 0.8:
        rand = random.randint(0, len(good_comments) - 1)
        return good_comments[rand]
    elif  0.3 < correct/total <= 0.5:
        rand = random.randint(0, len(not_good_comments) - 1)
        return not_good_comments[rand]
    else:
        rand = random.randint(0, len(bad_comments) - 1)
        return bad_comments[rand]

#Strings

bot_commands_string = """\n\
/add_words - добавить список слов и ассоциаций в словарь
/delete - удалить слово из словаря
/vocabulary - просмотреть текущий словарь
/training - начать тренировку
/rename - сменить имя"""


#Keyboards
commands_keyboard = telebot.types.ReplyKeyboardMarkup(True)
commands_keyboard.row("/reg", '/add_words', '/delete', '/vocabulary', '/training', '/rename')

reg_key = telebot.types.ReplyKeyboardMarkup(True, True)
reg_key.row("/reg")

stop_command_key = telebot.types.ReplyKeyboardMarkup(True, True)
stop_command_key.row("/stop")

@bot.message_handler(commands=['add_words'])
def add_words(message):
    bot.send_message(message.from_user.id, """Отправьте сообщение в следующем формате:
испанское слово > русское слово, русское слово > ссылка на картинку;
испанское слово > русское слово, русское слово, русское слово > ссылка на картинку;
...
испанское слово > русское слово > ссылка на картинку;""")
    bot.register_next_step_handler(message, get_words_from_message)

def get_words_from_message(message):
    translates = message.text.split(";")
    for translate in translates:
        print(translate)
        if (len(translate.split(">")) < 3):
            continue
        es, ru, picture = translate.split(">")
        es = es.strip()
        ru = ru.strip()
        picture = picture.strip()
        cur.execute("INSERT INTO vocabulary_{user_id} (es, ru) VALUES ('{es}', '{ru}')".format(user_id=message.from_user.id,
                                                                                            es=es, ru = ru))
        cur.execute("INSERT INTO pictures_{user_id} (word, picture_id) VALUES ('{word}', '{picture}')".format(user_id=message.from_user.id,
                                                                                                          word=es, picture=picture))
    con.commit()
    bot.send_message(message.from_user.id, "Слова успешно добавлены")

@bot.message_handler(commands=['reg'])
def reg(message):
    cur.execute("""CREATE TABLE IF NOT EXISTS users( 
        user_id serial primary key,
        name VARCHAR(30) NOT NULL    
    ) """)
    cur.execute("SELECT user_id, name FROM users")
    users = cur.fetchall()
    userIsFound = False
    for user in users:
        if user[0] == message.from_user.id:
            bot.send_message(message.from_user.id, "{name}, амиго, ты что, уже забыл о нашей давней дружбе? /"
                                                   "А я помню о тебе".format(name=user[1]))
            global commands_keyboard
            bot.send_message(message.from_user.id, "Давай я тебе напомню, как мы с тобой можем развлечься:" +
                             bot_commands_string,
                             reply_markup=commands_keyboard)
            userIsFound = True

    if not userIsFound:
        bot.send_message(message.from_user.id, "Скажи, амиго, как к тебе обращаться?")
        bot.register_next_step_handler(message, register_user)


def register_user(message):

    cur.execute( "INSERT INTO users (name, user_id) VALUES ('{name}', {user_id})".format(name=message.text,
                                                                                         user_id=message.from_user.id))
    cur.execute("""CREATE TABLE vocabulary_{user_id} (
                    id serial primary key, 
                    es char varying(30), 
                    ru char varying(30))""".format(user_id=message.from_user.id))
    cur.execute("""CREATE TABLE pictures_{user_id} (
                    word char varying(30) primary key,
                    picture_id text)""".format(user_id=message.from_user.id))
    con.commit()
    global commands_keyboard
    bot.send_message(message.from_user.id, ("Отлично, {name}. Да будет крепка наша дружба! Что ты хочешь делать?" +
                                            bot_commands_string).format(name=message.text),
                     reply_markup=commands_keyboard)

@bot.message_handler(commands=['rename'])

def get_name(message):
    cur.execute("SELECT user_id FROM users WHERE user_id = {user_id}".format(user_id = message.from_user.id))
    if len(cur.fetchall()) == 0:
        bot.send_message(message.from_user.id, "Давай сначала познакомимся. Зарегистрируйся, пожалуйста")
    else:
        bot.send_message(message.from_user.id, "Скажи, пожалуйста, как теперь тебя называть?")
        bot.register_next_step_handler(message, rename)


def rename(message):
    cur.execute("UPDATE users SET name='{new_name}' WHERE user_id={user_id}".format(new_name=message.text,
                                                                                    user_id=message.from_user.id))
    con.commit()
    bot.send_message(message.from_user.id, "Хорошо. Теперь ты для меня {new_name}".format(new_name=message.text))
    global commands_keyboard
    bot.send_message(message.from_user.id, "Чем теперь займемся?", reply_markup=commands_keyboard)

@bot.message_handler(commands=['vocabulary'])
def show_vocabulary(message):
    cur.execute("SELECT user_id FROM users WHERE user_id = {user_id}".format(user_id=message.from_user.id))

    if len(cur.fetchall()) == 0:
        bot.send_message(message.from_user.id, "Давай сначала познакомимся. Зарегистрируйся, пожалуйста",
                         reply_markup=reg_key)
    else:
        vocabulary = ""
        cur.execute("SELECT word FROM pictures_{user_id} ORDER BY word".format(user_id=message.from_user.id))
        words = cur.fetchall()
        for word in words:
            cur.execute("SELECT ru FROM vocabulary_{user_id} WHERE es='{es}'".format(user_id=message.from_user.id,
                                                                                     es=word[0]))
            translates = cur.fetchall()
            vocabulary += word[0] + " - "
            for translate in translates:
                vocabulary += translate[0] + ", "
            vocabulary += "\b\b\n"

        bot.send_message(message.from_user.id, vocabulary)


spanish = ""
russian = ""
picture_id = ""

@bot.message_handler(commands=["delete"])
def get_word(message):
    cur.execute("SELECT user_id FROM users WHERE user_id = {user_id}".format(user_id=message.from_user.id))
    if len(cur.fetchall()) == 0:
        bot.send_message(message.from_user.id, "Давай сначала познакомимся. Зарегистрируйся, пожалуйста")
    else:
        bot.send_message(message.from_user.id, "Введите слово по-испански")
        bot.register_next_step_handler(message, delete_word)

def delete_word(message):
    cur.execute("DELETE FROM pictures_{user_id} WHERE word = '{word}'".format(user_id=message.from_user.id,
                                                                              word=message.text))
    cur.execute("DELETE FROM vocabulary_{user_id} WHERE es='{word}'".format(user_id=message.from_user.id,
                                                                            word=message.text))
    con.commit()
    bot.send_message(message.from_user.id, "Слово успешно удалено", reply_markup=commands_keyboard)


is_testing_mode = False
training_word = ""
correct_answers = 0
wrong_answers = 0

@bot.message_handler(commands=["training"])
def start_training(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
    keyboard.row('Перевод', 'Ассоциации')
    bot.send_message(message.from_user.id, "Выберите вид тренировки", reply_markup=keyboard)
    bot.register_next_step_handler(message, choose_training_mode)


def choose_training_mode(message):
    if message.text == "Перевод":
        keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
        keyboard.row("Тест", "Письмо")
        bot.send_message(message.from_user.id, 'Выберите режим', reply_markup=keyboard)
        bot.register_next_step_handler(message, choose_language)

    elif message.text == "Ассоциации":
        keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
        keyboard.row("Тест", "Письмо")
        bot.send_message(message.from_user.id, 'Выберите режим', reply_markup=keyboard)
        bot.register_next_step_handler(message, send_picture)



def choose_language(message):
    global is_testing_mode
    is_testing_mode = (message.text == "Тест")
    lang_keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
    lang_keyboard.row("Русский -> Испанский", "Испанский -> Русский")
    bot.send_message(message.from_user.id, "Выберите режим перевода", reply_markup=lang_keyboard)
    bot.register_next_step_handler(message, send_translation)

ru_word = ""
es_word = ""

def send_translation(message):
    cur.execute("SELECT ru, es FROM vocabulary_{user_id}".format(user_id=message.from_user.id))
    translates = cur.fetchall()
    index = random.randint(0, len(translates) - 1)
    global ru_word
    global es_word
    ru_word = translates[index][0]
    es_word = translates[index][1]
    if message.text == "Русский -> Испанский":
        if is_testing_mode:
            variants = []
            variants.append(es_word)
            random.shuffle(translates)
            for translate in translates:
                if len(variants) == 4:
                    break
                if (translate[1] != es_word):
                    variants.append(translate[1])
            variants_keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
            variants_keyboard.row(variants[0], variants[1], variants[2], variants[3], "/stop")
            bot.send_message(message.from_user.id, ru_word, reply_markup=variants_keyboard)
        else:
            bot.send_message(message.from_user.id, ru_word, reply_markup=stop_command_key )
        bot.register_next_step_handler(message, send_translation_ru)

    elif message.text == "Испанский -> Русский":
        if is_testing_mode:
            variants = []
            variants.append(ru_word)
            random.shuffle(translates)
            for translate in translates:
                if len(variants) == 4:
                    break
                if (translate[0] != ru_word):
                    variants.append(translate[0])
            variants_keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
            variants_keyboard.row(variants[0], variants[1], variants[2], variants[3], "/stop")
            bot.send_message(message.from_user.id, es_word, reply_markup=variants_keyboard)
        else:
            bot.send_message(message.from_user.id, es_word, reply_markup=stop_command_key )
        bot.register_next_step_handler(message, send_translation_es)



def send_translation_ru(message):
    global es_word
    global ru_word
    global correct_answers
    global wrong_answers
    if message.text == "/stop":
        es_word = ""
        ru_word = ""
        bot.send_message(message.from_user.id, get_training_comment(correct_answers, wrong_answers) +
                         "\nВерно: {correct}, неверно: {wrong}".format(correct = correct_answers,
                                                                                           wrong = wrong_answers))
        correct_answers = 0
        wrong_answers = 0
        bot.send_message(message.from_user.id, "Ну что, чем займемся?" + bot_commands_string, reply_markup=commands_keyboard)
    else:
        cur.execute("SELECT es FROM vocabulary_{user_id} WHERE ru = '{ru_word}'".format(user_id = message.from_user.id,
                                                                                        ru_word = ru_word))
        es_words = cur.fetchall()
        if message.text.lower().strip() in es_words[0]:
            bot.send_message(message.from_user.id, "Верно")
            correct_answers += 1
        else:
            correct_words = ""
            for word in es_words[0]:
                correct_words += word + ', '
            bot.send_message(message.from_user.id, "Неверно. Правильный ответ " + correct_words)
            wrong_answers += 1
        cur.execute("SELECT ru, es FROM vocabulary_{user_id}".format(user_id=message.from_user.id))
        translates = cur.fetchall()
        index = random.randint(0, len(translates) - 1)
        ru_word = translates[index][0]
        es_word = translates[index][1]
        if is_testing_mode:
            variants = []
            variants.append(es_word)
            random.shuffle(translates)
            for translate in translates:
                if len(variants) == 4:
                    break
                if translate[1] != es_word:
                    variants.append(translate[1])
            random.shuffle(variants)
            variants_keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
            variants_keyboard.row(variants[0], variants[1], variants[2], variants[3], "/stop")
            bot.send_message(message.from_user.id, ru_word, reply_markup=variants_keyboard)
        else:
            bot.send_message(message.from_user.id, ru_word, reply_markup=stop_command_key )

        bot.register_next_step_handler(message, send_translation_ru)


def send_translation_es(message):
    global es_word
    global ru_word
    global correct_answers
    global wrong_answers
    if message.text == "/stop":
        es_word = ""
        ru_word = ""
        bot.send_message(message.from_user.id, get_training_comment(correct_answers, wrong_answers) +
                         "\nВерно: {correct}, неверно: {wrong}".format(correct = correct_answers, wrong = wrong_answers))
        correct_answers = 0
        wrong_answers = 0
        bot.send_message(message.from_user.id, "Ну что, чем займемся?" + bot_commands_string, reply_markup=commands_keyboard)
    else:
        cur.execute("SELECT ru FROM vocabulary_{user_id} WHERE es = '{es_word}'".format(user_id=message.from_user.id,
                                                                                        es_word=es_word))
        ru_words = cur.fetchall()
        print(ru_words)
        print (message.text.lower().strip() in ru_words[0])
        if message.text.lower().strip() in ru_words[0]:
            bot.send_message(message.from_user.id, "Верно")
            correct_answers += 1
        else:
            correct_words = ""
            for word in ru_words[0]:
                correct_words += word + ', '
            bot.send_message(message.from_user.id, "Неверно. Правильный ответ " + correct_words)
            wrong_answers += 1
        cur.execute("SELECT ru, es FROM vocabulary_{user_id}".format(user_id=message.from_user.id))
        translates = cur.fetchall()
        index = random.randint(0, len(translates) - 1)
        ru_word = translates[index][0]
        es_word = translates[index][1]
        if is_testing_mode:
            variants = []
            variants.append(ru_word)
            random.shuffle(translates)
            for translate in translates:
                if len(variants) == 4:
                    break
                if translate[0] != ru_word:
                    variants.append(translate[0])
            random.shuffle(variants)
            variants_keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
            variants_keyboard.row(variants[0], variants[1], variants[2], variants[3], "/stop")
            bot.send_message(message.from_user.id, es_word, reply_markup=variants_keyboard)
        else:
            bot.send_message(message.from_user.id, es_word, reply_markup=stop_command_key )
        bot.register_next_step_handler(message, send_translation_es)



def send_picture(message):
    global is_testing_mode
    global correct_answers
    global wrong_answers
    global training_word
    if (message.text != "/stop"):
        if training_word != "":
            if message.text.lower().strip() == training_word.lower().strip():
                bot.send_message(message.from_user.id, "Верно")
                correct_answers += 1
            else:
                bot.send_message(message.from_user.id, "Неверно. Правильный ответ " + training_word)
                wrong_answers += 1
        else:
            bot.send_message(message.from_user.id, "Поехали!")
            is_testing_mode = (message.text == "Тест")

        bot.send_message(message.from_user.id, "Введите испанское слово, ассоциирующееся с картинкой.")
        cur.execute("SELECT picture_id, word FROM pictures_{user_id}".format(user_id=message.from_user.id))
        words = cur.fetchall()

        index = random.randint(0, len(words) - 1)
        training_word = words[index][1]
        training_photo = words[index][0]


        if is_testing_mode:
            variants_keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
            variants = []
            random.shuffle(words)
            variants.append(training_word)

            for w in words:
                if (len(variants) == 4):
                    break
                if (w[1] != training_word):
                    variants.append(w[1])

            random.shuffle(variants)
            variants_keyboard.row(variants[0], variants[1], variants[2], variants[3], "/stop")

            bot.send_photo(message.from_user.id, training_photo, reply_markup=variants_keyboard)
            bot.register_next_step_handler(message, send_picture)

        else:
            bot.send_photo(message.from_user.id, training_photo, reply_markup=stop_command_key)
            bot.register_next_step_handler(message, send_picture)
    else:
        bot.send_message(message.from_user.id, get_training_comment(correct_answers,wrong_answers) +
                         "\nВерно: {correct}, неверно: {wrong}".format(correct=correct_answers,
                                                                                           wrong=wrong_answers))
        training_word = ""
        correct_answers = 0
        wrong_answers = 0
        global commands_keyboard
        bot.send_message(message.from_user.id, "Ну что, чем займемся?", reply_markup=commands_keyboard)




@bot.message_handler(content_types=["text"])
def start(message):
    global commands_keyboard

    cur.execute("""CREATE TABLE IF NOT EXISTS users( 
        user_id serial primary key,
        name VARCHAR(30) NOT NULL    
    ) """)
    bot.send_message(message.from_user.id, """Хола, мой новый друг! Меня зовут Хосе, и я помогу тебе в изучении\
испанского языка. Добавляй слова в словарь, подбирай картинки, ассоциирующиеся со словами и тренируйся!
         
Вот список того, что мы можем с тобой делать:""" + bot_commands_string, reply_markup=commands_keyboard)


def registered(message):
    cur.execute('SELECT name FROM users WHERE user_id = {id}'.format(id=message.from_user.id))
    username = cur.fetchall()[0][0]
    global commands_keyboard
    bot.send_message(message.from_user.id,"Ну что, {username}, чем займемся?".format(username=username),
                     reply_markup=commands_keyboard)



bot.polling(none_stop=True, interval=0)