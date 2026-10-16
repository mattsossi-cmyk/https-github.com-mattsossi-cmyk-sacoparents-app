import os, sys
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
email, mode = sys.argv[1], sys.argv[2]
if mode == 'unset':
    r = db.users.update_one({'email': email}, {'$unset': {'ai_notice_version': '', 'ai_notice_ack_at': ''}})
elif mode == 'old':
    r = db.users.update_one({'email': email}, {'$set': {'ai_notice_version': '2000-01-01'}})
u = db.users.find_one({'email': email}, {'_id':0,'ai_notice_version':1,'ai_notice_ack_at':1,'privacy_consent_version':1})
print(r.matched_count, u)
print('send_anyway last:', list(db.ai_send_anyway_log.find({}, {'_id':0}).sort([('$natural',-1)]).limit(1)))
