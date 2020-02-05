# Telegram planner bot

/start
/help [<command>]
/event <event name> [<date>] [<start_time>] [<end_time>]
/info <date> [<start_time>] [<end_time>]
/today
/tomorrow

Assume that today is Monday. Options are:
* Today
* Monday: next Monday
* Monday2: Monday two weeks from now
* 17: this month's 17, next month's 17 if today is >17.
* 17/2: this year's 17/2, next year's 17/2 if today is >17/2
* 17/2/20: exact date

Assume that it is 13:00. Options are:
* Empty: all day.
* 15: at 15:00
* 15:30, 1530: at 15:30.
