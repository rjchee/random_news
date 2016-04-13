from twython import Twython
import os
from news_model import NewsModel
import random

def can_add_to_tweet(tweet, tweet_len):
    return len(tweet.strip()) < tweet_len or len(tweet) < 100 and tweet[-1] not in ".,?! "

def add_character_model(tweet, text):
    if (not tweet or tweet[-1] == ' ') and not (text[0].isupper() or text[0].isdigit()):
        text = ""
    elif tweet and tweet[-1].isalpha() and text[0].isupper():
        text = ""
    elif tweet and tweet[-1] in ".,!?" and (not text.startswith(' ') or len(text) > 1 and not text[1].isupper()):
        text = ""
    elif tweet and tweet[-1].isdigit() and not text.startswith(' '):
        text = ""
    elif tweet and tweet[-1] == "'" and text[0] not in "s ":
        text = ""
    return text

def add_word_model(tweet, text):
    if (not tweet or tweet[-2] in '.!?') and not (text[0].isupper() or text[0].isdigit()):
        text = ""
    return text

if __name__ == '__main__':
    CHARACTER_MODEL = 'news_model'
    WORD_MODEL = 'word_model'
    model_name = CHARACTER_MODEL
    rw = NewsModel.get_news_model(model_name)
    if not rw.trained:
        NewsModel.update_news_models(model_name)
    tweet = ""
    tweet_len = 46 + random.randint(-12, 12)

    while can_add_to_tweet(tweet, tweet_len):
        text = ""
        for ch in rw.generate_tokens():
            text += ch + ' '
            if model_name == CHARACTER_MODEL:
                text = add_character_model(tweet, text)
            elif model_name == WORD_MODEL:
                text = add_word_model(tweet, text)
            if not can_add_to_tweet(tweet + text, tweet_len):
                break
        if text:
            print(text)
            tweet += text
    tweet = tweet.strip()
    odd_double_quotes = tweet.count('"') % 2 == 1
    if odd_double_quotes:
        tweet += '"'
    twitter = Twython(os.environ['API_KEY'], os.environ['API_SECRET'], os.environ['OAUTH_TOKEN'], os.environ['OAUTH_SECRET'])
    twitter.update_status(status=tweet.strip())
