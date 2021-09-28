import os
import shlex
from slack_bolt import App
from pathlib import Path
from dotenv import load_dotenv

import re
import datetime

from database import Db

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

CHANNEL_ID = os.getenv("CHANNEL_ID", None)

# Initializes your app with  bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# It stores username with its related questions and  answers
answers = {}


db = Db()
cursor = db.connect()

# Listens to incoming messages that contain "hello"


@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Will you be working from home, today?"
                },
                "accessory": {
                    "type": "radio_buttons",
                    "action_id": "radio_buttons-action",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "No",
                                "emoji": True
                            },
                            "value": "0"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Yes",
                                "emoji": True
                            },
                            "value": "1"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Maybe",
                                "emoji": True
                            },
                            "value": "2"
                        }
                    ],
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Are you Fine today?"
                },
                "accessory": {
                    "type": "radio_buttons",
                    "action_id": "radio_buttons-fine",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "No",
                                "emoji": True
                            },
                            "value": "0"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Yes",
                                "emoji": True
                            },
                            "value": "1"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Maybe",
                                "emoji": True
                            },
                            "value": "2"
                        }
                    ],
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                                "type": "plain_text",
                                "text": "Save My Response"
                        },
                        "action_id": "save_response"
                    }
                ]
            }
        ],
        text=f"Save your response <@{message['user']}>!"
    )


def convert_stored_response_to_tuple_list(answers, for_leave=False):
    if for_leave:
        for key, val in answers.items():
            arr=[key]
            for val in val.items():
                arr.append(val[1])
            return arr
    else:
        for key, val in answers.items():
            arr = []
            for val in val.items():
                formatted = (key, )
                arr.append(formatted + val)
            return arr


@app.action("save_response")
def save_survey_response(ack, respond):
    ack()

    list = convert_stored_response_to_tuple_list(answers)

    print("list", list)
    if list is None or len(list)<2:
        respond(f"Please select the suitable answers")
    else:
        query = """INSERT INTO daily_survey(user_id,question_id,answer)
                VALUES(%s,%s,%s) RETURNING id;"""

        x = cursor.executemany(query, list)
        db.commit()
        print("many execute", x)
        respond(f"Survey Saved")


@app.action(re.compile('radio_buttons-(fine|action)'))
def store_radio_click(ack, action, body):
    ack()

    for i in body.get("message").get("blocks"):
        print(f'section: {i}')

    print(f'action {action}')
    print("Inside response handling section")

    action_block_id = action.get('block_id')
    for i in body.get("message").get("blocks"):
        if i.get('block_id') == action_block_id:
            question = i.get('text').get('text')

    print(f'action_block_id {action_block_id}')
    selected_option = action.get('selected_option')
    print(f'selected_option {selected_option}')
    value = selected_option.get('text').get('text')
    print(f'value {value}')

    user = body.get('user')

    print(f'user {user}')
    user_id = user.get('name')
    print(f'user_id {user_id}')

    if user_id in answers:
        answers[user_id][question] = value
    else:
        answers[user_id] = {}
        answers[user_id][question] = value

    print(f'answers: {answers}')


"""
---------------------------------------
Command related text
---------------------------------------
"""
BLOCK_ID_ABSENT_START = "absent_start_date"
BLOCK_ID_ABSENT_END = "absent_end_date"
BLOCK_ID_USER_TEXT = "absent_text"

command_absent_answers = {}


