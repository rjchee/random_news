import argparse
import configparser
from html.parser import HTMLParser
import os
import pickle
import psycopg2
import randomwriter
from randomwriter import RandomWriter
import re
import requests
from urllib.parse import urlparse

class NewsHTMLParser(HTMLParser):
    """ Parses HTML from a news website, pulling out headline text """


    def __init__(self, save_headline, is_headline_tag):
        self.cur_count = 0
        self.save_headline = save_headline
        self.is_headline_tag = is_headline_tag
        self.headline_count = 0
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
        def is_headline_tag(tag, attrs):
            return ('class', name) in attrs
        return is_headline_tag


class NewsModel:
    @staticmethod
    def update_models(writers, url, is_headline_tag, blacklist={}):
        def save_headline(headline):
            if "ttp://" in headline:
                return False
            endtime_match = re.match('^.*(?P<time>\\d\\d?:\\d{2} [AP]M \\wT)$', headline)
            if endtime_match is not None: # for new york times headlines ending in the time
                headline = headline[:len(headline) - len(endtime_match.group('time'))].strip()
            ret = headline not in blacklist
            if ret:
                for rw in writers:
                    rw.train(headline)
            # mark headlines so they can be ignored on future runs
            blacklist[headline] = False
            return ret
        html_parser = NewsHTMLParser(save_headline, is_headline_tag)
        r = requests.get(url)
        html_parser.feed(r.text)
        return html_parser.headline_count


    @staticmethod
    def get_db_conn():
        url = urlparse(os.environ['DATABASE_URL'])
        return psycopg2.connect(
            database=url.path[1:],
            user = url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )


    @staticmethod
    def get_news_model(name, level=5, strategy=randomwriter.CharacterStrategy):
        with NewsModel.get_db_conn() as conn:
            with conn.cursor() as cur:
                # check if our table exists
                cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables where table_name=%s);", ('models',))
                if not cur.fetchone()[0]:
                    # our table does not exist
                    cur.execute("CREATE TABLE models (id serial PRIMARY KEY, name text NOT NULL UNIQUE, pickle bytea NOT NULL);")
                # get the pickle from the database
                cur.execute("SELECT pickle FROM models WHERE name=%s;", (name,)) 
                res = cur.fetchone()
                if res:
                    res = res[0].tobytes()
                    rw = RandomWriter.unpickle(res)
                else:
                    rw = RandomWriter(level, strategy)
                    pkl = pickle.dumps(rw)
                    cur.execute("INSERT INTO models (name, pickle) VALUES (%s, %s);", (name, pkl))
                    conn.commit()
                return rw


    @staticmethod
    def delete_news_model(name):
        with NewsModel.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM models WHERE name=%s;", (name,))
                conn.commit()


    @staticmethod
    def delete_headlines():
        with NewsModel.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS headlines;")
                conn.commit()


    @staticmethod
    def update_news_models(models):
        config = configparser.ConfigParser()
        config.read('config.ini')
        news_sites = config['NEWS']

        with NewsModel.get_db_conn() as conn:
            with conn.cursor() as cur:
                # get blacklist table
                cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables where table_name=%s);", ('headlines',))
                if not cur.fetchone()[0]:
                    # our table does not exist
                    cur.execute("CREATE TABLE headlines (id serial PRIMARY KEY, headline text NOT NULL UNIQUE);")

                cur.execute("SELECT headline FROM headlines;")
                last_headlines = cur.fetchall()
                last_headlines = set(res[0] for res in last_headlines)
                blacklist = dict.fromkeys(last_headlines, True)

                if isinstance(models, str):
                    models = {models : None}

                writers = dict((NewsModel.get_news_model(name) if settings is None else NewsModel.get_news_model(name, settings[0], settings[1]), name) for name, settings in models.items())

                for url, class_name in news_sites.items():
                    print(url, NewsModel.update_models(writers, "http://" + url,
                        NewsHTMLParser.identify_headline_class(class_name),
                        blacklist))

                for headline, can_remove in blacklist.items():
                    if headline not in last_headlines:
                        # new headline found
                        cur.execute("INSERT INTO headlines (headline) VALUES (%s);", (headline,))
                    elif can_remove:
                        cur.execute("DELETE FROM headlines WHERE headline=%s;", (headline,))


                for rw, name in writers.items():
                    pkl = pickle.dumps(rw)
                    cur.execute("UPDATE models SET pickle=%s WHERE name=%s", (pkl, name))
                conn.commit()

if __name__ == '__main__':
    models = {
        'news_model' : None,
        'word_model' : (5, randomwriter.WordStrategy),
    }
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd')
    update_parser = subparsers.add_parser('update')
    update_parser.add_argument('-o', '--omit', default=[], nargs='+', choices=list(models.keys()))
    delete_parser = subparsers.add_parser('delete')
    delete_parser.add_argument('models', nargs='*', choices=list(models.keys()) + [[]]) # no arguments means delete headlines only

    args = parser.parse_args()
    if args.cmd == 'update':
        for model in args.omit:
            del models[model]
        NewsModel.update_news_models(models)
    elif args.cmd == 'delete':
        for model in args.models:
            NewsModel.delete_news_model(model)
        NewsModel.delete_headlines()
