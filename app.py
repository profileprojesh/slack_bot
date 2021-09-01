import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pathlib import Path;
from dotenv import  load_dotenv;
import json

from slack_bolt.logger import messages

env_path = Path('.') / '.env';
load_dotenv(dotenv_path=env_path)

# Initializes your app with  bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

answers={}

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
                    "action_id":"save_response"
				}
			]
		}
        ],
        text=f"Save your response <@{message['user']}>!"
    )

@app.action("save_response")
def save_survey_response(ack,action,respond):
    # Acknowledge the action
    ack()
    respond(f"Survey Saved")


@app.action("radio_buttons-action")
def store_radio_click(ack,action,client,body,user):
    ack()
	
    print(action)

    action_block_id= action.get('block_id')
    selected_option= action.get('selected_option')

    value = selected_option.get('value')

    user = body.get('user')
    user_id = user.get('id')
  
    print("user_id",user_id)
    print("action_block",action_block_id)
    print("value",value)

    # answers[user_id][action_block_id] = value

    if user_id in answers:
        answers[user_id][action_block_id]=value
    else:
        answers[user_id]={}
        answers[user_id][action_block_id] = value
    print(answers)

@app.action("radio_buttons-fine")
def store_radio_click(ack,action,client,body,user):
    ack()
	
    print(action)

    action_block_id= action.get('block_id')
    selected_option= action.get('selected_option')

    value = selected_option.get('value')

    user = body.get('user')
    user_id = user.get('id')
  
    print("user_id",user_id)
    print("action_block",action_block_id)
    print("value",value)

    # answers[user_id][action_block_id] = value

    if user_id in answers:
        answers[user_id][action_block_id]=value
    else:
        answers[user_id]={}
        answers[user_id][action_block_id] = value
    print(answers)


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 5000)))
