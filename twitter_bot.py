#!/usr/bin/env python3
import argparse
import config_reader
from news_model import NewsModel
import os
import random
from twython import Twython

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
    config = config_reader.read_configs()
    models = config['MODEL_WEIGHTS']
    distribution = [model for model, count in models.items() for i in range(int(count))]
    default_model = random.choice(distribution)

    parser = argparse.ArgumentParser(description="Tweet random news")
    parser.add_argument('--notweet', action='store_true', default=False)
    parser.add_argument('--model', default=default_model, choices=models.keys(), dest='model_name')
    args = parser.parse_args()
    print("Using", args.model_name)
    rw = NewsModel.get_news_model(args.model_name)
    if not rw.trained:
        NewsModel.update_news_models(args.model_name)
    tweet = ""
    tweet_len = 50
    if args.model_name in config['CHARACTER_MODELS']:
        tweet_len = random.randint(-12, 12) + 46
    elif args.model_name in config['WORD_MODELS']:
        tweet_len = random.randint(-20, 20) + 60

    while can_add_to_tweet(tweet, tweet_len):
        text = ""
        for ch in rw.generate_tokens():
            text += ch
            if args.model_name in config['CHARACTER_MODELS']:
                text = add_character_model(tweet, text)
            elif args.model_name in config['WORD_MODELS']:
                text += ' '
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

    if args.notweet:
        print(tweet)
    else:
        twitter = Twython(os.environ['API_KEY'], os.environ['API_SECRET'], os.environ['OAUTH_TOKEN'], os.environ['OAUTH_SECRET'])
        twitter.update_status(status=tweet.strip())
