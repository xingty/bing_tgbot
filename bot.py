import argparse
from telebot import TeleBot
from bing import register
from telebot.types import BotCommand, Message  # type: ignore

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("tg_token", help="The token of your telegram bot")
	options = parser.parse_args()

	bot = TeleBot(options.tg_token)
	print(options.tg_token)

	register(bot,options)
	print("Bot init done.")

	bot.infinity_polling()

if __name__ == "__main__":
	main()