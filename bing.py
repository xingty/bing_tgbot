from EdgeGPT.EdgeGPT import Chatbot,ConversationStyle
from telebot import TeleBot
from telebot.types import Message,BotCommand,InlineKeyboardButton,InlineKeyboardMarkup
from utils.md2tgmd import escape
from utils.text import messages_to_segments,split_to_segments
from threading import Thread
from utils.prompt import build_bing_prompt,parse_search_result
from session import Session
from user_profile import UserProfile
import json,asyncio
import traceback,time
from pathlib import Path

session = Session()
profiles = UserProfile()
cookie_file = None
proxy = None
key = None

# def ask(message: Message, bot: TeleBot, reply_msg_id):
# 	async def execute(cookies):
# 		ai = None
# 		try:
# 			ai = await Chatbot.create(
# 				cookies=cookies,
# 				proxy=proxy
# 			)

# 			uid = str(message.from_user.id)
# 			profile = profiles.load(uid)
# 			search = profile['search']
# 			style = ConversationStyle[profile['style']]

# 			histories = session.get_session(uid)
# 			webpage_context = build_bing_prompt(histories,message.text,profile['prompt'])
# 			response = await ai.ask(
# 				prompt=message.text,
# 				conversation_style=style,
# 				webpage_context=webpage_context,
# 				search_result=search,
# 				no_search=(not search),
# 				mode=profile.get('model'),
# 			)

# 			if 'item' in response and 'result' in response['item']:
# 				result = response['item']['result']
# 				if result and "success" == (result['value']+'').lower():
# 					content = response['item']['result']['message']

# 					search_result = parse_result(response['item'],search)
# 					last_message_id = message.message_id
# 					replies: list = []
# 					segments = split_to_segments(content, search_result)
# 					is_seg = False
					
# 					for seg in segments:
# 						reply = bot.send_message(
# 							chat_id=message.chat.id,
# 							text=escape(seg),
# 							reply_to_message_id=last_message_id,
# 							parse_mode="MarkdownV2",
# 							disable_web_page_preview=True
# 						)
# 						replies.append({
# 							'role': 'assistant',
# 							'text': seg,
# 							'message_id': reply.message_id,
# 							'chat_id': message.chat.id,
# 							'ts': reply.date,
# 							'is_seg': is_seg
# 						})
# 						is_seg = True
# 						last_message_id = reply.message_id
					
# 					session.append_message(message,replies)
				
# 		except Exception as e:
# 			print(traceback.format_exc())
# 			print(e)
# 			bot.reply_to(message,str(e))
# 		finally:
# 			bot.delete_message(message.chat.id, reply_msg_id)
# 			if ai is not None:
# 				await ai.close()

# 	if cookie_file and cookie_file.exists():
# 		cookies = json.loads(cookie_file.read_text())
# 		asyncio.run(execute(cookies))	
# 		return
	
# 	bot.reply_to(message,"Please set cookies first.")

def ask(message: Message, bot: TeleBot, reply_msg_id):
	async def execute(msg: Message, bot: TeleBot, reply_msg_id):
		uid = str(msg.from_user.id)
		profile = profiles.load(uid)
		search = profile['search']
		style = ConversationStyle[profile['style']]
		search_result = []
		offset = 0
		content = ''
		try:
			cookies = json.loads(cookie_file.read_text())
			ai = await Chatbot.create(
				cookies=cookies,
				proxy=proxy
			)

			histories = session.get_session(uid)
			webpage_context = build_bing_prompt(histories,msg.text,profile['prompt'])

			async for final,response in ai.ask_stream (
				prompt=msg.text,
				conversation_style=style,
				search_result=search,
				raw=True,
				webpage_context=webpage_context,
				no_search=(not search),
				mode=profile.get('model'),
			):
				type = response["type"]
				if type == 1 and "messages" in response["arguments"][0]:
					message = response["arguments"][0]["messages"][0]
					msg_type = message.get("messageType")
					
					if msg_type == "InternalSearchResult":
						search_result = search_result + parse_search_result(message)
					elif msg_type is None:
						content = message["text"]
						if message.get("contentOrigin") == "Apology":
							print('message has been revoked')
							print(message)
							content = f"{message.get('text')} -end- (message has been revoked)"

						total = len(content)
						if total - offset >= 15 and total < 4096:
							bot.edit_message_text(
								text=escape(content),
								chat_id=msg.chat.id,
								message_id=reply_msg_id,
								parse_mode="MarkdownV2",
							)
							offset = total
					else:
						print(f'Ignoring message type: {msg_type}')
		except Exception as e:
				print(e)
				bot.edit_message_text(
					text=escape(f'{content}\n\n{str(e)}'),
					chat_id=msg.chat.id,
					message_id=reply_msg_id,
					parse_mode="MarkdownV2",
				)
				await ai.close()
				return

		if len(search_result) > 0:
			content += '\n\n'
			index = 1
			for item in search_result:
				content += f'- [^{index}^] [{item["title"]}]({item["url"]})\n'
				index += 1

		truncated = escape(content)
		if len(truncated) > 4096:
			truncated = truncated[:4095]
		bot.edit_message_text(
			text=truncated,
			chat_id=msg.chat.id,
			message_id=reply_msg_id,
			parse_mode="MarkdownV2",
			disable_web_page_preview=True
		)

		session.append_message(msg,[{
			'role': 'assistant',
			'text': content,
			'message_id': reply_msg_id,
			'chat_id': msg.chat.id,
			'ts': int(time.time()),
		}])

		await ai.close()

	asyncio.run(execute(message,bot,reply_msg_id))

