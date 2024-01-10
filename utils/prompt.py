from utils.md2tgmd import escape
import json

def build_bing_prompt(messages: [],prompt: str,sytem_prompt: str=''):
	content = ''
	if sytem_prompt:
		content = f'[system](#additional_instructions)\n{sytem_prompt}'
	
	if messages and len(messages) > 0:
		for m in messages:
			text = f'{m["text"]}'
			if not m.get("is_seg"):
				text = f'\n[{m["role"]}](#message)\n{text}'
				
			content += text

	content += f'\n[user](#message)\n{prompt}'

	return content

def parse_result(item,search=False):
	if not search:
		return ''
	
	def parse_search_result(message):
		if 'Web search returned no relevant result' in message['hiddenText']:
			return [{
				'title': 'No relevant result',
				'url': None,
				'snippet': message['hiddenText']
		}]
	
		data = []
		for group in json.loads(message['text']).values():
			for item in group:
				data.append({
					'title': item['title'],
					'url': item['url'],
				})

		return data
	
	search_result = []
	if search:
		for m in item['messages']:
			if m.get('messageType') != 'InternalSearchResult':
				continue
			
			search_result += parse_search_result(m)

	content = ''
	if len(search_result) > 0:
		index = 1
		content = f'\n\n**Reference:**\n'
		for item in search_result:
			content += f'- [^{index}^] [{item["title"]}]({item["url"]})\n'
			index += 1

	return content


def parse_search_result(message):
	if 'Web search returned no relevant result' in message['hiddenText']:
		return [{
				'title': 'No relevant result',
				'url': None,
				'snippet': message['hiddenText']
		}]
	
	data = []
	for group in json.loads(message['text']).values():
		for item in group:
			data.append({
				'title': item['title'],
				'url': item['url'],
			})

	return data
