import os

from dotenv import load_dotenv

load_dotenv()
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']
STORAGE_CHAT_PREFIX = 'GII bot storage '
TOKEN = os.environ['TOKEN']
BAZARIKI_URL = 'https://www.bazaraki.com'
TEMPLATE_DESCRIPTION = '''{name}
price: {price}{price_lowered}
date: {date}{distance}{description}

'''
DISABLE_NOTIFICATIONS = os.getenv('DISABLE_NOTIFICATIONS') == 'True'