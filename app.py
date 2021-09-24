import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from decouple import config
import re
import datetime

from database import Db


# Initializes your app with  bot token and signing secret
app = App(
    token=config("SLACK_BOT_TOKEN"),
    signing_secret=config("SLACK_SIGNING_SECRET")
)


answers = {} # It stores username with its related questions and  answers

db = Db()
cursor = db.connect()

# Listens to incoming messages that contain "hello"

@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
	print("Hello world")
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
                            "action_id": "radio_buttons-action"
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
                            "action_id": "radio_buttons-fine"
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
def save_survey_response(ack, action, respond, say):
    ack()

    list = convert_stored_response_to_tuple_list(answers)

    print("list", list)
    if list is None or len(list)<2:
        # say("hello")
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
    # print(f'body {body}')

    # print(f'body {body.get("message").get("blocks")}')

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

    # answers[user_id][action_block_id] = value

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

command_out_response = {}


def command_by_day_handler(days, user_id):
    """
    Returns start and end date format
    Args:
      days = str, Days passed as a parameter in command
      user_id = str, Requested user id
    """
    print(f'days: {days}')
    days = int(days)
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=days)

    # start_format = start_date.strftime("%Y-%m-%d")
    # end_format = end_date.strftime("%Y-%m-%d")

    command_out_response[user_id] = {}
    command_out_response[user_id][BLOCK_ID_ABSENT_START] = start_date
    command_out_response[user_id][BLOCK_ID_ABSENT_END] = end_date

    return f"You will be on leave from: *{start_date}* and available from: *{end_date}*. Save?"


COMMAND_OUT_ARGS = {
    '-d': command_by_day_handler
}


@app.command("/out")
def command_absent(ack, say, command):
    ack()
    command_text = command.get("text")

    if command_text:
        mssg = "You have entered incorrect command. Try: `/out` to add manually."
        command_args = command_text.split(" ")
        command_key = command_args[0]

        try:
            command_value = command_args[1]

            user_id = command.get('user_id')

            mssg = COMMAND_OUT_ARGS[command_key](
                command_value, user_id=user_id)

        finally:
            # except (KeyError, IndexError, ValueError):
            say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": mssg
                        },
                    },
                ]
            )
    else:

        today_date = datetime.datetime.today()
        tomorrow_date = today_date + datetime.timedelta(days=1)
        say(
            blocks=[
                {
                    "type": "input",
                    "block_id": BLOCK_ID_ABSENT_START,
                    "element": {
                        "type": "datepicker",
                        # "initial_date": today_date.strftime("%Y-%m-%d"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True
                        },
                        "action_id": "datepicker_out-start"
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
                        # "initial_date": tomorrow_date.strftime("%Y-%m-%d"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True
                        },
                        "action_id": "datepicker_out-end"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Pickup the date you will be coming."
                    }
                },
            ],
        )
    say(
        blocks=[
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Save My Response"
                        },
                        "action_id": "datepicker_out-save"
                    },
                ],
            },
        ]
    )


@app.action("datepicker_out-save")
def save_leave_response(ack, action, respond):
    global command_out_response
    ack()
    print("inside save leave statement")

    print(f'command_out_response {command_out_response}')
    list = convert_stored_response_to_tuple_list(command_out_response, for_leave=True)
    command_out_response = {}
    today_date = datetime.date.today()
    print("list", list)

    if list !=None and len(list) ==3:
        leave_start_date = list[1]
        leave_end_date = list[2]


    if list is None:
        respond("Please provide date value in input filed")
    
    elif len(list) !=3:
        respond("Please provide both leave start and end date!!!")
    elif leave_start_date < today_date or leave_end_date < today_date or leave_start_date==leave_end_date:
        respond("You have entered invalid date. Please enter valid date and try agian")

    else:
        query = """INSERT INTO employee_leave_table(user_id,leave_start_date,leave_end_date)
                VALUES(%s,%s,%s) RETURNING id;"""

        x = cursor.execute(query, list)
        db.commit()
        print("many execute", x)
        respond(f"Absent date has been sucessfully  Saved.")


@app.action(re.compile("datepicker_out-(start|end)"))
def store_leave_start(ack, action, client, body):
    ack()
    print("inside datepicker start or end")
    print(f'body {body}')
    print(f'action {action}')
    action_block_id = action.get('block_id')
    selected_date = action.get('selected_date')
    selected_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
    print(f'selected_date: {selected_date}')

    user_id = body.get('user').get('id')

    if user_id in command_out_response:
        command_out_response[user_id][action_block_id] = selected_date
    else:
        command_out_response[user_id] = {}
        command_out_response[user_id][action_block_id] = selected_date



# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 5000)))
