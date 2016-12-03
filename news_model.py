#!/usr/bin/env python3
""" NewsModel
This module contains logic to update a RandomWriter object from news headlines
pulled from the internet.
"""
import argparse
from datetime import datetime
from html.parser import HTMLParser
import os
import pickle
import re
from urllib.parse import urlparse

import psycopg2
import requests

import config_reader
import randomwriter
from randomwriter import RandomWriter

class NewsHTMLParser(HTMLParser):
    """ Parses HTML from a news website, pulling out headline text """


    def __init__(self, save_headline, is_headline_tag):
        self.cur_count = 0
        self.save_headline = save_headline
        self.is_headline_tag = is_headline_tag
        self.headline_count = 0
        self.cur_headline = ""
        super().__init__()


    def handle_starttag(self, tag, attrs):
        if self.cur_count:
            self.cur_count += 1
        elif self.is_headline_tag(tag, attrs):
            self.cur_count = 1
            self.cur_headline = ""


    def handle_endtag(self, tag):
        if self.cur_count:
            self.cur_count -= 1
            if not self.cur_count:
                if self.save_headline(' '.join(self.cur_headline.split())):
                    self.headline_count += 1


    def handle_data(self, data):
        if self.cur_count:
            self.cur_headline += data


    @classmethod
    def identify_headline_class(cls, name):
        """ Return a headline tag identifier based on the class attribute """
        def is_headline_tag(tag, attrs):
            """ Identify a tag as one containing a headline by the class attribute """
            return ('class', name) in attrs
        return is_headline_tag


class NewsModel(object):
    """ This class contains logic to access the PostgreSQL database on news models """


    def __init__(self):
        self.urlmap = {}


    def update_model(self, writer, url, is_headline_tag, old_headlines, new_headlines, blacklist=None):
        """ Update a single model with the URL and other parameters """
        if not hasattr(self, 'window'):
            print("please update the news model through news_model.py")
            return
        # we don't make blacklist a set() by default at the top because the set
        # is mutable and is instantiated when the module is loaded
        if blacklist is None:
            blacklist = set()
        if url in self.urlmap:
            headlines, count = self.urlmap[url]
        else:
            headlines = []
            endtime_re = re.compile('^.*(?P<time>\\d\\d?:\\d{2} [AP]M \\wT)$')
            def save_headline(headline):
                """ Filter out useless headlines and store the useful ones for training later """
                if "ttp://" in headline:
                    return False
                endtime_match = endtime_re.match(headline)
                if endtime_match is not None: # for new york times headlines ending in the time
                    headline = headline[:len(headline) - len(endtime_match.group('time'))].strip()
                ret = headline not in blacklist and headline.strip()
                if ret:
                    headlines.append(headline)
                    new_headlines.add(headline)
                return ret
            html_parser = NewsHTMLParser(save_headline, is_headline_tag)
            html_page = requests.get(url)
            html_parser.feed(html_page.text)
            count = html_parser.headline_count
            self.urlmap[url] = (headlines, count)

        for headline in headlines:
            writer.train(headline)
        for headline in old_headlines:
            writer.untrain(headline)
        return count


    @staticmethod
    def get_db_conn():
        """ Open a connection with the PostgreSQL database """
        url = urlparse(os.environ['DATABASE_URL'])
        return psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )


    def get_randomwriter(self, name, level=5, strategy=randomwriter.CharacterStrategy):
        """ Retrieve a news model from the database """
        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                # check if our table exists
                cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables"
                            + " where table_name=%s);", ('models',))
                if not cur.fetchone()[0]:
                    # our table does not exist
                    cur.execute("CREATE TABLE models (id serial PRIMARY KEY,"
                                + " name text NOT NULL UNIQUE, pickle bytea NOT NULL);")
                # get the pickle from the database
                cur.execute("SELECT pickle FROM models WHERE name=%s;", (name,))
                res = cur.fetchone()
                if res:
                    res = res[0].tobytes()
                    random_writer = RandomWriter.unpickle(res)
                else:
                    random_writer = RandomWriter(level, strategy)
                    pkl = pickle.dumps(random_writer)
                    cur.execute("INSERT INTO models (name, pickle) VALUES (%s, %s);", (name, pkl))
                return random_writer


    def delete_news_model(self, name):
        """ Delete a news model from the PostgreSQL database """
        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM models WHERE name=%s;", (name,))


    def delete_headlines(self):
        """ Clear the headlines table """
        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE headlines;")


    def update_news_models(self, models):
        """ Update a list of models with headlines pulled from the websites in the config """
        if not hasattr(self, 'window'):
            print("please update the news model through news_model.py")
            return
        news_sites = config_reader.read_configs()['NEWS']

        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                # get table of already used headlines
                cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables"
                            + " where table_name=%s);", ('headlines',))
                if not cur.fetchone()[0]:
                    # our table does not exist
                    cur.execute("CREATE TABLE headlines (id serial PRIMARY KEY,"
                                + " headline text NOT NULL UNIQUE,"
                                + " date_added date);")

                cur.execute("SELECT headline FROM headlines;")
                blacklist = set(res[0] for res in cur)
                cur.execute("SELECT headline FROM headlines WHERE date_added < now() - interval '%s days';", (self.window,))
                old_headlines = set(res[0] for res in cur)

        if isinstance(models, str):
            models = {models : None}

        output = {}
        new_headlines = set()
        for name, settings in models.items():
            if settings is None:
                model = self.get_news_model(name)
            else:
                model = self.get_news_model(name, settings[0], settings[1])
            for url, class_name in news_sites.items():
                # counts should never differ, so just save it each time
                output[url] = self.update_model(model, "http://" + url,
                                                NewsHTMLParser.identify_headline_class(class_name),
                                                old_headlines, new_headlines, blacklist)
            with self.get_db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE models SET pickle=%s WHERE name=%s",
                                (pickle.dumps(model), name))

        for url, count in output.items():
            print(url, count)

        # clear out old headlines and add new ones
        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM headlines WHERE date_added < now() - interval '%s days';", (self.window,))
                for headline in new_headlines:
                    cur.execute("INSERT INTO headlines (headline, date_added) VALUES (%s, %s);", (headline, datetime.now()))


def __main():
    config = config_reader.read_configs()
    models = {}
    for model_name in config['MODEL_WEIGHTS']:
        if model_name in config['CHARACTER_MODELS']:
            models[model_name] = (int(config['CHARACTER_MODELS'][model_name]),
                                  randomwriter.CharacterStrategy)
        elif model_name in config['WORD_MODELS']:
            models[model_name] = (int(config['WORD_MODELS'][model_name]), randomwriter.WordStrategy)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd')
    update_parser = subparsers.add_parser('update')
    update_parser.add_argument('-o', '--omit', default=[], nargs='+', choices=list(models.keys()))
    delete_parser = subparsers.add_parser('delete')
    # no arguments means delete headlines only
    delete_parser.add_argument('models', nargs='*', choices=list(models.keys()) + [[]])
    parser.set_defaults(cmd='update', omit=[])

    args = parser.parse_args()
    news_model = NewsModel()
    news_model.window = int(config['DB']['window'])
    if args.cmd == 'update':
        for model in args.omit:
            del models[model]
        news_model.update_news_models(models)
    elif args.cmd == 'delete':
        if args.model:
            for model in args.models:
                news_model.delete_news_model(model)
        else:
            news_model.delete_headlines()


if __name__ == '__main__':
    __main()
