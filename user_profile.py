from pathlib import Path
import json

DEFAULT_PROFILE = {
	"prompt": "You are ChatGPT, a large language model trained by OpenAI.\nLatex inline: $x^2$\nLatex block: $$e=mc^2$$",
	"style": "precise",
	"search": False,
	"model": None,
}

class UserProfile:
	def __init__(self):
		self.maps: dict = {}
		self.profile_path: Path = Path(__file__).parent.joinpath('sessions/profiles')
		self.presets = {}
		self._init_context(self.profile_path)
	
	def _init_context(self,path: Path):
		if not path.exists():
			path.mkdir(parents=True, exist_ok=True)

		for item in path.iterdir():
			segments = item.name.split('.')
			if len(segments) != 2:
				print('invalid profile: ' + item.name)
				continue
		
			uid = segments[0]
			file_extension = segments[1]

			if file_extension == 'json':
				self.maps[uid] = json.loads(item.read_text())

		file = Path(__file__).parent.joinpath('presets.json')
		presets: [] = json.loads(file.read_text())
		for preset in presets:
			self.presets[preset['role']] = preset

	def load(self,uid: str):
		profile: dict = self.maps.get(uid)
		if profile is None:
			profile = DEFAULT_PROFILE.copy()
			self.maps[uid] = profile

		return profile

	def save(self,uid: str,profile: dict):
		file = self.profile_path.joinpath(uid + '.json')
		file.write_text(json.dumps(profile))

	def update(self,uid: str,file_name: str,value):
		profile = self.maps.get(uid) or DEFAULT_PROFILE.copy()
		profile[file_name] = value
		self.save(uid,profile)

	def update_all(self,uid,profile):
		self.maps[uid] = profile
		self.save(uid,profile)

	def create(self,uid):
		profile = DEFAULT_PROFILE.copy()
		self.maps[uid] = profile
		self.save(uid,profile)
	
	def use(self,uid: str,profile_name: str):
		profile = self.presets.get(profile_name) or DEFAULT_PROFILE.copy()
		old = self.maps.get(uid) or {}
		profile['model'] = old.get('model')

		self.update_all(uid,profile)

		return profile
