import os
import shlex
from slack_bolt import App
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request
from slack_bolt.adapter.flask import SlackRequestHandler

import re
import ast
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

def get_question_blocks(questions):
    def get_question_options(options):
        dict_list = []
        for k, v in options.items():
            dict = {
                    "text": {
                        "type": "plain_text",
                        "text": v,
                        "emoji": True
                    },
                    "value": k
                }
            dict_list.append(dict)
        return dict_list

    blocks = []
    for question in questions:
        dict = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": question[1]
                },
                "block_id": str(question[0]),
                "accessory": {
                    "type": question[2],
                    "action_id": question[3],
                    "options": get_question_options(question[4])
                }
            }
        blocks.append(dict)
    return blocks


@app.message("hello")
def message_hello(message, say):
    cursor.execute("SELECT * FROM question")
    questions = cursor.fetchall()

    blocks = get_question_blocks(questions)

    submit_dict = {
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
    blocks.append(submit_dict)
    say(
        blocks=blocks,
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

    if list is None or len(list)<2:
        respond(f"Please select the suitable answers")
    else:
        query = """INSERT INTO daily_survey(user_id,question_id,answer)
                VALUES(%s,%s,%s) RETURNING id;"""

        x = cursor.executemany(query, list)
        db.commit()
        respond(f"Survey Saved")


@app.action(re.compile('radio_buttons-(fine|action)'))
def store_radio_click(ack, action, body):
    ack()

    question_id = action.get('block_id')

    selected_option = action.get('selected_option')
    value = selected_option.get('text').get('text')

    user = body.get('user')

    user_id = user.get('name')

    if user_id in answers:
        answers[user_id][question_id] = value
    else:
        answers[user_id] = {}
        answers[user_id][question_id] = value



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
    mssg = "You have entered incorrect command. Try: `/out` to add manually."
    user_id = command.get("user_name")

    command_args = shlex.split(command.get("text")) 

    try:
        if len(command_args) > 3:
            raise IndexError

        days = command_args[1]
        absent_text = len(command_args) == 3 and command_args[2] or None

        days = int(days)
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=days)

        start_format = start_date.strftime("%Y-%m-%d")
        end_format = end_date.strftime("%Y-%m-%d")

        errors = validate_absent_data(start_format, end_format)

        if len(errors) > 0:
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

    return mssg, False


def base_get_absent_handler(command, for_month=True):
    """
    Handles absent command by month 
    Args:
        command: str, slack bot command
        for_month: bool, month or year 
    Returns dictionary of keys:
        message: str
        value: int , month number
        is_weekend_included: bool, weekend included or not
    """
    handler_text = for_month and "month" or "year"

    mssg = f"You have entered incorrect command. Try: `{for_month and '/out-month' or '/out-year'}` to get absent members this {handler_text}."
    response = {
        "message": mssg,
        "value": None,
        "is_weekend_included": None,
    }

    command_args = re.findall(r'\w+|\[\w+.+\w+\]', command.get("text"))
    # command_args = shlex.split(command.get("text"))

    try:
        if len(command_args) > 3:
            raise IndexError()

        date_range = None
    
        month_year_number = command_args[1]
        is_weekend_included = len(command_args) == 3 and command_args[2] or "true"

        if month_year_number.startswith("[") and month_year_number.endswith("]"):
            date_range = ast.literal_eval(str(month_year_number))

            if len(date_range) > 2:
                raise Exception("List can only have two elements: _start_ and _end (included)_.")
        else:
            month_year_number = int(month_year_number)
            date_range = [month_year_number, month_year_number]


        if int(date_range[0]) > int(date_range[1]):
            raise Exception("List first element must be less than later one.")
        
        if for_month:
            if int(date_range[0]) not in range(1, 13) or int(date_range[1]) not in range(1, 13):
                raise Exception("Month number must be between 1 and 12.")

        else:
            if int(date_range[0]) < 1980 or int(date_range[1]) < 1980:
                raise Exception("Year must be valid.")

        if is_weekend_included not in ["true", "false"]:
            raise Exception("Last value can either be *true* or *false*.")

        response["value"] = date_range
        response["message"] = "success"
        response["is_weekend_included"] = is_weekend_included == "true"
        return response, True

    except IndexError:
        cmd_ex = for_month and "/out-month -m 1 false" or "/out-year -y 2021 false" 
        mssg = f"You can pass *month number* and *include weekends*. Example: `{cmd_ex}`"
    except ValueError as ve:
        mssg = f"{handler_text.capitalize()} number must be integer."
    except Exception as e:
        mssg = str(e)

    response["message"] = mssg
    return response, False


def get_absent_by_month_handler(command):
    return base_get_absent_handler(command=command, for_month=True)


def get_absent_by_year_handler(command):
    return base_get_absent_handler(command=command, for_month=False)


"""
Types of commands available
"""
COMMAND_ABSENT_ARGS = {
    '-d': command_by_day_handler,
}
COMMAND_ABSENT_BY_MONTH_ARGS = {
    '-m': get_absent_by_month_handler,
}
COMMAND_ABSENT_BY_YEAR_ARGS = {
    '-y': get_absent_by_year_handler,
}

def get_command_absent_view(start_date=None, end_date=None):
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
        list = convert_stored_response_to_tuple_list(command_absent_answers, for_leave=True)
        start_date = list[1]
        end_date = list[2]
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        days = (end_date-start_date).days
        list.append(days)
        channels = [user_id, ]
        if CHANNEL_ID:
            channels.append(CHANNEL_ID)

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
        msg = f"{username} is in leave from {list[1]} to {list[2]}"
        for ch in channels:
            client.chat_postMessage(channel=ch, text=msg)

    except Exception as e:
        msg = "There was an error."
        logger.exception(f"Failed to post a message {e}")
        

def get_sql_for_year_month(for_month, is_weekend_included):
    """
    Returns sql query to retrieve absent record by month or year
    Args:
        for_month: bool, sql for month or year
        is_weekend_included: bool
    """
    sql = ""
    if for_month:
        sql = """SELECT
                user_id,
                EXTRACT('MONTH' FROM days.s) AS MONTH,
                COUNT(*) AS d
                FROM employee_leave el
                CROSS JOIN LATERAL (
                    SELECT * FROM generate_series(el.leave_start_date, el.leave_end_date - interval '1 day', INTERVAL '1 day') s
                ) days        
                WHERE EXTRACT('MONTH' FROM days.s) BETWEEN %s AND %s 
            """

        if is_weekend_included:
            sql += " GROUP BY 1, 2 ORDER BY d DESC;"
        else:
            sql += " AND EXTRACT('ISODOW' FROM days.s) < 6 GROUP BY 1, 2 ORDER BY d DESC;"
    else:
        sql = """SELECT
                    user_id,
                    EXTRACT('YEAR' FROM days.s) AS YEAR,
                    COUNT(*) AS d
                    FROM employee_leave el
                    CROSS JOIN LATERAL (
                        SELECT * FROM generate_series(el.leave_start_date, el.leave_end_date - interval '1 day', INTERVAL '1 day') s
                    ) days        
                    WHERE EXTRACT('YEAR' FROM days.s) BETWEEN %s AND %s
                """

        if is_weekend_included:
            sql += " GROUP BY 1, 2 ORDER BY d DESC;"
        else:
            sql += " AND EXTRACT('ISODOW' FROM days.s) < 6 GROUP BY 1, 2 ORDER BY d DESC;"
    return sql



def base_command_absent_by_month_year(say, command, for_month=True, **kwargs):
    """
    Base function to handle absent by month or year command
    Args:
        say: Slack bolt say
        command: Slack bolt command
        for_month: bool, command for month or not
        **kwargs
    """

    command_text = command.get("text")
    is_weekend_included = True


    date_text = kwargs["text"]
    date_range = kwargs["number"] 
    command_args_const = kwargs["constant"]

    if command_text:
        cm_text = for_month and "/out-month" or "/out-year"
        mssg = f"You have entered incorrect command. Try: `{cm_text}` to get absent members this {date_text}."
        command_args = shlex.split(command_text) 
        command_key = command_args[0]

        is_valid = False

        try:
            func = command_args_const[command_key]
            data, is_valid = func(command)

            mssg = data.get("message")

            if is_valid:
                date_range = data.get("value")
                is_weekend_included = data.get("is_weekend_included")

        except KeyError:
            available_texts = ", ".join([''.join(key) for key, value in command_args_const.items()])
            mssg = f"Incorrect command parameter: `{command_text}`, available are: `{available_texts}`"
            
        if not is_valid:
            say(mssg)
            return

    sql = get_sql_for_year_month(for_month, is_weekend_included)
    
    cursor.execute(sql, date_range)

    users_tuple_list = cursor.fetchall()

    if len(users_tuple_list) == 0:
        say(f"There is no members on leave in the {date_text} :relaxed:")
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
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"""``` {'-'*40:^40} {'-'*15:^15} {'-'*15:^15}\n|{'NAME':^40}|{date_text.upper():^15}|{'LEAVE DAYS':^15}|\n {'='*40:^40} {'='*15:^15} {'='*15:^15} \n"""
                    }
                }
            ]
        }

        for user in users_tuple_list:
            my_string = f"""|{user[0]:^40}|{int(user[1]):^15}|{user[2]:^15}|\n {'-'*40:^40} {'-'*15:^15} {'-'*15:^15} \n"""
            mssg["blocks"][1]["text"]["text"] += my_string

        mssg["blocks"][1]["text"]["text"] += "```"
        say(**mssg)



