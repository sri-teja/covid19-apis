from libraries import *
from flask import Blueprint


app = Flask(__name__)
CORS(app)

## for logs
# gunicorn_logger = logging.getLogger('gunicorn.error')
# app.logger.handlers = gunicorn_logger.handlers
# app.logger.setLevel(gunicorn_logger.level)

updates = Blueprint('updates', __name__, url_prefix="/updates")

from db_connection import exdb

@updates.route('/get_updates', methods=["GET", "POST"])
def get_updates():
	if request.method=="POST":
		data = request.json()
		category = data["category"]
	else:
		category = ""

	if category == "":
		updates = exdb.getData("select id, headline, body, tags, link, DATE_FORMAT(record_time, '%d %M %Y %h:%i %p')\
		  as record_time from updates")
	else:
		updates = exdb.getData("select id, headline, body, tags, link, DATE_FORMAT(record_time, '%%d %%M %%Y %%h:%%i %%p')\
		 as record_time from updates where tags like '%%%s%%'" %(category))

	collect_tags = exdb.getData("select tags from updates")
	tags = []
	for each in collect_tags:
		for tag in each["tags"].split(","):
			tag = tag.strip()
			if tag not in tags:
				tags.append(tag)
	return jsonify({"success": True, "updates": updates, "tags": tags})

@updates.route('/add_update', methods=["POST"])
def add_update():
	data = request.json()
	app.logger.info(data)

	link = data["link"]
	headline = data["headline"]
	body = data["body"]
	tags = data["tags"]

	if link and headline:
		exdb.editData("insert into updates (link, headline, body, tags) values (\"%s\", \"%s\", \"%s\", \"%s\")" %(link, headline, body, tags))
		return jsonify({"success": True, "message": "Update Added"})
	return jsonify({"success": False, "message": "Link or Headline cannot be empty"})