def permission_check(func):
	def wrapper(message: Message, bot: TeleBot):
		uid = str(message.from_user.id)
		if session.get_session(uid) is not None:
			func(message,bot)
		else:
			bot.reply_to(message,"Please enter a valid key to use the system. You can do this by typing '/key key'.")
	
	return wrapper

@permission_check
def handle_message(message: Message, bot: TeleBot):
	if message.text == '/start':
		return
	
	reply_message: Message = bot.reply_to(
		message, 
		"Processing...",
	)

	reply_msg_id = reply_message.message_id
	Thread(target=ask,args=(message,bot,reply_msg_id)).start()

@permission_check
def handle_search(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
	keyboard = [
        [
			InlineKeyboardButton("Enable", callback_data=f'search:on:{context}'),
         	InlineKeyboardButton("disable", callback_data=f'search:off:{context}'),
		],
    ]

	profile = profiles.load(str(message.from_user.id))
	search = profile.get('search',False)

	reply_markup = InlineKeyboardMarkup(keyboard)
	bot.send_message(
		chat_id=message.chat.id, 
		text=escape(f'Curren status of Search: **{("Enable" if search else "Disable")}**'), 
		reply_markup=reply_markup,
		parse_mode="MarkdownV2"
	)

def do_search_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int, uid: str):
	search = operation == "on"

	profiles.update(uid,'search',search)
	bot.send_message(
		chat_id=chat_id,
		text=escape(f'Curren status of Search: **{"Enable" if search else "Disable"}**'),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)

@permission_check
def handle_gpt4_turbo(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
	keyboard = [
        [
			InlineKeyboardButton("On", callback_data=f'model:on:{context}'),
         	InlineKeyboardButton("Off", callback_data=f'model:off:{context}'),
		],
    ]

	profile = profiles.load(str(message.from_user.id))
	model = profile.get('model',None)

	reply_markup = InlineKeyboardMarkup(keyboard)
	bot.send_message(
		chat_id=message.chat.id, 
		text=escape(f'Curren status of gpt4_turbo: **{("on" if model else "off")}**'), 
		reply_markup=reply_markup,
		parse_mode="MarkdownV2"
	)

def do_model_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int, uid: str):
	model = ("gpt4-turbo" if operation == "on" else None)

	profiles.update(uid,'model',model)
	bot.send_message(
		chat_id=chat_id,
		text=escape(f'Curren status of gpt4_turbo: **{"on" if model else "off"}**'),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)

@permission_check
def handle_style(message: Message, bot: TeleBot):
	keyboard = []
	context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
	for m in ConversationStyle._member_names_:
		callback_data = f'style:{m}:{context}'
		keyboard.append(InlineKeyboardButton(m, callback_data=callback_data))

	reply_markup = InlineKeyboardMarkup([keyboard])
	profile = profiles.load(str(message.from_user.id))
	text = json.dumps(profile,indent=2,ensure_ascii=False)
	text = f"Current style: {profile['style']}\n```json\n{text}\n```"

	bot.send_message(
		chat_id=message.chat.id, 
		text=escape(text), 
		reply_markup=reply_markup,
		parse_mode="MarkdownV2"
	)

def do_style_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int, uid: str):
	profiles.update(uid,'style',operation)
	bot.send_message(
		chat_id=chat_id,
		text=escape(f"Current Style has been changed to **{operation}**"),
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2"
	)

