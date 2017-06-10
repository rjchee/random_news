Twitter bot that pulls in headlines from various news sites and outputs Markov chains using a RandomWriter. The model is stored in a Python pickle that is stored in a PostgreSQL database. A working version of this is running on https://twitter.com/RandomNews5.

Requirements:
------------
Python dependencies listed in requirements.txt

Set up a Twitter account and get your Consumer API Key and Secret, as well as an Access Token and Secret.

A PostgreSQL database is used to store the Python pickle of the data model, as well as the previously found headlines to avoid training on duplicate headlines.

Save the following bash environment variables:

* `API_KEY` = Your Twitter API Key
* `API_SECRET` = Your Twitter API Secret
* `OAUTH_TOKEN` = Your Access Token
* `OAUTH_SECRET` = Your Access Secret
* `DATABASE_URL` = Your PostgreSQL Database URL

Usage:
------
Setting up virtualenv is useful before running anything.
    
Use `pip install -r requirements.txt` to install python dependencies.

Run `python3 twitter_bot.py` to send a tweet.

Run `python3 news_model.py` to update the model. By default, if the model doesn't exist, twitter_bot.py initializes it for you.

If you want to modify the set of websites to train on, edit the config.ini file. It assumes that headlines are found in HTML tags that all have the same class, so the format of a config line is
`URL = class_name`
