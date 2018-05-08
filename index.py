# -*- coding: utf-8 -*-
import os
import logging
import redis, json
import gevent
import re
from flask import Flask, render_template
from flask_sockets import Sockets

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("logs/sockets.log")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

REDIS_CHAN = 'chat'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

from dotenv import load_dotenv
from os import environ
load_dotenv('.env')


sockets = Sockets(app)
redis = redis.from_url("redis://%s:6379" % environ.get("redis_host_local"))

class ChatBackend(object):
    all_species_client = {
        "LLG": set(),
        "AGT+D": set(),
        "AUT+D": set(),
        "MAUT+D": set()
    }

    def __init__(self):
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(REDIS_CHAN)
        self.clients = set()

    def __iter_data(self):
        for message in self.pubsub.listen():
            data = message.get('data')
            if message['type'] == 'message':
                yield data

    def register(self, code, client):
        self.all_species_client[code].add(client)

    def send(self, client, data):
        try:
            data = data.decode("utf-8")
            client.send(data)
        except Exception,e:
            self.clients.discard(client)

    def run(self):
        try:
            for data in self.__iter_data():
                if "href" in data:
                    continue

                for client in self.clients:
                    gevent.spawn(self.send, client, data)

                try:
                    ap = re.compile(r'(=")(.*?)(")')
                    data_re = ap.sub(r'=\\"\2\\"', data)
                    data_json = json.loads(data_re.decode("unicode_escape")
                                           .replace('\r', '')
                                           .replace('\n', '').encode("utf-8"))

                    if "code" in data_json and data_json['code'] in self.all_species_client:
                        for client in self.all_species_client[data_json['code']]:
                            gevent.spawn(self.send, client, data)
                except Exception,e:
                    logger.error(e.message)
                    logger.error(data_re)
                    continue
                    
        except Exception,e:
            logger.error(e.message)

    def start(self):
        gevent.spawn(self.run)

chats = ChatBackend()
chats.start()

@app.route('/')
def hello():
    return render_template('index.html')

@sockets.route('/close')
def close(ws):
    print "close"

@sockets.route('/receive')
def outbox(ws):
    chats.clients.add(ws)
    while not ws.closed:
        message = str(ws.receive())
        if message.startswith("subscribe:"):
            code = message.split(":")[-1].split(",")
            for c in code:
                if c in ChatBackend.all_species_client:
                    chats.register(c, ws)

        gevent.sleep(0.1)

