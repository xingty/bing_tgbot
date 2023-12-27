

MAX_TEXT_LENGTH = 3900

def messages_to_segments(messages: list):
	segment = ''
	total_len = 0
	segments = []
	for m in messages:
		text = f'### {m["role"]}\n{m["text"]}\n\n'
		text_len = len(text)
		if total_len + text_len > MAX_TEXT_LENGTH:
			segments.append(segment)
			segment = ''
			total_len = 0

		segment += text
		total_len += text_len	
	
	if total_len > MAX_TEXT_LENGTH:
		segment = segment[0:MAX_TEXT_LENGTH-3] + '...'
	
	segments.append(segment)

	return segments