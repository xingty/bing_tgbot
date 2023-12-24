from EdgeGPT.EdgeGPT import Chatbot,ConversationStyle
from telebot import TeleBot
from telebot.types import Message,BotCommand,InlineKeyboardButton,InlineKeyboardMarkup
from utils.md2tgmd import escape
from threading import Thread
from utils.prompt import build_bing_prompt,parse_result
from session import Session
import os,json,asyncio
from pathlib import Path

style = ConversationStyle.precise
model = None
search = False

session = Session('bingai')

def load_json(filename):
  script_dir = os.path.dirname(os.path.realpath(__file__))
  cookies_file_path = os.path.join(script_dir, filename)

  if not os.path.exists(cookies_file_path):
     return None

  with open(cookies_file_path, encoding="utf-8") as f:
    return json.load(f)

def ask(message: Message, bot: TeleBot, reply_msg_id):
	async def execute():
		try:
			cookies = load_json("cookies.json")
			ai = await Chatbot.create(
				cookies=cookies,
				proxy='http://127.0.0.1:7890'
			)

			print(f'model={model} style={style.name} search={search}')

			uid = str(message.from_user.id)
			histories = session.get_session(uid)
			webpage_context = build_bing_prompt(histories,message.text)
			# print(webpage_context)
			response = await ai.ask(
				prompt=message.text,
				conversation_style=style,
				webpage_context=webpage_context,
				search_result=search,
				no_search=(not search),
				mode=model,
			)

			if 'item' in response and 'result' in response['item']:
				result = response['item']['result']
				if result and "success" == (result['value']+'').lower():
					reply = bot.reply_to(
						message,
						parse_result(response['item'],search=True),
						parse_mode="MarkdownV2",
						disable_web_page_preview=True
					)

					content = response['item']['result']['message']
					session.append_message(message,reply,content)
				

		except FileNotFoundError:
			return {'code': 500, 'message': 'No cookies file found'},500
		except Exception as e:
			print(e)
			bot.reply_to(message,str(e))
		finally:
			bot.delete_message(message.chat.id, reply_msg_id)
			await ai.close()

	asyncio.run(execute())	

def handle_message(message: Message, bot: TeleBot):
	if message.text == '/start':
		return
	
	print(session.context)
	reply_message: Message = bot.reply_to(
		message, 
		"Getting answers... Please wait",
	)

	reply_msg_id = reply_message.message_id
	Thread(target=ask,args=(message,bot,reply_msg_id)).start()

def handle_search(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}'
	keyboard = [
        [
			InlineKeyboardButton("Enable", callback_data=f'search:on:{context}'),
         	InlineKeyboardButton("disable", callback_data=f'search:off:{context}'),
		],
    ]
	
	reply_markup = InlineKeyboardMarkup(keyboard)
	bot.send_message(
		chat_id=message.chat.id, 
		text=escape(f'Curren status of Search: **{("Enable" if search else "Disable")}**'), 
		reply_markup=reply_markup,
		parse_mode="MarkdownV2"
	)

def do_search_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int):
	global search
	search = operation == "on"

	bot.send_message(
		chat_id=chat_id,
		text=escape(f'Curren status of Search: **{"Enable" if search else "Disable"}**'),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)

def handle_gpt4_turbo(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}'
	keyboard = [
        [
			InlineKeyboardButton("On", callback_data=f'model:on:{context}'),
         	InlineKeyboardButton("Off", callback_data=f'model:off:{context}'),
		],
    ]

	reply_markup = InlineKeyboardMarkup(keyboard)
	bot.send_message(
		chat_id=message.chat.id, 
		text=escape(f'Curren status of gpt4_turbo: **{("on" if model else "off")}**'), 
		reply_markup=reply_markup,
		parse_mode="MarkdownV2"
	)

def do_model_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int):
	global model
	model = ("gpt4-turbo" if operation == "on" else None)

	bot.send_message(
		chat_id=chat_id,
		text=escape(f'Curren status of gpt4_turbo: **{"on" if model else "off"}**'),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)

def handle_style(message: Message, bot: TeleBot):
	keyboard = []
	context = f'{message.message_id}:{message.chat.id}'
	for m in ConversationStyle._member_names_:
		callback_data = f'style:{m}:{context}'
		keyboard.append(InlineKeyboardButton(m, callback_data=callback_data))

	reply_markup = InlineKeyboardMarkup([keyboard])
	bot.send_message(
		chat_id=message.chat.id, 
		text=f"Current style: {style.name}", 
		reply_markup=reply_markup
	)