def command_by_day_handler(command):
    """
    Returns start and end date format
    Args:
      days = str, Days passed as a parameter in command
      user_id = str, Requested user id
    """
    print("inside command by day hander func")
    mssg = "You have entered incorrect command. Try: `/out` to add manually."
    print(f'command {command}')
    user_id = command.get("user_name")

    command_args = shlex.split(command.get("text")) 
    print(f'command_args: {command_args}')

    try:
        if len(command_args) > 3:
            print("inside index error if block")
            raise IndexError

        days = command_args[1]
        absent_text = len(command_args) == 3 and command_args[2] or None
        print(f'absent_text is {absent_text}')
        print(f'days: {days}')
        # print(f'absent_text {absent_text}')

        days = int(days)
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=days)

        start_format = start_date.strftime("%Y-%m-%d")
        end_format = end_date.strftime("%Y-%m-%d")

        errors = validate_absent_data(start_format, end_format)

        if len(errors) > 0:
            print("Inisde lenght block")
            mssg = "Please correct your values:\n"
            error_list = [''.join(value) for key, value in errors.items()]
            new_mssg = mssg + "> {}".format("\n".join(error_list))
            return new_mssg, False

        command_absent_answers[user_id] = {}
        command_absent_answers[user_id][BLOCK_ID_ABSENT_START] = start_format
        command_absent_answers[user_id][BLOCK_ID_ABSENT_END] = end_format
        command_absent_answers[user_id][BLOCK_ID_USER_TEXT] = absent_text

        mssg = f"You will be on leave from: *{start_format}* and available from: *{end_format}*. Save?"
        return mssg, True

    except ValueError:
        mssg = f"Days must be integer."
    except IndexError:
        mssg = f"You have to pass two values: *day* and *leave_text*. Example: `/out -d 1 \"I am travelling.\"`"

    print("retuned some value")
    return mssg, False


# TODO: CHECK
def get_absent_by_month_handler(command):
    """
    Handles absent command by month 
    Args:
        command: slack bot command
    Returns dictionary of keys:
        message: str
        value: int , month number
        is_weekend_included: bool, weekend included or not
    """
    response = {
        "message": "You have entered incorrect command. Try: `/out-month` to get absent members this month.",
        "value": None,
        "is_weekend_included": None,
    }

    command_args = shlex.split(command.get("text")) 

    try:
        if len(command_args) > 3:
            raise IndexError()
    
        month_number = command_args[1]
        is_weekend_included = len(command_args) == 3 and command_args[2] or "true"

        month_number = int(month_number)

        if month_number not in range(1,13):
            raise Exception("Month number must be between 1 and 12.")

        if is_weekend_included not in ["true", "false"]:
            raise Exception("Last value can either be *true* or *false*.")

        response["value"] = month_number
        response["message"] = "success"
        response["is_weekend_included"] = is_weekend_included == "true"
        return response, True

    except IndexError:
        mssg = f"You can pass *month number* and *include weekends*. Example: `/out-month -m 1 false`"
    except ValueError as ve:
        mssg = f"Month number must be integer."
    except Exception as e:
        mssg = str(e)

    response["message"] = mssg
    return response, False

"""
Types of commands available
"""
COMMAND_ABSENT_ARGS = {
    '-d': command_by_day_handler,
}
COMMAND_ABSENT_BY_MONTH_ARGS = {
    '-m': get_absent_by_month_handler,
}


def get_command_absent_view(start_date=None, end_date=None):
    print("Inside absent view")
    start_date = start_date or datetime.date.today()
    end_date = end_date or (start_date + datetime.timedelta(days=1))
    
    view = {
            "type": "modal",
            "callback_id": "absent_view",
            "title": {"type": "plain_text", "text": "Leave Form"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": BLOCK_ID_ABSENT_START,
                    "element": {
                        "type": "datepicker",
                        "initial_date": start_date.strftime("%Y-%m-%d"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True
                        },
                        "action_id": "absent_date-start"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Pickup the date you will be out."
                    }
                },
                {
                    "type": "input",
                    "block_id": BLOCK_ID_ABSENT_END,
                    "element": {
                        "type": "datepicker",
                        "initial_date": end_date.strftime("%Y-%m-%d"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True
                        },
                        "action_id": "absent_date-end"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Pickup the date you will be coming."
                    }
                },
                {
                    "type": "input",
                    "block_id": BLOCK_ID_USER_TEXT,
                    "optional":True,
                    "label": {
                        "type": "plain_text", 
                        "text": "What is the reason for leave?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "absent_date-text",
                        "multiline": True
                    }
                },
            ],
        }
    return view


