import configparser
import logging
import re
from datetime import date, datetime

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import \
    Updater, \
    CommandHandler, \
    ConversationHandler, \
    MessageHandler, \
    CallbackQueryHandler
from telegram.ext.filters import Filters


def get_help_texts():
    """Get help texts from a separate file."""
    HELP_TEXTS = {'global': "Here's what you can do:\n" +
                  "* /start\n" +
                  "* /help [<command>]\n" +
                  "* /event [<date>] [<start_time>] [<end_time>]\n" +
                  "* /info <date> [<start_time>] [<end_time>]\n" +
                  "* /today\n" +
                  "* /tomorrow\n"
                  }
    with open('help_texts.txt') as fh:
        current_text = ""
        for line in fh:
            line = line.strip()
            if len(line) != 0:
                current_text += line + "\n"
            else:
                HELP_TEXTS[current_text.split()[0]] = current_text
                current_text = ""
    if current_text != "":
        HELP_TEXTS[current_text.split()[0]] = current_text
    return HELP_TEXTS


def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    """Build an inline menu."""
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def build_date(tuple):
    """Build a date from its regex."""
    tuple = (tuple[0], tuple[2], tuple[3])
    try:
        day, month, year = list(
            map(lambda x: None if x is None else int(x), tuple)
        )
    except (TypeError):
        return None

    if day is None:  # If day is empty, message has wrong format
        return None

    today = date.today()
    if month is None:  # Both month and year are None
        month = today.month
        year = today.year
        if day < today.day:
            month = month + 1
            if month == 13:
                month = 1
                year = year + 1
    elif year is None:  # Only year is None
        year = today.year
        if month < today.month:
            year = year + 1

    if len(str(year)) == 2:
        year += 2000

    try:
        selected = date(year, month, day)
        if selected < today:
            return None
    except (ValueError):
        return None
    return "%d.%d.%d" % (selected.day, selected.month, selected.year)


def validate_and_format_event(event_data):
    """
    Check that all fields in an event are valid and format it.

    Returns a tuple (boolean, string) where boolean is True when the event
    is valid and false otherwise. When true, the string contains the event
    info. When false, it contains the cause of error.
    """
    if 'n' not in event_data:
        return (False, "Name is required")

    today = date.today()
    defaults = {
        'sd': "%d.%d.%d" % (today.day, today.month, today.year),
        'ed': "%d.%d.%d" % (today.day, today.month, today.year),
        'st': '00:00',
        'et': '23:59'
    }

    for key, value in defaults.items():
        if key not in event_data:
            event_data[key] = value

    # Date and time check
    sd_arr = event_data['sd'].split(".") + event_data['st'].split(":")
    sd_arr = list(map(lambda x: int(x), sd_arr))
    sd = datetime(sd_arr[2], sd_arr[1], sd_arr[0], sd_arr[3], sd_arr[4])

    ed_arr = event_data['ed'].split(".") + event_data['et'].split(":")
    ed_arr = list(map(lambda x: int(x), ed_arr))
    ed = datetime(ed_arr[2], ed_arr[1], ed_arr[0], ed_arr[3], ed_arr[4])

    if (sd > ed):
        return (False, "Event start must be earlier than event end")

    # Event formatting
    event = "*%s*\n" % (event_data['n']) + \
        " From %s\n" % (datetime.strftime(sd, "%d.%m.%Y %H:%M")) + \
        " To %s\n" % (datetime.strftime(ed, "%d.%m.%Y %H:%M"))
    return (True, event)


HELP_TEXTS = get_help_texts()
EVENT_FIELDS = {
    'n': {
        'name': 'Name',
        'regexp': r'(^[^\'"\n]*)$',
        'builder': lambda l: l[0]
    },
    'sd': {
        'name': 'Start date',
        'regexp':
            r'^(\d{1,2})\D?((\d{1,2})\D?(\d{2,4})?)?$',
        'builder': build_date
    },
    'ed': {
        'name': 'End date',
        'regexp':
            r'^(\d{1,2})\D?((\d{1,2})\D?(\d{2,4})?)?$',
        'builder': build_date
    },
    'st': {
        'name': 'Start time',
        'regexp': r'^([0-1]?[0-9]|2[0-4])\D?([0-5][0-9])?$',
        'builder': lambda l: ":".join(
            [elem if elem is not None else "00" for elem in l]
        )
    },
    'et': {
        'name': 'End time',
        'regexp': r'^([0-1]?[0-9]|2[0-4])\D?([0-5][0-9])?$',
        'builder': lambda l: ":".join(
            [elem if elem is not None else "00" for elem in l]
        )
    }
}


def send(update, context, text, reply_markup=None):
    """Send a message in the given context and chat."""
    context.bot.send_message(
        update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )


def not_understood(update, context):
    """Send a message when the text has not been understood."""
    send(update, context, "I do not understand this message")


def start(update, context):
    """Say hello and show available actions."""
    send(update, context, 'Hello!')
    send(update, context, HELP_TEXTS['global'])


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
    reply_markup = InlineKeyboardMarkup(build_menu(
        button_list,
        n_cols=2,
        header_buttons=header_buttons
    ))
    send(update, context, "Select a field to fill it", reply_markup)


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
        event = validate_and_format_event(context.chat_data)
        if (event[0]):
            send(update, context, event[1])
            send(update, context, "This is the created event. " +
                 "To confirm send yes, to keep editing send anything else")
            return 'confirm'
        else:
            send(update, context, event[1])
            return
    context.chat_data['pending'] = type
    send(update, context, "Enter " + EVENT_FIELDS[type]['name'].lower())
    return


def conversation_single_input(update, context):
    """Read and process a value for a single event field."""
    if 'pending' not in context.chat_data:
        send(update, context, "No field selected")
        return
    type = context.chat_data['pending']
    text = update.message.text
    match = re.search(EVENT_FIELDS[type]['regexp'], text)
    if match:
        content = EVENT_FIELDS[type]['builder'](match.groups())
        if content:
            context.chat_data[type] = content
            del context.chat_data['pending']
        else:
            send(update, context, "Invalid value. Try again")
            return
        conversation_single_send_menu(update, context)
        return

    send(update, context, "Invalid format, try again!")


def conversation_single_confirm(update, context):
    """Save a single event."""
    if re.match(r'^[Yy]([Ee][Ss])?$', update.message.text) is not None:
        print(context.chat_data)
        send(update, context, "Event saved")
        return -1
    else:
        conversation_single_send_menu(update, context)
        return 'menu'


def help(update, context):
    """Display full help or help for a command."""
    text = context.args
    if len(text) == 0:
        send(update, context, HELP_TEXTS['global'])
        return
    if text[0] in HELP_TEXTS:
        send(update, context, HELP_TEXTS[text[0]])
    else:
        send(update, context, "This command does not exist")


def add_handlers(dispatcher):
    """Add all handlers in the same place."""
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
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
