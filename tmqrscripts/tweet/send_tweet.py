import tweepy
from tmqr.settings import *

class Tweet_System:
    def __init__(self):
        self.api = self.login_to_twitter()
        pass

    def login_to_twitter(self):
        auth = tweepy.OAuthHandler(CONSUMER_KEY,CONSUMER_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN,TWITTER_ACCESS_TOKEN_SECRET)

        api = tweepy.API(auth)
        ret = {}
        ret['api'] = api
        ret['auth'] = auth
        return api

    def post_tweets(self, message):

        # message = "Hello,\nHow are you doing today #testing"

        ret = self.api.update_status(status=message)

    def post_tweets_with_image(self, message, img):

        # message = "Hello,\nHow are you doing today #testing"
        # image = ''
        # ret = self.api.update_with_media(filename='C:/Users/Steve Pickering/Downloads/test.png', status=message)
        ret = self.api.update_with_media(filename=img, status=message)

    def get_followers(self):
        # user = self.api.get_list()
        # print(user.screen_name)
        # print(user.followers_count)
        # for friend in user.friends():
        #     print(friend.screen_name)

        for follower in tweepy.Cursor(self.api.followers).items():
            print(follower)

            # status_list = api.user_timeline(user_handler)
            # status = status_list[0]
            # json_str = json.dumps(status._json)

    def get_public_tweets(self):
        public_tweets = self.api.home_timeline()
        for tweet in public_tweets:
            print(tweet.text)

if __name__ == "__main__":
    ts = Tweet_System()
    # ts.post_tweets()
    ts.post_tweets_with_image()