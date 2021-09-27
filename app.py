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

# Initializes your app with  bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

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
def save_survey_response(ack, action, respond):
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
def store_radio_click(ack, action, client, body):
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
      command: Slack bolt commant argument
    """
    mssg = "You have entered incorrect command. Try: `/out` to add manually."
    user_name = command.get("user_name")

    command_args = shlex.split(command.get("text")) 

    try:
        if len(command_args) > 3:
            raise IndexError()
    
        days = command_args[1]
        absent_text = len(command_args) == 3 and command_args[2] or None

        days = int(days)
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=days)

        start_format = start_date.strftime("%Y-%m-%d")
        end_format = end_date.strftime("%Y-%m-%d")

        errors = validate_absent_data(start_format, end_format, absent_text)

        if len(errors) > 0:
            mssg = "Please correct your values:\n"
            mssg += "\n".join(['> ' + value for key, value in errors.items()])
            return mssg, False

        command_absent_answers[user_name] = {}
        command_absent_answers[user_name][BLOCK_ID_ABSENT_START] = start_format
        command_absent_answers[user_name][BLOCK_ID_ABSENT_END] = end_format
        command_absent_answers[user_name][BLOCK_ID_USER_TEXT] = absent_text

        mssg = f"You will be on leave from: *{start_format}* and available from: *{end_format}*. Save?"
        return mssg, True

    except IndexError:
        mssg = f"You can pass two values: *day* and *leave_text*. Example: `/out -d 1 \"I am travelling.\"`"
    except ValueError as ve:
        mssg = f"Days must be integer."

    return mssg, False

"""
Types of commands available
"""
COMMAND_ABSENT_ARGS = {
    '-d': command_by_day_handler,
}

def get_command_absent_view(start_date=None, end_date=None):
    """
    Return command absent view dictionary.
    Args:
        start_date (datetime): datetime of starting leave (Default: Today)
        start_date (datetime): datetime of coming from leave (Default: Tomorrow)
    """
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
                    "optional": True,
                    "block_id": BLOCK_ID_USER_TEXT,
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

def save_absent(client, user_id, logger):
    """
    Saves the absent record in the database. Shows error message or success message
    Args:
        client:- Slack bolt client 
        user_id:- User id
        logger:- Slack bolt logger
    """
    msg = ""
    try:
        list = convert_stored_response_to_tuple_list(command_absent_answers, True)
        print("list", list)
        # query = """INSERT INTO employee_leave_table(user_id,leave_start_date,leave_end_date,reason_text)
        #         VALUES(%s,%s,%s,%s) RETURNING id;"""

        query = """INSERT INTO employee_leave_table(user_id,leave_start_date,leave_end_date,reason_text)
                VALUES(%s,%s,%s,%s)
                ON CONFLICT ON CONSTRAINT employee_leave_table_user_id_leave_start_date_key 
                DO UPDATE SET
                leave_end_date = EXCLUDED.leave_end_date,
                reason_text = EXCLUDED.reason_text RETURNING id;"""

        cursor.execute(query, list)
        db.commit()
        print(command_absent_answers)
        msg = f"Absent record Saved."

    except Exception as e:
        print(e)
        msg = "There was an error."

    try:
        client.chat_postMessage(channel=user_id, text=msg)
    except Exception as e:
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
    user_id = body.get("user").get("id")

    save_absent(client=client, user_id=user_id, logger=logger)


@app.view("absent_view")
def handle_absent_modal_submission(ack, body, client, view, logger):
    print("--------------")

    user_id = body.get("user").get("id")
    user_name = body.get("user").get("name")

    data = view["state"]["values"]

    absent_start_date = data[BLOCK_ID_ABSENT_START]["absent_date-start"]["selected_date"]
    absent_end_date = data[BLOCK_ID_ABSENT_END]["absent_date-end"]["selected_date"]
    absent_text = data[BLOCK_ID_USER_TEXT]["absent_date-text"]["value"]

    errors = validate_absent_data(absent_start_date, absent_end_date, absent_text)

    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return

    ack()

    command_absent_answers[user_name] = {}
    command_absent_answers[user_name][BLOCK_ID_ABSENT_START] = absent_start_date
    command_absent_answers[user_name][BLOCK_ID_ABSENT_END] = absent_end_date
    command_absent_answers[user_name][BLOCK_ID_USER_TEXT] = absent_text

    save_absent(client=client, user_id=user_id, logger=logger)


@app.command("/out-today")
def command_absent_today(ack, say):
    ack()
    say_mssg = "Members who are on leave:\n"
    cursor.execute("""SELECT DISTINCT user_id 
                        FROM employee_leave_table 
                        WHERE leave_start_date = %s;
                    """, (datetime.date.today(), ))
    users_tuple_list = cursor.fetchall()

    if len(users_tuple_list) == 0:
        say_mssg = "There is no members on leave today :relaxed:"
    else:
        say_mssg += "\n".join([ f"{ind+1}. " + user_id[0] for ind, user_id in enumerate(users_tuple_list)])

    say(say_mssg)


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 5000)))
