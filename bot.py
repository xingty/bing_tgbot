import argparse
from telebot import TeleBot
from bing import init_bot
from telebot.types import BotCommand, Message  # type: ignore

def main():
	parser = argparse.ArgumentParser()
	# parser.add_argument("tg_token", help="The token of your telegram bot")
	parser.add_argument(
    '--tg_token',
    type=str,
		required=True,
    help="The token of your telegram bot",
  )
	parser.add_argument(
    '--access_key',
    type=str,
		required=True,
    help="Specify Access Key to use this bot",
  )
	parser.add_argument(
    '--cookie_file',
    type=str,
		required=False,
    help="Path of your cookie file",
  )
	parser.add_argument(
    '--proxy',
    type=str,
		required=False,
    help="proxy server, e.g. http://127.0.0.1:7890",
  )
	parser.add_argument(
    '--locale',
    type=str,
		required=False,
    help="the locale of the proxy server, e.g. en-US",
  )
	options = parser.parse_args()
	print(options)

	bot = TeleBot(options.tg_token)

	init_bot(bot,options)
	print("Bot init done.")

	bot.infinity_polling()

if __name__ == "__main__":
	main()