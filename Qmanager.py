# -*- coding: utf-8 -*-
import redis, threading, json, time, logging
from kafka import KafkaConsumer

from dotenv import load_dotenv
from os import environ

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("logs/push_in_queue.log")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Qmanager:
    def __init__(self):
        self.myqueue = None
        self.group_id = None
        self.last = {}

        load_dotenv('.env')
        self.r = redis.Redis(host=environ.get('redis_host'))
	self.r_local = redis.Redis(host=environ.get('redis_host_local'))

    def manager_proc(self):
        redis_thread = threading.Thread(target=self.push_redis)
        kafka_thread = threading.Thread(target=self.push_kafka)

        redis_thread.start()
        kafka_thread.start()

        redis_thread.join()
        kafka_thread.join()

    def push_redis(self):
        ps = self.r.pubsub()
        ps.psubscribe(['quotation_changed*'])

        for item in ps.listen():
            try:
		print item
                if not isinstance(item['data'], long):
                    data = json.loads(item['data'])
                    code = data['code']
                    push_data = item['data']
		    print push_data
                    ptime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(data['quoteTime'])))

                    if code not in self.last:
                        self.r_local.publish("chat", push_data.encode("utf-8"))
                        self.last[code] = {
                            "time": ptime,
                            "times": 1
                        }
                    else:
                        if ptime == self.last[code]['time']:
                            if self.last[code]['times'] < 3:
                                self.r_local.publish("chat", push_data)

                            self.last[code]['times'] += 1
                        else:
                            self.r_local.publish("chat", push_data)
                            self.last[code]['times'] = 1
                            self.last[code]['time'] = ptime
            except Exception,e:
                logger.error(e.message)

    def push_kafka(self):
        try:
            server = {
                'host': environ.get('kafka_host'),
            }

            consumer = KafkaConsumer('crawl_jin10_kuaixun',
                                     bootstrap_servers=server['host'],
                                     group_id=self.group_id,
                                     auto_offset_reset="earliest")

            for msg in consumer:
                try:
                    data = msg.value.decode('utf-8')
                    self.r_local.publish("chat", data)
                except Exception, e:
                    print e
        except Exception,e:
            logger.error(e.message)
