# -*- coding: utf-8 -*-
import sys, json, datetime
from decimal import *
reload(sys)
sys.setdefaultencoding('utf-8')

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy, DeclarativeMeta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:abc123@127.0.0.1/trade'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)

class DbToJSON():
    def as_dict(self):
        dic = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if isinstance(val, datetime.datetime):
                dic[c.name] = val.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(val, Decimal):
                dic[c.name] = float(val)
            else:
                dic[c.name] = val
        return dic

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data) # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

class User(db.Model, DbToJSON):
    __tablename__ = 'trade_user'
    wxid = db.Column(db.String(28), primary_key=True)
    availableAsset = db.Column(db.DECIMAL)
    created_time = db.Column(db.DateTime, default=db.func.now())
    updated_time = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

class Order(db.Model, DbToJSON):
    __tablename__ = 'trade_order'

    id = db.Column(db.BIGINT, primary_key=True)
    wxid = db.Column(db.String(28))
    price = db.Column(db.DECIMAL)
    quantity = db.Column(db.Integer)
    orderTime = db.Column(db.DateTime, default=db.func.now())
    frozenMargin = db.Column(db.DECIMAL)
    symbolName = db.Column(db.String(16))
    bsFlag = db.Column(db.SmallInteger)
    ocFlag = db.Column(db.String(1))
    state = db.Column(db.SmallInteger, default=1)
    updated_time = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

class Hold(db.Model, DbToJSON):
    __tablename__ = 'trade_hold'
    id = db.Column(db.DECIMAL, primary_key=True)
    wxid = db.Column(db.String(28))
    quantity = db.Column(db.Integer)
    openPrice = db.Column(db.DECIMAL)
    frozenQuantity = db.Column(db.Integer)
    symbolName = db.Column(db.String(16))
    bsFlag = db.Column(db.SmallInteger)
    created_time = db.Column(db.DateTime, default=db.func.now())
    updated_time = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())




