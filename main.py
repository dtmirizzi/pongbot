from slack import WebClient
import os
from pathlib import Path
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import string
import time
import re
import mysql.connector
from elo import rate_1vs1


#reeeeeee
beats_keys = ["beats", "beat", "beated"]
looses_keys = ["lost to", "was distroyed by"]
keys = looses_keys + beats_keys
beats_regex = re.compile(f'([<][@]u.+[>])\s+([<][@]u.+[>])\s+(' + "|".join(keys) + ')\s+([<][@]u.+[>])')

app = Flask(__name__)

#slack

slack_event_adapter = SlackEventAdapter(
    os.environ['SLACK_VERFICATION_KEY'], '/slack/events', app)
client = WebClient(token=os.environ['SLACK_CLEINT_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']
ping_pong_chan = '#pingpong'

table_qry ='''create table if not exists pingpong.users (
  user_id varchar(255),
  wins int default 0,
  losses int default 0,
  elo int default 400,
  PRIMARY KEY(user_id)
);
'''

pongdb = mysql.connector.connect(
  host=os.environ['MYSQL_HOST'],
  user=os.environ['MYSQL_USER'],
  password=os.environ['MYSQL_PASSWORD']
)
pongdb.cursor().execute(table_qry)
print(f"created pong table")

@app.route('/')
def index():
       return "Pong Serv Index"

@slack_event_adapter.on('app_mention')
def message(payload):
    event = payload.get('event', {})
    channel_id = ping_pong_chan
    user_id = event.get('user')
    text = event.get('text')
    #print(payload)
    if user_id != None and BOT_ID != user_id:
        try:
            if "leaderboard" in text.lower():
                client.chat_postMessage(
                channel=channel_id, 
                text=f"<@{user_id}> Requested the leaderboard ```{leaderboard()} ```"
                )    
            elif any(x in text.lower() for x in beats_keys):
                print(text.lower())
                u = split(text)
                print(u)
                beat(u[0], u[1])
            elif any(x in text.lower() for x in looses_keys):
                u = split(text)
                beat(u[1], u[0])
            else:
                client.chat_postMessage(
                channel=event.get('channel'), 
                text=f"Hey I didnt understand you, try `@PongBot @DT Beat @ME` or `@PongBot Leaderboard`"
                )
        except Exception as e:
            print(e)
            client.chat_postMessage(
                channel=event.get('channel'), 
                text=f"Hey sorry something is not working"
                )
            return

# split will return a tuple with 2 user ids 
def split(text):
    return beats_regex.match(text.lower()).group(2,4)

def beat(winner, looser):
    curs = pongdb.cursor()
    # get each user rank 
    winner_rank = get_rank(curs, winner)
    looser_rank = get_rank(curs, looser) 

    print(winner_rank, looser_rank)

    winner_rank, looser_rank = rate_1vs1(winner_rank, looser_rank)

    # a user can never have a <100 rank
    if looser_rank < 100:
        looser_rank = 100
    
    # add to db
    curs.execute("update pingpong.users set wins=wins+1, elo = %s where user_id = %s", (int(winner_rank), winner))
    curs.execute("update pingpong.users set losses=losses+1, elo = %s where user_id = %s", (int(looser_rank), looser))

    pongdb.commit()
    curs.close()

def get_rank(curs, user):
    curs.execute("select elo from pingpong.users where user_id= %s", (user, ))
    rows = curs.fetchall()
    if len(rows) == 0:
        # if we never seen the user b4 set their rank to 400
        curs.execute("insert into pingpong.users (user_id) values (%s)", (user, ))
        pongdb.commit()
        return 400
    return rows[0][0]

def leaderboard():
    curs = pongdb.cursor()
    curs.execute("select user_id, wins, losses, elo from pingpong.users order by elo desc")
    rows = curs.fetchall()
    results = []
    rank = 0
    prev_rank = 1000000000
    for u in rows:
        if u[3] < prev_rank:
            rank = rank + 1
            prev_rank = u[3]
        results.append(f'{rank}. <{u[0].upper()}> Wins:{u[1]} Losses: {u[2]} Elo: {u[3]}')
    curs.close()
    return '\n'.join(results)

if __name__ == '__main__':
    if os.environ['ENV']== "PROD": 
        from waitress import serve
        serve(app, host="0.0.0.0", port=8080)
    else:
        app.run(host='0.0.0.0', port=8080)