def validate_absent_data(start_date, end_date, text=None):
    """
    Validates the absent data. Returns dictionary of errors
    Args:
        start_date (str): date of starting leave in "%Y-%m-%d" format
        end_date (str): date of coming after leave in "%Y-%m-%d" format
        text (str): Reason for leave 
    """
    errors = {}
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    if start_date.date() < datetime.date.today():
        errors[BLOCK_ID_ABSENT_START] = "You can't take date before today"

    if end_date.date() <= start_date.date():
        errors[BLOCK_ID_ABSENT_END] = "You can't take date before starting date"
    
    return errors

def save_absent(client, user_id, username, logger):
    """
    Saves the absent record in the database. Shows error message or success message
    Args:
        client:- Slack bolt client 
        user_id:- User id
        logger:- Slack bolt logger
    """
    msg = ""
    try:
        print(f'client {client}')
        list = convert_stored_response_to_tuple_list(command_absent_answers, for_leave=True)
        print("list", list)
        start_date = list[1]
        end_date = list[2]
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        print(start_date)
        days = (end_date-start_date).days
        list.append(days)
        print(f"DAYS: {days}")
        print(f'list {list}')
        channels = [user_id, ]
        if CHANNEL_ID:
            channels.append(CHANNEL_ID)
        print(f"channels {channels}")

        # Save to db
        query = """INSERT INTO employee_leave (user_id,leave_start_date,leave_end_date,remarks,leave_days)
                VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, leave_start_date) 
                DO UPDATE SET
                leave_end_date = EXCLUDED.leave_end_date,
                remarks = EXCLUDED.remarks,
                leave_days = EXCLUDED.leave_days
                RETURNING id;"""

        cursor.execute(query, list)
        db.commit()
        print(command_absent_answers)
        msg = f"{username} is in leave from {list[1]} to {list[2]}"
        for ch in channels:
            client.chat_postMessage(channel=ch, text=msg)

    except Exception as e:
        print(e)
        msg = "There was an error."
        logger.exception(f"Failed to post a message {e}")
        
"""
--------------------
Below are all slack bolt listeners
--------------------
"""

@app.command("/out")
def command_absent(ack, say, command, client, body):
    ack()
    print(command)
    command_text = command.get("text")

    if command_text:
        mssg = "You have entered incorrect command. Try: `/out` to add manually."
        command_args = shlex.split(command_text) 
        command_key = command_args[0]

        is_valid = False

        try:
            func = COMMAND_ABSENT_ARGS[command_key]
            mssg, is_valid = func(command)

            if is_valid:
                say(
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": mssg
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Save My Response"
                                    },
                                    "action_id": "absent_date-save"
                                },
                            ],
                        },
                    ]
                )

        except KeyError:
            available_texts = ", ".join([''.join(key) for key, value in COMMAND_ABSENT_ARGS.items()])
            mssg = f"Incorrect command parameter: `{command_text}`, available are: `{available_texts}`"

        if not is_valid:
            say(mssg)
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_command_absent_view(),
        )


@app.action("absent_date-save")
def save_leave_response(ack, body, client, logger):
    ack()
    username = body.get("user").get("username")
    user_id = body.get("user").get("id")

    save_absent(client=client, user_id=user_id, logger=logger, username=username)


