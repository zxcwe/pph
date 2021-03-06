"""
Fill-in the information in config.json, and execute this file: python3.5 inlinetexbot.py.

The telepot library's (https://github.com/nickoala/telepot) Bot object is used to interface with the Telegram Bot API.
Inline queries are processed using an Answerer: this ensures that one client may have at most one process working on
their query. Old requests by the same user are abandoned: only the latest request is served.

InlineTeXBot creates a folder for each user it receives a query from, and uses this folder as an execution context
for the pdflatex command. This library is removed and re-created when a new query arrives, but no cleanup occurs when
the script terminates.
"""

import asyncio
import telepot
import telepot.async
from telepot.namedtuple import InlineQueryResultPhoto, InlineQueryResultArticle
import logging
import os

from inlinetex_loggers import initialize_loggers
import config_reader
import latex_generator


class InlineTexBot(telepot.async.Bot):
    async def handle(self, msg):
        flavor = telepot.flavor(msg)
        if flavor == 'normal':
            content_type, chat_type, chat_id = telepot.glance(msg, flavor)
            server_logger.info("Normal %s message, %s." % (content_type, chat_id))
            await bot.sendMessage(int(chat_id), "I'm an inline bot. You cannot speak to me directly")
        elif flavor == 'inline_query':
            msg_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
            server_logger.info("Inline equation, %s : %s" % (from_id, query_string))
            answerer.answer(msg)


async def compute_answer(msg):
    def get_error_query():
        return [InlineQueryResultArticle(id="latex_start", title='Invalid LaTex',
                                         description="Couldn't parse your input.",
                                         message_text="Sorry, I lost my way around. Didn't mean to send this.",
                                         type='article')]
    if len(msg['query']) < 1:   # TODO: maybe don't send anything at all?
        results = [InlineQueryResultArticle(id="latex_start", title='Enter LaTeX',
                                            description="Waiting to process your equation. No need to add math mode, "
                                                        "I'll take care of that.",
                                            message_text="Sorry, I lost my way around. Didn't mean to send this.",
                                            thumb_url='http://a1.mzstatic.com/eu/r30/Purple69/v4/b2/f2/92/b2f292f4-a27f'
                                                      '-7ecc-fa20-19d84095e035/icon256.png', thumb_width=256,
                                            thumb_height=256, type='article')]
    else:
        try:
            jpg_url, width, height = await latex_generator.process(str(msg['from']['id']), msg['query'])
        except UnboundLocalError:   # probably failed to generate file
            results = get_error_query()
        else:
            results = [InlineQueryResultPhoto(id='Formatted equation', photo_url=jpg_url,
                                              thumb_url=jpg_url, photo_height=height, photo_width=width)]
    return results

initialize_loggers()

TOKEN = config_reader.token

bot = InlineTexBot(TOKEN)
answerer = telepot.async.helper.Answerer(bot, compute_answer)
server_logger = logging.getLogger('server_logger')

loop = asyncio.get_event_loop()
latex_generator.loop = loop
latex_generator.run_dir = os.getcwd()
loop.create_task(bot.messageLoop())
print("Listening...")

loop.run_forever()
