#!/usr/bin/env python
from libraries import *

#Creating a FLASK instance
app = Flask(__name__)

from readings import readings
# from readings import summary
from readings import patient_data_periodic
# from readings import daily
from readings import new_summary_periodic
from readings import new_daily_periodic
from readings import all_countries_update
from readings import world_stats_update_periodic
from readings import all_states_periodic

app.register_blueprint(readings)


from updates import updates
app.register_blueprint(updates)


CORS(app)
app.config['debug'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'mycovidsecret key'

HOST = "localhost"
USER = "root"
PASS = "mngl99"
# PASS = "12345678"
MYDB = "covid"

## for database
import pymysql
import pymysql.cursors as mc
import contextlib

DictCursor = mc.DictCursor
SSCursor = mc.SSCursor
SSDictCursor = mc.SSDictCursor
Cursor = mc.Cursor

## for database connection
@contextlib.contextmanager
def connection(cursorclass=Cursor,
               host=HOST, user=USER,
               passwd=PASS, dbname=MYDB,
               driver=pymysql):
    connection = driver.connect(
            host=host, user=user, passwd=passwd, db=dbname,
            cursorclass=cursorclass)
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()

@contextlib.contextmanager
def cursor(cursorclass=Cursor, host=HOST, user=USER,
           passwd=PASS, dbname=MYDB):
    with connection(cursorclass, host, user, passwd, dbname) as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

class database:
    def getData(self, query):
        with cursor(SSDictCursor) as cur:
            # print(cur)
            connection = cur.connection
            # print(connection)
            cur.execute(query)
            result = cur.fetchall()
            print(result)
            return list(result)

    def editData(self, query):
        with cursor(SSDictCursor) as cur:
            # print(cur)
            connection = cur.connection
            # print(connection)
            cur.execute(query)
            num = cur.lastrowid
            print(num)
            return num

exdb = database()



@app.route('/test', methods = ['POST'])
def test():
    data = request.json
    print(data)
    return jsonify({"success": True, "message": "Data received Successfully!", "data": data})

# for SSL Certificate
# @app.route('/.well-known/acme-challenge/<challenge>', methods=["GET"])
# def letsencrypt_check(challenge):
#     challenge_response = {
#         "":"<challenge_response>",
#         "<challenge_token>":"<challenge_response>"
#     }
#     return Response(challenge_response[challenge], mimetype='text/plain')

#Cors
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

## for logs
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)


# def run_schedule():
#     while 1:
#         schedule.run_pending()
#         time.sleep(1)

# # schedule.every(12).minutes.do(summary)
# schedule.every(2).minutes.do(patient_data_periodic)
# # schedule.every(16).minutes.do(daily)
# schedule.every(1).minutes.do(new_daily_periodic)
# schedule.every(3).minutes.do(new_summary_periodic)


# t = Thread(target=run_schedule)
# t.start()

# Start the scheduler
sched = Scheduler()
sched.start()

sched.add_interval_job(patient_data_periodic, minutes=30)
sched.add_interval_job(new_daily_periodic, minutes=15)
sched.add_interval_job(new_summary_periodic, minutes=10)
sched.add_interval_job(all_countries_update, minutes=310)
sched.add_interval_job(world_stats_update_periodic, minutes=300)
sched.add_interval_job(all_states_periodic, minutes=310)

if __name__ == '__main__':
#     # app.run(port=8081,threaded=True, host="0.0.0.0", debug=True, ssl_context=('/etc/letsencrypt/live/mngl.vectorx.co/fullchain.pem', '/etc/letsencrypt/live/mngl.vectorx.co/privkey.pem'))
    app.run(threaded=True, host="0.0.0.0", use_reloader=True)
