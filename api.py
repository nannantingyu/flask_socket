# -*- coding: utf-8 -*-
import sys, datetime, json, logging
reload(sys)
sys.setdefaultencoding('utf-8')
from flask import Flask, request, session, render_template, url_for, redirect, jsonify
from model.Db_util import db, User, Order, Hold
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("logs/trade.log")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

from dotenv import load_dotenv
from os import environ
load_dotenv('.env')

print environ.get('URL_PREFIX')
def get_config(key):
    try:
        value = environ.get(key)
    except Exception,e:
        logger.error(e.message)
        return None
    else:
        return value

def redirect_to(url):
    url = get_config("URL_PREFIX") + url_for(url).strip("/")
    return url

app = Flask(__name__)
app.add_template_global(get_config, "get_config")

contract = {
    "AGT+D": {
        "unit": 1,
        "persent": 0.13
    },
    "AUT+D": {
        "unit": 1000,
        "persent": 0.11
    },
    "MAUT+D": {
        "unit": 100,
        "persent": 0.11
    },
    "LLG": {
        "unit": 100,
        "persent": 0.11
    }
}

@app.route('/trade')
def index():
    return render_template("trade.html")

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/register')
def register():
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(redirect_to("login"))

@app.route('/post_register', methods=['POST'])
def post_register():
    wxid = request.form.get('wxid')
    try:
        db.session.add(User(
            wxid=wxid,
            availableAsset=100000
        ))
        db.session.commit()
    except Exception,e:
        print e
        return jsonify({
            "success": 0
        })
    else:
        return jsonify({
            "success": 1
        })

@app.route('/post_login', methods=['POST'])
def post_login():
    wxid = request.form.get('wxid')
    try:
        user = User.query.filter(
            User.wxid == wxid
        ).one_or_none()

        print user
        if user:
            session['user_id'] = wxid
            return jsonify({
                "success": 1
            })
        else:
            return jsonify({
                "success": 0
            })
    except Exception,e:
        print e
        return jsonify({
            "success": 0
        })

@app.route('/lists')
def lists():
    return render_template("lists.html")

@app.route('/getEntrustDate/<wxid>')
def getEntrustDate(wxid):
    data = Order.query.filter(
        db.and_(
            Order.wxid == wxid,
            Order.state == 1
        )
    ).all()

    return jsonify([a.as_dict() for a in data])

@app.route('/getEntrustDateHistory/<wxid>')
def getEntrustDateHistory(wxid):
    data = Order.query.filter(
        db.and_(
            Order.wxid == wxid,
            Order.state != 1
        )
    ).all()

    return jsonify([a.as_dict() for a in data])

@app.route('/')
def home():
    print url_for("lists")
    return redirect(redirect_to("lists"))

@app.route('/placeOrder', methods=['POST'])
def order():
    symbolName = request.form.get('symbolName')
    price = request.form.get('price')
    bsFlag = request.form.get('bsFlag')
    ocFlag = request.form.get('ocFlag')
    orderTime = datetime.datetime.now()
    quantity = request.form.get('quantity')
    user_id = request.form.get('wxid')

    frozenMargin = float(price) * float(quantity) * contract[symbolName]['unit'] * contract[symbolName]['persent']
    print symbolName, price, bsFlag, ocFlag, quantity, user_id
    try:
        wx_order = Order(
            wxid = user_id,
            symbolName = symbolName,
            price = price,
            bsFlag = bsFlag,
            ocFlag = ocFlag,
            orderTime = orderTime,
            quantity = quantity,
            frozenMargin = frozenMargin
        )

        db.session.add(wx_order)
        db.session.commit()
    except Exception,e:
        logger.error(e.message)
        db.session.rollback()
        return jsonify({
            "success": 0
        })
    else:
        logger.info("%s set an order 【%s】" % (user_id, symbolName))
        return jsonify({
            "success": 1
        })

@app.route('/cancelOrder', methods=['POST'])
def cencelOrder():
    order_id = request.form.get('id')
    wxid = request.form.get('wxid')

    try:
        Order.query.filter(
            db.and_(
                Order.wxid == wxid,
                Order.id == order_id
            )
        ).update(
            {
                "state": 3
            }
        )
    except Exception,e:
        logger.error(e.message)
    else:
        logger.info("%s rollback an order 【%s】" % (wxid, order_id))
        return jsonify({
            "success": 1
        })

@app.route('/getPositionDate/<wxid>')
def getPositionDate(wxid):
    data = Hold.query.filter(
        Hold.wxid==wxid
    ).all()

    return jsonify({"success": 1, "data": [a.as_dict() for a in data], "customerInfo": getCustomer(wxid)})

def getCustomer(wxid):
    data = User.query.filter(
        User.wxid == wxid
    ).all()

    return [a.as_dict() for a in data]

@app.route('/getCustomerInfo/<wxid>')
def getCustomerInfo(wxid):
    data = User.query.filter(
        User.wxid == wxid
    ).all()

    return jsonify([a.as_dict() for a in data])

@app.route('/socketaddr')
def getsocketaddr():
    return jsonify(app.config['SOCKET_ADDR'])

if __name__ == '__main__':
    db.create_all()
    app.config.from_json("setting.json")
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, host='0.0.0.0', port=int(environ.get("API_PORT")))
