"""Utility functions for planner bot."""
from datetime import date, datetime


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


def reverse_date(date):
    """Reverse a date separated by '.'."""
    arr = date.split(".")
    arr.reverse()
    return ".".join(arr)


def send(update, context, text, reply_markup=None):
    """Send a message in the given context and chat."""
    context.bot.send_message(
        update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )
