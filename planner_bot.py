import configparser
import logging
import re
import dbutil
import util
from datetime import datetime, timedelta

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import \
    Updater, \
    CommandHandler, \
    ConversationHandler, \
    MessageHandler, \
    CallbackQueryHandler
from telegram.ext.filters import Filters


HELP_TEXTS = util.get_help_texts()


def not_understood(update, context):
    """Send a message when the text has not been understood."""
    util.send(update, context, "I do not understand this message")


def start(update, context):
    """Say hello and show available actions."""
    if dbutil.is_authorised(update.effective_user.id):
        util.send(update, context, 'Hello!')
        util.send(update, context, HELP_TEXTS['global'])
    else:
        dbutil.add_user(update.effective_user.id)
        util.send(update, context, 'You are not authorised. Contact admin')


def conversation_single_send_menu(update, context):
    """Send the inline menu for single event conversation."""
    data = context.chat_data
    IKB = InlineKeyboardButton
    header_buttons = IKB(
        data['n'] if 'n' in data else "Name",
        callback_data='n'
    )
    button_list = [
        IKB(data['sd'] if 'sd' in data else "Start date", callback_data='sd'),
        IKB(data['st'] if 'st' in data else "Start time", callback_data='st'),
        IKB(data['ed'] if 'ed' in data else "End date", callback_data='ed'),
        IKB(data['et'] if 'et' in data else "End time", callback_data='et'),
        IKB("Done", callback_data='d')
    ]
    reply_markup = InlineKeyboardMarkup(util.build_menu(
        button_list,
        n_cols=2,
        header_buttons=header_buttons
    ))
    util.send(update, context, "Select a field to fill it", reply_markup)


def conversation_single_start(update, context):
    """Create a new event."""
    text = context.args
    if len(text) == 0:
        conversation_single_send_menu(update, context)
        return 'menu'


def conversation_single_menu(update, context):
    """Read the clicked inline button and prompt for content."""
    type = update.callback_query.data
    if (type == 'd'):
        event = util.validate_and_format_event(context.chat_data)
        if (event[0]):
            util.send(update, context, event[1])
            util.send(update, context,
                      "This is the created event. " +
                      "To confirm send yes, to keep editing " +
                      "send anything else")
            return 'confirm'
        else:
            util.send(update, context, event[1])
            return
    context.chat_data['pending'] = type
    util.send(update, context,
              "Enter " + util.EVENT_FIELDS[type]['name'].lower())
    return


def conversation_single_input(update, context):
    """Read and process a value for a single event field."""
    if 'pending' not in context.chat_data:
        util.send(update, context, "No field selected")
        return
    type = context.chat_data['pending']
    text = update.message.text
    match = re.search(util.EVENT_FIELDS[type]['regexp'], text)
    if match:
        content = util.EVENT_FIELDS[type]['builder'](match.groups())
        if content:
            context.chat_data[type] = content
            del context.chat_data['pending']
        else:
            util.send(update, context, "Invalid value. Try again")
            return
        conversation_single_send_menu(update, context)
        return

    util.send(update, context, "Invalid format, try again!")


def conversation_single_confirm(update, context):
    """Save a single event."""
    if re.match(r'^[Yy]([Ee][Ss])?$', update.message.text) is not None:
        e = context.chat_data
        dbutil.add_event(dbutil.Event(e['n'], e['sd'], e['ed'],
                                      e['st'], e['et']))
        util.send(update, context, "Event saved")
        return -1
    else:
        conversation_single_send_menu(update, context)
        return 'menu'


def help(update, context):
    """Display full help or help for a command."""
    text = context.args
    if len(text) == 0:
        util.send(update, context, HELP_TEXTS['global'])
        return
    if text[0] in HELP_TEXTS:
        util.send(update, context, HELP_TEXTS[text[0]])
    else:
        util.send(update, context, "This command does not exist")


def get_events(update, context, sd, ed, st="00:00", et="23:59"):
    """Get and send events for the given date and time."""
    r = util.reverse_date
    events = dbutil.get_events(r(sd), st, r(ed), et)
    if not events:
        util.send(update, context, "No events available")
    for event in events:
        util.send(update, context, event.as_message())


def get_today(update, context):
    """Get events for today."""
    today = datetime.utcnow()
    date = today.strftime("%d.%m.%Y")
    get_events(update, context, date, date)


def get_tomorrow(update, context):
    """Get events for tomorrow."""
    tomorrow = datetime.utcnow() + timedelta(days=1)
    date = tomorrow.strftime("%d.%m.%Y")
    get_events(update, context, date, date)


def get_events_for(update, context):
    """Get events for a specific date."""
    text = update.message.text
    match = re.search(util.EVENT_FIELDS['sd']['regexp'], text)
    if match:
        content = util.build_date(match.groups())
        if content:
            get_events(update, context, content, content)
        else:
            util.send(update, context, "Invalid value. Try again")
    else:
        util.send(update, context, "Something very bad happened")


def add_handlers(dispatcher):
    """Add all handlers in the same place."""
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(MessageHandler(
        Filters.regex(re.compile(r'^today$', re.IGNORECASE)),
        get_today
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.regex(re.compile(r'^tomorrow$', re.IGNORECASE)),
        get_tomorrow
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.regex(util.EVENT_FIELDS['sd']['regexp']),
        get_events_for
    ))
    dispatcher.add_handler(ConversationHandler(
        [CommandHandler('single', conversation_single_start)],
        {
            'menu': [
                CallbackQueryHandler(conversation_single_menu),
                MessageHandler(Filters.text, conversation_single_input)
            ],
            'confirm': [
                MessageHandler(Filters.text, conversation_single_confirm)
            ]
        },
        [
            not_understood
        ]
    ))
    dispatcher.add_handler(MessageHandler(Filters.text, not_understood))


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'DEFAULT' not in config:
        print("Config file needs a DEFAULT section")
        exit(1)

    token = config['DEFAULT']['token']
    bot = telegram.Bot(token=token)
    print(bot.get_me())

    updater = Updater(token=token, use_context=True)
    add_handlers(updater.dispatcher)

    updater.start_polling()
