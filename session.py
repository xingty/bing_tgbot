from pathlib import Path
from telebot.types import Message
import json

class Session():
	def __init__(self):
		self.context = {}
		self._init_context()

	def load_and_filter(self,messages):
		history = []
		for item in reversed(messages):
			if item['role'] == 'breaker':
				break
			
			history.append(item)
		
		history.reverse()
		return history

	def _init_context(self):
		self.session_path = Path(__file__).parent.joinpath('sessions')
		if not self.session_path.exists():
			self.session_path.mkdir(parents=True, exist_ok=True)

		for item in self.session_path.iterdir():
			segments = item.name.split('.')
			if len(segments) != 2:
				print('invalid session file: ' + item.name)
				continue
		
			uid = segments[0]
			file_extension = segments[1]

			if file_extension == 'json':
				self.context[uid] = self.load_and_filter(json.loads(item.read_text()))

	def append_message(self,user_msg: Message, replies: list):
		uid = str(user_msg.from_user.id)
		if uid not in self.context:
			self.context[uid] = []

		conversation = self.context.get(uid)
		messages = [
			{
				"role": 'user',
				"text": user_msg.text,
				"message_id": user_msg.message_id,
				"chat_id": user_msg.chat.id,
				"ts": user_msg.date,
			}
		]

		messages += replies

		conversation += messages
		self.append_to_disk(uid,messages)

	def get_messages(self,uid: str):
		file = self.session_path.joinpath(uid + '.json')
		history = []
		if file.exists():
			history = json.loads(file.read_text())

		return file,history

	def append_to_disk(self,uid,messages):
		file,history = self.get_messages(uid)
		history += messages

		file.write_text(json.dumps(history,ensure_ascii=False))

	def get_session(self,uid: str):
		return self.context.get(uid)

	def remove_and_save(self, uid: str, messages_ids: list):
		file,history = self.get_messages(uid)
		for entry in reversed(history):
			msg_id = entry.get('message_id')
			if msg_id and len(messages_ids) > 0 and msg_id in messages_ids:
				history.remove(entry)
				messages_ids.remove(msg_id)

		file.write_text(json.dumps(history,ensure_ascii=False))

	def clear_context(self,uid: str):
		self.context[uid] = []
		self.append_to_disk(uid,[
			{
				"role": "breaker",
				"message": "clear context"
			}
		])

	def enroll(self,uid: str):
		self.context[uid] = []
		self.append_to_disk(uid,[])