def do_style_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int):
	global style
	if operation in ConversationStyle._member_names_:
		style = getattr(ConversationStyle, operation)
	else:
		style = ConversationStyle.precise

	bot.send_message(
		chat_id=chat_id,
		text=escape(f"Current Style has been changed to **{style.name}**"),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)

def handle_clear(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}'
	keyboard = [
        [
			InlineKeyboardButton("Yes", callback_data=f'clear:yes:{context}'),
         	InlineKeyboardButton("No", callback_data=f'clear:no:{context}'),
		],
    ]

	reply_markup = InlineKeyboardMarkup(keyboard)
	bot.send_message(
		chat_id=message.chat.id, 
		text='Are you sure?', 
		reply_markup=reply_markup
	)

def do_clear(bot: TeleBot,operation: str,msg_id: int, chat_id: int,uid: str):
	if (operation != "yes"):
		bot.delete_message(chat_id, msg_id)
		return

	bot.send_message(
		chat_id=chat_id,
		text="Context cleared.",
		reply_to_message_id=msg_id
	)

	session.clear_context(uid)

def handle_conversation(message: Message, bot: TeleBot):
	messages = session.get_session(str(message.from_user.id))
	if len(messages) == 0:
		bot.reply_to(message,"No conversation found.")
		return

	content = ''
	for m in messages:
		content += f'### {m["role"]}\n{m["text"]}\n\n'
	
	bot.reply_to(
		message=message,
		text=escape(content),
		parse_mode="MarkdownV2",
		disable_web_page_preview=True
	)

def handle_revoke(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}'
	keyboard = [
        [
			InlineKeyboardButton("Yes", callback_data=f'revoke:yes:{context}'),
         	InlineKeyboardButton("No", callback_data=f'revoke:no:{context}'),
		],
    ]

	bot.send_message(message.chat.id, 'Are you sure?', reply_markup=InlineKeyboardMarkup(keyboard))

def do_revoke(bot: TeleBot,operation: str,msg_id: int, chat_id: int,uid: str):
	if operation != 'yes':
		bot.delete_message(chat_id, msg_id)
		return

	messages = session.get_session(uid)
	if len(messages) <= 0:
		bot.send_message(
			chat_id=chat_id,
			text="Could not find any message in current conversation",
			reply_to_message_id=msg_id
		)
		return
	
	answer = messages.pop()
	question = messages.pop()
	revoke_list = [question,answer]

	content = ''
	for m in revoke_list:
		content += f'### {m["role"]}\n{m["text"]}\n\n'

	bot.send_message(
		chat_id=chat_id,
		text=escape(content),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)
	session.remove_and_save(
		uid,[ answer['message_id'],question['message_id'] ]
	)
	for m in revoke_list:
		if 'message_id' in m and 'chat_id' in m:	
			bot.delete_message(m['chat_id'], m['message_id'])
	

def register(bot: TeleBot,options: dict):
	bot.set_my_commands([
		BotCommand("search","Enable/Disable Search"),
		BotCommand("style","Change style"),
		BotCommand("conversation","Get current conversation"),
		BotCommand("gpt4_turbo","Enable/Disable GPT4-Turbo"),
		BotCommand("revoke","Revoke message"),
		BotCommand("clear","Clear context"),
	])

	bot.register_message_handler(handle_gpt4_turbo, pass_bot=True, commands=['gpt4_turbo'])
	bot.register_message_handler(handle_style, pass_bot=True, commands=['style'])
	bot.register_message_handler(handle_search, pass_bot=True, commands=['search'])
	bot.register_message_handler(handle_clear, pass_bot=True, commands=['clear'])
	bot.register_message_handler(handle_conversation, pass_bot=True, commands=['conversation'])
	bot.register_message_handler(handle_revoke, pass_bot=True, commands=['revoke'])
	bot.register_message_handler(handle_message, pass_bot=True, content_types=['text'])

	@bot.callback_query_handler(func=lambda call: True)
	def callback_handler(call):
		segments = call.data.split(':')
		uid = str(call.from_user.id)
		target = segments[0]
		operation = segments[1]
		message_id = segments[2]
		chat_id = segments[3]

		if target == 'style':
			do_style_change(bot,operation,message_id,chat_id)
		elif target == 'revoke':
			do_revoke(bot,operation,message_id,chat_id,uid)
		elif target == 'model':
			do_model_change(bot,operation,message_id,chat_id)
		elif target == 'search':
			do_search_change(bot,operation,message_id,chat_id)
		elif target == 'clear':
			do_clear(bot,operation,message_id,chat_id,uid)

		bot.delete_message(call.message.chat.id,call.message.message_id)

	