@permission_check
def handle_clear(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
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

@permission_check
def handle_conversation(message: Message, bot: TeleBot):
	messages = session.get_session(str(message.from_user.id))
	if len(messages) == 0:
		bot.reply_to(message,"No conversation found.")
		return
	
	messages = [msg for msg in messages if msg['chat_id'] == message.chat.id]
	segments = messages_to_segments(messages)
	last_message_id = message.message_id
	for content in segments:
		reply_msg: Message = bot.send_message(
			chat_id=message.chat.id,
			text=escape(content),
			parse_mode="MarkdownV2",
			disable_web_page_preview=True,
			reply_to_message_id=last_message_id
		)
		last_message_id = reply_msg.message_id

@permission_check
def handle_revoke(message: Message, bot: TeleBot):
	uid = str(message.from_user.id)
	messages = session.get_session(uid)
	if (len(messages) == 0):
		bot.reply_to(message,"No conversation found.")
		return

	context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
	keyboard = [
        [
			InlineKeyboardButton("Yes", callback_data=f'revoke:yes:{context}'),
         	InlineKeyboardButton("No", callback_data=f'revoke:no:{context}'),
		],
    ]

	revoke_list = [messages[-2],messages[-1]]
	content = ''
	for m in revoke_list:
		content += f'### {m["role"]}\n{m["text"]}\n\n'
	
	content = f'Are you sure? This operation will revoke the messages below:\n\n{content}'

	bot.send_message(
		chat_id=message.chat.id, 
		text=escape(content), 
		parse_mode="MarkdownV2",
		reply_markup=InlineKeyboardMarkup(keyboard)
	)

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
	
def handle_key(message: Message, bot: TeleBot):
	uid = str(message.from_user.id)
	if session.get_session(uid) is not None:
		msg = 'You have already been registered in the system. No need to enter the key again.'
	elif message.text.replace('/key ','') == key:
		session.enroll(uid)
		msg = 'Your registration is successful!'
	else:
		msg = 'Invalid key. Please enter a valid key to proceed.'

	bot.reply_to(message, msg)

def handle_profiles(message: Message, bot: TeleBot):
	context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
	keyboard = []
	items = []
	for name in profiles.presets.keys():
		callback_data = f'profile:{name}:{context}'
		if len(items) == 3:
			keyboard.append(items)
			items = []
		items.append(InlineKeyboardButton(name, callback_data=callback_data))
	
	if len(items) > 0:
		keyboard.append(items)
	
	bot.send_message(message.chat.id, 'Presets:', reply_markup=InlineKeyboardMarkup(keyboard))

def do_profile_change(bot: TeleBot,operation: str,msg_id: int, chat_id: int,uid: str):
	profile = profiles.use(uid,operation)
	text = json.dumps(profile,indent=2,ensure_ascii=False)

	bot.send_message(
		chat_id=chat_id,
		reply_to_message_id=msg_id,
		parse_mode="MarkdownV2",
		text=escape(f'```json\n{text}\n```')
	)

def register(bot: TeleBot):
	bot.set_my_commands([
		BotCommand("search","Enable/Disable Search"),
		BotCommand("style","Change style"),
		BotCommand("conversation","Get current conversation"),
		BotCommand("gpt4_turbo","Enable/Disable GPT4-Turbo"),
		BotCommand("profile","Presets"),
		BotCommand("revoke","Revoke message"),
		BotCommand("clear","Clear context"),
		BotCommand("key","Access key"),
	])

	bot.register_message_handler(handle_gpt4_turbo, pass_bot=True, commands=['gpt4_turbo'])
	bot.register_message_handler(handle_style, pass_bot=True, commands=['style'])
	bot.register_message_handler(handle_search, pass_bot=True, commands=['search'])
	bot.register_message_handler(handle_clear, pass_bot=True, commands=['clear'])
	bot.register_message_handler(handle_conversation, pass_bot=True, commands=['conversation'])
	bot.register_message_handler(handle_profiles, pass_bot=True, commands=['profile'])
	bot.register_message_handler(handle_revoke, pass_bot=True, commands=['revoke'])
	bot.register_message_handler(handle_key, pass_bot=True, commands=['key'])
	bot.register_message_handler(handle_message, pass_bot=True, content_types=['text'])

	@bot.callback_query_handler(func=lambda call: True)
	def callback_handler(call):
		message: Message = call.message
		segments = call.data.split(':')
		uid = str(call.from_user.id)
		target = segments[0]
		operation = segments[1]
		message_id = segments[2]
		chat_id = segments[3]
		source_uid = int(segments[4])

		if call.from_user.id != source_uid:
			return

		if target == 'style':
			do_style_change(bot,operation,message_id,chat_id,uid)
		elif target == 'revoke':
			do_revoke(bot,operation,message_id,chat_id,uid)
		elif target == 'model':
			do_model_change(bot,operation,message_id,chat_id,uid)
		elif target == 'search':
			do_search_change(bot,operation,message_id,chat_id,uid)
		elif target == 'clear':
			do_clear(bot,operation,message_id,chat_id,uid)
		elif target == 'profile':
			do_profile_change(bot,operation,message_id,chat_id,uid)
			return

		bot.delete_message(message.chat.id,message.message_id)


def init_bot(bot: TeleBot,options: dict):
	register(bot)

	global cookie_file
	global proxy
	global key
	
	if options.cookie_file:
		cookie_file = Path(options.cookie_file)

	key = options.access_key

	p: str = options.proxy
	if p and (p.startswith("http") or p.startswith("socks5")):
		proxy = p
	


