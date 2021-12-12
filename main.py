from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import random

from sqlalchemy import func, extract
from sqlalchemy.sql.elements import Null, or_
from flask_caching import Cache
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import json
from flask_marshmallow import Marshmallow

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost:3306/shortUrl'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = "SimpleCache"
app.config['CACHE_DEFAULT_TIMEOUT'] = 3600
db = SQLAlchemy(app)
ma = Marshmallow(app)
cache = Cache(app)
baseURL = "https://www.demo.com/"


@app.before_first_request
def create_tables():
    db.create_all()


# models
class Urls(db.Model):
    __tablename__ = 'urls'
    id = db.Column('id', db.Integer, primary_key=True)
    long = db.Column('long', db.String(255))
    short = db.Column('short', db.String(7), index=True)
    meta = db.Column('meta', db.Text())
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    updated_on = db.Column(db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    expired_on = db.Column(db.DateTime, nullable=True)

    def __init__(self, long, short, meta):
        self.long = long
        self.short = short
        self.meta = meta


class Url_Hit_Count(db.Model):
    __tablename__ = 'url_hit_count'
    id = db.Column('id', db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('urls.id'),
                       nullable=False)
    count = db.Column('count', db.Integer)
    created_on = db.Column('created_on', db.DateTime, server_default=db.func.now())
    updated_on = db.Column('updated_on', db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())

    def __init__(self, url_id, count):
        self.url_id = url_id
        self.count = count


class UrlsSchema(ma.Schema):
    class Meta:
        fields = ('id', 'long', 'short', 'meta', 'created_on')


# Init schema
url_schema = UrlsSchema()
urls_schema = UrlsSchema(many=True)


def get_count_key(short_url):
    return datetime.now().strftime('%Y%m%d%H') + "_" + short_url


def hash_generator():
    base_62_string = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    while True:
        rand_letters = random.choices(base_62_string, k=7)
        rand_letters = "".join(rand_letters)
        short_url = Urls.query.filter_by(short=rand_letters, expired_on=Null).first()
        if not short_url:
            return rand_letters


@app.route('/', methods=['GET'])
def home():
    return jsonify({"msg": "welcome"})


@app.route('/generate_short_url', methods=['POST'])
def generate_short_url():
    try:
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if 'long_url' not in request.form:
            return {'status': False, "msg": "long_url is required"}
        if re.match(regex, request.form["long_url"]) is None:
            return {'status': False, "msg": "Valid long url is required"}
        long_url = request.form["long_url"]
        record = Urls.query.filter_by(long=long_url).first()
        if record:
            return {"status": True,
                    "data": {
                        "shortURL": baseURL + record.short,
                        "urlHash": record.short
                    },
                    "message": "Short Url Generated"
                    }, 201
        else:
            short_url = hash_generator()
            response = requests.get(long_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            metas = soup.find_all('meta')
            meta_description = [meta.attrs['content'] for meta in metas if
                                'name' in meta.attrs and meta.attrs['name'].lower() == 'description']
            new_url_meta = (" ").join(meta_description)
            meta_keywords = [meta.attrs['content'] for meta in metas if
                             'name' in meta.attrs and meta.attrs['name'].lower() == 'keywords']
            new_url_meta += (" ").join(meta_keywords)
            new_url = Urls(long_url, short_url, new_url_meta)
            db.session.add(new_url)
            db.session.commit()
            cache.set(short_url, long_url, 600)
            count_key = get_count_key(short_url)
            cache.set(count_key, 0)
            keys = cache.get('keys')
            if keys:
                keys.append(count_key)
                cache.set('keys', keys)
            else:
                keys = [count_key]
                cache.set('keys', keys)
            return {"status": True,
                    "data": {
                        "shortURL": baseURL + short_url,
                        "urlHash": short_url
                    },
                    "message": "Short Url Generated"}, 201
    except Exception as e:
        print(e)
        return {'status': False, "msg": "Something Went Wrong"}, 413


@app.route('/get_long_url', methods=['POST'])
def get_long_url():
    try:
        if 'short_url' not in request.form:
            return {'status': False, "msg": "short_url is required"}
        short_url = request.form["short_url"].split('/')[-1]
        long_url = None
        if cache.get(short_url):
            long_url = cache.get(short_url)
        else:
            record = Urls.query.filter_by(short=short_url, expired_on=None).first()
            if record:
                long_url = record.long
        if long_url:
            count_key = get_count_key(short_url)
            hit_count = 1
            count = cache.get(count_key)
            if count != None:
                count += 1
                hit_count = count
                cache.set(count_key, count)
            else:
                cache.set(count_key, hit_count)
            keys = cache.get('keys')
            if keys == None:
                keys = [count_key]
                cache.set('keys', keys)

            return {"status": True,
                    "data": {
                        "longURL": baseURL + long_url,
                        "urlHash": long_url,
                        "lastHourHitCount": hit_count
                    },
                    "message": "Long Url Exist"
                    }, 200
        else:
            return {"status": False, "msg": "No Long Url Exist. Invalid Short Url"}, 200
    except Exception as e:
        print(e)
        return {'status': False, "msg": "Something Went Wrong"}, 413


@app.route('/analytics_cron_job', methods=['GET'])
def analytics_cron_job():
    keys = cache.get('keys')
    if keys:
        print(keys)
        cache.delete('keys')
        for k in keys:
            count = cache.get(k)
            print(count)
            if count:
                short_url = k.split('_')[-1]
                record = Urls.query.filter_by(short=short_url, expired_on=None).first()
                new_record = Url_Hit_Count(record.id, count)
                db.session.add(new_record)
                db.session.commit()
                cache.delete(k)

    return {}, 200


@app.route('/search_from_keywords', methods=['POST'])
def search_from_metadata():
    if 'search_term' not in request.form:
        return {'status': False, "msg": "search_term is required"}
    search_term = request.form['search_term']
    results = Urls.query.filter(or_(Urls.meta.ilike(f'%{search_term}%'), Urls.long.ilike(f'%{search_term}%'))).all()
    results = urls_schema.dump(results)

    if len(results) > 0:
        return {
            "status": True,
            "data": results
        },200
    else:
        return {
            "status": False,
            "data": "No Data Found"
        },200


@app.route('/get_analytics_of_short_url', methods=['GET'])
def get_analytics_of_short_url():
    if 'short_url' not in request.args:
        return {'status': False, "msg": "short_url is required"}
    short_url = request.args.get("short_url").split('/')[-1]
    record = Urls.query.filter_by(short=short_url, expired_on=None).first()
    if record:
        responseData = {}
        responseData['short_url_details'] = url_schema.dump(responseData)
        data = Url_Hit_Count.query.with_entities(func.sum(Url_Hit_Count.count).label('average')).filter(Url_Hit_Count.url_id == record.id).first()
        responseData['total_hits'] = data[0]
        data = db.engine.execute('SELECT `created_on`, sum(count) FROM url_hit_count GROUP BY hour( created_on ) , day( created_on )')
        summary= []
        for i in data:
            print(i[0],i[1])
            summary.append({"time":str(i[0]),"count":i[1]})
        responseData['total_hourly_hits'] =summary

        print(responseData)
        return {
          "status":True,
            "data":responseData
        },200
    return {"status": False, "msg": "No Long Url Exist. Invalid Short Url"}, 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
