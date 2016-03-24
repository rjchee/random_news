from randomwriter import RandomWriter
import randomwriter
from html.parser import HTMLParser
import requests
import os
import configparser
import psycopg2
from urllib.parse import urlparse
import pickle

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
    def __init__(self, name):
        self.name = name

    @staticmethod
    def update_model(rw, url, is_headline_tag, blacklist={}):
        def save_headline(headline):
            if "ttp://" in headline:
                return False
            ret = headline not in blacklist
            if ret:
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


    def get_news_model(self):
        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                # check if our table exists
                cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables where table_name=%s);", ('models',))
                if not cur.fetchone()[0]:
                    # our table does not exist
                    cur.execute("CREATE TABLE models (id serial PRIMARY KEY, name text NOT NULL UNIQUE, pickle bytea NOT NULL);")
                # get the pickle from the database
                cur.execute("SELECT pickle FROM models WHERE name=%s;", (self.name,)) 
                res = cur.fetchone()
                if res:
                    res = res[0].tobytes()
                    rw = RandomWriter.unpickle(res)
                else:
                    rw = RandomWriter(5, randomwriter.CharacterStrategy)
                    pkl = pickle.dumps(rw)
                    cur.execute("INSERT INTO models (name, pickle) VALUES (%s, %s);", (self.name, pkl))
                    conn.commit()
                return rw


    def delete_news_model(self):
        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM models WHERE name=%s;", (self.name,))
                cur.execute("DROP TABLE headlines;")
                conn.commit()


    def update_news_model(self, rw=None):
        config = configparser.ConfigParser()
        config.read('config.ini')
        news_sites = config['NEWS']

        with self.get_db_conn() as conn:
            with conn.cursor() as cur:
                if rw is None:
                    rw = self.get_news_model()
                # get blacklist table
                cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables where table_name=%s);", ('headlines',))
                if not cur.fetchone()[0]:
                    # our table does not exist
                    cur.execute("CREATE TABLE headlines (id serial PRIMARY KEY, headline text NOT NULL UNIQUE);")

                cur.execute("SELECT headline FROM headlines;");
                last_headlines = cur.fetchall()
                last_headlines = set(res[0] for res in last_headlines)
                blacklist = dict.fromkeys(last_headlines, True)

                for url, class_name in news_sites.items():
                    print(url, self.update_model(rw, "http://" + url, NewsHTMLParser.identify_headline_class(class_name), blacklist))

                for headline, can_remove in blacklist.items():
                    if headline not in last_headlines:
                        # new headline found
                        cur.execute("INSERT INTO headlines (headline) VALUES (%s);", (headline,))
                    elif can_remove:
                        cur.execute("DELETE FROM headlines WHERE headline=%s;", (headline,))


                pkl = pickle.dumps(rw)
                cur.execute("UPDATE models SET pickle=%s WHERE name=%s", (pkl, self.name))
                conn.commit()

if __name__ == '__main__':
    model = NewsModel('news_model')
    model.update_news_model()
