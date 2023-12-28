

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

def split_by_length(text: str, length: int=MAX_TEXT_LENGTH):
	return [text[i:i+length] for i in range(0, len(text), length)]

def split_to_segments(text: str, search_result: str, length: int=MAX_TEXT_LENGTH):
	segments = split_by_length(text, length)
	if (len(segments[-1]) + len(search_result)) > length:
		segments.append(search_result)
	else:
		segments[-1] = segments[-1] + '\n\n' + search_result
	
	return segments