## covid19-apis

This repository contains the APIs for the website hosted at www.curecovid19.in

### Files
- `libraries.py` contains all the `global variables` and `imports` go
- `db_connection.py` contains the code to connect to your `SQL database`
- `app.py` contains the `Flask` instance along with `logger` and `scheduler`
- `readings.py` contains the APIs which collect the stats about covid19 on a regular basis as defined in the scheduler.
- `updates.py` contains the APIs which deals with the posts in updates page.

### Install
`pip install -r requirements.txt`

### Run
`python app.py`

This defaults to port 5000. You can access the apis with base url as `localhost:5000`

### How to Contribute

Follow the steps given in the below link to clone the forked repo, create branch, add your changes, push, compare and send a pull request for review.

`https://github.com/firstcontributions/first-contributions/blob/master/README.md`

#### Join Telegram Group, for updates and discussions.
`https://t.me/joinchat/Lw0dpxlYNwXA9k7TKdhvKw`

##### \#IndiaFightsCorona \#TogetherWeCan