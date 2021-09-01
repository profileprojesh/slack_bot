
class Survey:

    START_TEXT={
        'type':'section',
        'text':{
            'type':'mrkdwn',
            'text':"Welcome"
        }
    }

    DIVIDER={
        'type':'divider'
    }
    def __init__(self,channel,user,):
        self.channel = channel
        self.user = user
        self.icon_emoji = ':robot_face:'
        self.timestamp = ''
        self.completed = False

    def get_message(self):
        return {
            'ts':self.timestamp,
            'channel':self.channel,
            'username':'welcome Robot!',
            'icon_emoji':self.icon_emoji,
            'blocks':[
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }

    def _get_reaction_task(self):
        checkmark= ':white_check_mark:'

        if not self.completed:
            checkmark=':white_large_square:'
        text = f'{checkmark} *React to this message* '

        return {'type':'section','text':{'type':'mrkdwn','text':text}}