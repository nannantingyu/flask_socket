# -*- coding: utf-8 -*-
import os
import logging
import redis, json
import gevent
from flask import Flask, render_template
from flask_sockets import Sockets

REDIS_CHAN = 'chat'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url("redis://127.0.0.1:6379")

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
            print e

    def run(self):
        for data in self.__iter_data():
            for client in self.clients:
                gevent.spawn(self.send, client, data)

            data_json = json.loads(data.decode("unicode_escape").replace("'", '"').encode("utf-8"))
            if data_json['code'] in self.all_species_client:
                for client in self.all_species_client[data_json['code']]:
                    gevent.spawn(self.send, client, data)

    def start(self):
        gevent.spawn(self.run)

chats = ChatBackend()
chats.start()

@app.route('/')
def hello():
    return render_template('index.html')

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