# helper function to find out weather a person is valid to take leave or not
def check_employee_leave_validity(start_date, end_date):
    """
    This takes start_date and end_date of user stored in database as arguments  and returns a Boolean value to ascertain validatity of user to take leave.
    """
    valid = True
    days = end_date-start_date
    today = datetime.date.today()
    days_pass = today-start_date
    if days_pass < days:
        valid = False
    return valid


"""
--------------------
Below are all slack bolt listeners
--------------------
"""
@app.command("/out")
def command_absent(ack, say, command, client, body):
    ack()
    command_text = command.get("text")
    user_id = body.get('user_name')
    cursor.execute("SELECT * FROM employee_leave where user_id = %s ORDER BY leave_start_date desc;",(user_id,))
    x = cursor.fetchall()
    if x:
        start_date = x[0][2]
        end_date = x[0][3]
        is_able=check_employee_leave_validity(start_date, end_date)
        if not is_able:
            formated_date = datetime.datetime.strftime(end_date, "%Y-%m-%d")
            say(f"Oops!! You are currently in leave till {formated_date}.")
            return
    # db.commit()

    if command_text:
        mssg = "You have entered incorrect command. Try: `/out` to add manually."
        command_args = shlex.split(command_text) 
        command_key = command_args[0]

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
            else:
                say(mssg)

        except KeyError:
            available_texts = ", ".join([''.join(key) for key, value in COMMAND_ABSENT_ARGS.items()])
            mssg = f"Incorrect command parameter: `{command_text}`, available are: `{available_texts}`"
            say(mssg)
        except Exception:
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
    username = body.get("user").get("username") 
    user_id = body.get("user").get("id")

    data = view["state"]["values"]

    absent_start_date = data[BLOCK_ID_ABSENT_START]["absent_date-start"]["selected_date"]
    absent_end_date = data[BLOCK_ID_ABSENT_END]["absent_date-end"]["selected_date"]
    absent_text = data[BLOCK_ID_USER_TEXT]["absent_date-text"]["value"]

    errors = validate_absent_data(absent_start_date, absent_end_date, absent_text)

    if len(errors) > 0:
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
    month_number = datetime.datetime.today().month

    kwargs = {
        "text": "month",
        "number": [month_number, month_number] ,
        "constant": COMMAND_ABSENT_BY_MONTH_ARGS,
    }

    base_command_absent_by_month_year(say=say, command=command, for_month=True, **kwargs)


@app.command("/out-year")
def command_absent_year(ack, say, command):
    ack()
    year_number = datetime.datetime.today().year

    kwargs = {
        "text": "year",
        "number": [year_number, year_number],
        "constant": COMMAND_ABSENT_BY_YEAR_ARGS,
    }

    base_command_absent_by_month_year(say=say, command=command, for_month=False, **kwargs)


flask_app = Flask(__name__)
slack_request_handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return slack_request_handler.handle(request)

if __name__ == "__main__":
    flask_app.run(
        port=int(os.getenv("PORT", 5000))
    )
