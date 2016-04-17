import argparse
from news_model import NewsHTMLParser, NewsModel

class StubRandomWriter:
    def __init__(self):
        self.lst = []


    def train(self, data):
        self.lst.append(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', type=str)
    parser.add_argument('headline_class', type=str)
    args = parser.parse_args()
    rw = StubRandomWriter()
    NewsModel.update_models([rw], 'http://' + args.url, NewsHTMLParser.identify_headline_class(args.headline_class))
    print(args.url, '=', args.headline_class)
    print(rw.lst)
    print(len(rw.lst))
