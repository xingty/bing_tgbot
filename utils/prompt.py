from utils.md2tgmd import escape
import json

SYTEM_PROMPT = "You are ChatGPT, a large language model trained by OpenAI.\nLatex inline: $x^2$ \nLatex block: $$e=mc^2$$"

def build_bing_prompt(messages,prompt):
	content = f'[system](#additional_instructions)\n{SYTEM_PROMPT}\n'
	for m in messages:
		content += f'[{m["role"]}](#message)\n{m["text"]}\n'

	content += f'[user](#message)\n{prompt}\n'

	return content

def parse_result(item,search=False):
	content = item['result']['message']

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

	if len(search_result) > 0:
		index = 1
		content += f'\n\n**Reference:**\n'
		for item in search_result:
			content += f'- [^{index}^] [{item["title"]}]({item["url"]})\n'
			index += 1

	return escape(content)