@app.view("absent_view")
def handle_absent_modal_submission(ack, body, client, view, logger):
    print("Inside absent modal submit")
    print(f'body: {body}')
    username = body.get("user").get("username") 
    user_id = body.get("user").get("id")
    print(f'username: {username}')

    data = view["state"]["values"]

    absent_start_date = data[BLOCK_ID_ABSENT_START]["absent_date-start"]["selected_date"]
    absent_end_date = data[BLOCK_ID_ABSENT_END]["absent_date-end"]["selected_date"]
    absent_text = data[BLOCK_ID_USER_TEXT]["absent_date-text"]["value"]

    errors = validate_absent_data(absent_start_date, absent_end_date, absent_text)

    if len(errors) > 0:
        print(f'errors {errors}')
        ack(response_action="errors", errors=errors)
        return

    ack()

    command_absent_answers[username] = {}
    command_absent_answers[username][BLOCK_ID_ABSENT_START] = absent_start_date
    command_absent_answers[username][BLOCK_ID_ABSENT_END] = absent_end_date
    command_absent_answers[username][BLOCK_ID_USER_TEXT] = absent_text

    save_absent(client=client, user_id=user_id, logger=logger, username=username)


@app.command("/out-today")
def command_absent_today(ack, say):
    ack()
    say_mssg = "Members who are on *leave today*:\n"
    cursor.execute("""SELECT DISTINCT user_id 
                        from employee_leave
                        WHERE ((current_date-leave_start_date)= 0 or sign(current_date-leave_start_date)=1) 
                        AND ((current_date-leave_start_date)<(leave_end_date-leave_start_date));
                    """)
    users_tuple_list = cursor.fetchall()

    if len(users_tuple_list) == 0:
        say_mssg = "There is no members on leave today :relaxed:"
    else:
        say_mssg += "\n".join([ f"{ind+1}. " + user_id[0] for ind, user_id in enumerate(users_tuple_list)])

    say(say_mssg)


@app.command("/out-month")
def command_absent_month(ack, say, command):
    ack()

    command_text = command.get("text")
    month_number = datetime.datetime.now().month
    is_weekend_included = True

    if command_text:
        mssg = "You have entered incorrect command. Try: `/out-month` to get absent members this month."
        command_args = shlex.split(command_text) 
        command_key = command_args[0]

        is_valid = False

        try:
            func = COMMAND_ABSENT_BY_MONTH_ARGS[command_key]
            data, is_valid = func(command)

            mssg = data.get("message")

            if is_valid:
                month_number = data.get("value")
                is_weekend_included = data.get("is_weekend_included")

        except KeyError:
            available_texts = ", ".join([''.join(key) for key, value in COMMAND_ABSENT_BY_MONTH_ARGS.items()])
            mssg = f"Incorrect command parameter: `{command_text}`, available are: `{available_texts}`"
            
        if not is_valid:
            say(mssg)
            return

    '''
    Ref: https://dba.stackexchange.com/a/55998
    '''
    sql = """SELECT
                user_id,
                EXTRACT('MONTH' FROM days.s) AS MONTH,
                COUNT(*) AS d
                FROM employee_leave el
                CROSS JOIN LATERAL (
                    SELECT * FROM generate_series(el.leave_start_date, el.leave_end_date - interval '1 day', INTERVAL '1 day') s
                ) days        
                WHERE EXTRACT('MONTH' FROM days.s) = %s
            """

    if is_weekend_included:
        sql += " GROUP BY 1, 2 ORDER BY d DESC;"
    else:
        sql += " AND EXTRACT('ISODOW' FROM days.s) < 6 GROUP BY 1, 2 ORDER BY d DESC;"
    
    cursor.execute(sql, (month_number,))

    users_tuple_list = cursor.fetchall()

    if len(users_tuple_list) == 0:
        say("There is no members on leave in the month :relaxed:")
    else:
        title_txt = "List of members with absent count "
        title_txt = is_weekend_included and f"{title_txt}:" or f"{title_txt} (weekends excluded):"
        mssg = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "text": title_txt,
                        "type": "mrkdwn"
                    },
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Name*"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Leave Days*"
                        },
                    ]
                }
            ]
        }
        print(users_tuple_list)
        for user in users_tuple_list:
            for i in [0, 2]:
                col_dict = {
                    "type": "plain_text"
                }
                col_dict["text"] = str(user[i])
                mssg["blocks"][0]["fields"].append(col_dict)

        say(**mssg)


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 5000)))
