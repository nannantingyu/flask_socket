# -*- coding: utf-8 -*-
import sys, redis, logging, json, time
reload(sys)
sys.setdefaultencoding('utf-8')
from dotenv import load_dotenv
from os import environ
from model.Db_util import db, Order

load_dotenv('.env')

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("logs/trade_manager.log")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

rc = redis.Redis(host=environ.get('redis_host'))
rlocal = redis.Redis(host="127.0.0.1")
ps = rc.pubsub()
ps.psubscribe(['quotation_changed*'])

qlength = 5
tick_list = {}

def scan_db_to_manage(code, low, high):
    Order.query.filter(
        db.and_(
            Order.symbolName == code,
            Order.state == 1,
            Order.ocFlag == 'o',
            Order.price >= low
        )
    ).update({
        "state": 2
    })

    Order.query.filter(
        db.and_(
            Order.symbolName == code,
            Order.state == 1,
            Order.ocFlag == 'c',
            Order.price <= high
        )
    ).update({
        "state": 2
    })

    db.session.commit()

for item in ps.listen():
    try:
        if not isinstance(item['data'], long):
            data = json.loads(item['data'])
            code = data['code']
            if code in ['AGT+D', 'AUT+D', 'MAUT+D', 'LLG']:
                push_data = item['data'].decode("utf-8")

                # 在报价qlength次之内的，先存到redis猴子那个
                if code not in tick_list:
                    # 如果第一次获取数据
                    tick_list[code] = {
                        "times": 1,
                        "time": data['quoteTime']
                    }

                    rlocal.zadd("trade_manage:buy:%s:%s" % (code, data['quoteTime']), time.time(),
                                float(data['buy']))
                    rlocal.zadd("trade_manage:sell:%s:%s" % (code, data['quoteTime']), time.time(),
                                float(data['sell']))
                else:
                    if tick_list[code]['times'] <= qlength:
                        tick_list[code]['times'] += 1
                        rlocal.zadd("trade_manage:buy:%s:%s" % (code, tick_list[code]['time']), time.time(),
                                    float(data['buy']))
                        rlocal.zadd("trade_manage:sell:%s:%s" % (code, tick_list[code]['time']), time.time(),
                                    float(data['sell']))
                    else:
                        # 到了qlength次时，扫描数据库
                        key_buy = "trade_manage:buy:%s:%s" % (code, tick_list[code]['time'])
                        key_sell = "trade_manage:sell:%s:%s" % (code, tick_list[code]['time'])
                        high = rlocal.zrevrange(key_buy, 0, 0, withscores=True)[0][1]
                        low = rlocal.zrange(key_sell, 0, 0, withscores=True)[0][1]
                        scan_db_to_manage(code, high, low)

                        tick_list[code] = {
                            "times": 1,
                            "time": data['quoteTime']
                        }

                        rlocal.zadd("trade_manage:buy:%s:%s" % (code, tick_list[code]['time']), time.time(),
                                    float(data['buy']))
                        rlocal.zadd("trade_manage:sell:%s:%s" % (code, tick_list[code]['time']), time.time(),
                                    float(data['sell']))
    except Exception,e:
        logger.error(e.message)
