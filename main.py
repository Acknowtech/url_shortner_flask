from flask import Flask, jsonify , request
from flask_sqlalchemy import SQLAlchemy
import random
from sqlalchemy.sql.elements import Null

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost:3306/shortUrl'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
baseURL = "https://www.demo.com/"
@app.before_first_request
def create_tables():
    db.create_all()

class Urls(db.Model):
    __tablename__ = 'urls'
    id = db.Column('id',db.Integer, primary_key=True)
    long = db.Column( 'long',db.String(255))
    short = db.Column('short',db.String(7),index=True)
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    updated_on = db.Column(db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    expired_on = db.Column(db.DateTime, nullable=True)
    def __init__(self, long, short):
        self.long = long
        self.short = short

class Url_Hit_Count(db.Model):
    __tablename__ = 'url_hit_count'
    id = db.Column('id', db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('urls.id'),
                          nullable=False)
    count = db.Column('count',db.Integer)
    created_on = db.Column('created_on',db.DateTime, server_default=db.func.now())
    updated_on = db.Column('updated_on',db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())

def hash_generator():
    base_62_string  = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    while True:
        rand_letters = random.choices(base_62_string, k=7)
        rand_letters = "".join(rand_letters)
        short_url = Urls.query.filter_by(short=rand_letters,expired_on=Null).first()
        if not short_url:
            return rand_letters

@app.route('/',methods=['GET'])
def home():
    return  jsonify({"msg":"welcome"})

@app.route('/generate_short_url',methods=['POST'])
def generate_short_url():
    try:
        if 'long_url' not in request.form:
            return {'status':False,"msg":"long_url is required"}
        long_url = request.form["long_url"]
        record = Urls.query.filter_by(long=long_url).first()
        if record:
            return { "status":True,
                       "data" : {
                           "shortURL": baseURL+record.short,
                           "urlHash": record.short
                       },
                     "message":"Short Url Generated"
                     },201
        else:
            short_url = hash_generator()
            new_url = Urls(long_url, short_url)
            db.session.add(new_url)
            db.session.commit()
            return {"status":True,
                       "data" : {
                           "shortURL": baseURL+new_url,
                           "urlHash": new_url
                       },
                     "message":"Short Url Generated"},201
    except Exception as e:
        print(e)
        return {'status': False, "msg": "Something Went Wrong"},413

@app.route('/get_long_url',methods=['POST'])
def get_long_url():
    try:
        if 'short_url' not in request.form :
            return {'status':False,"msg":"short_url is required"}
        short_url = request.form["short_url"].split('/')[-1]
        print(short_url)
        record = Urls.query.filter_by(short=short_url,expired_on=None).first()
        if record:
            return { "status":True,
                       "data" : {
                           "longURL": baseURL+record.long,
                           "urlHash": record.long
                       },
                     "message":"Long Url Exist"
                     },200
        else:
            return {"status":False,"msg":"No Long Url Exist. Invalid Short Url"},200
    except Exception as e:
        print(e)
        return {'status': False, "msg": "Something Went Wrong"},413

if __name__ == '__main__':
    app.run(port=5000, debug=True)


