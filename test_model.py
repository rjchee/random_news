from news_model import NewsModel
from news_model import NewsHTMLParser

class StubRandomWriter:
    def __init__(self):
        self.lst = []


    def train(self, data):
        self.lst.append(data)


if __name__ == '__main__':
    rw = StubRandomWriter()
    NewsModel.update_model(rw, "http://www.nytimes.com", NewsHTMLParser.identify_headline_class('story-heading'))
    print(rw.lst)
    print(len(rw.lst))
