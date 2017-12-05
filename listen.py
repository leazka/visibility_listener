import requests
import json
from ConfigParser import SafeConfigParser
import argparse
import logging

achtung = False

logging.basicConfig(filename='visibility.log', format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)


def get_visibility(campaign_id, key):
    request = str(config_parser.get('requests', 'campaign_data')) + '&campaign_id=' + campaign_id + '&key=' + key
    get = requests.get(request)

    if 'rc' in str(args):
        try:
            visibility_yesterday = json.loads(get.content)['All']['data'][0]['Vi'][6]['Vr']
            visibility_today = json.loads(get.content)['All']['data'][0]['Vi'][7]['Vr']
        except IndexError:
            logging.warning('JSON received for campaign ' + campaign_id + ' was of unexpected length')
            return 0, 0
    else:
        try:
            visibility_yesterday = json.loads(get.content)['data']['Vi'][6]['Vr']
            visibility_today = json.loads(get.content)['data']['Vi'][7]['Vr']
        except IndexError:
            logging.warning('WARNING: JSON received for campaign ' + campaign_id + ' was of unexpected length, could not get Visibility')
            return 0, 0
    return visibility_yesterday, visibility_today


def get_diff(campaign_id):
    visibility_yesterday, visibility_today = get_visibility(campaign_id, KEY)

    if visibility_yesterday == visibility_today:
        logging.info('Visibility did not change for campaign' + campaign_id)
    try:
        diff = ((abs(visibility_today - visibility_yesterday)) / visibility_yesterday) * 100.0
        if diff > 10:
            alert(campaign_id, diff)
            global achtung
            achtung = True
        logging.info('for campaign #' + campaign_id + ' difference between visibility is %.2f' % diff)
    except ZeroDivisionError:
        logging.warning('WARNING: yesterdays Visibility is 0 for campaign ' + campaign_id)


def alert(campaign_id, diff):
    if 'rc' in str(args):
        message = 'RC! Visibility difference for campaign ' + str(campaign_id) + ' was too big: %.2f' % diff
    else:
        message = 'Visibility difference for campaign ' + str(campaign_id) + ' was too big: %.2f' % diff
    requests.post('https://slack.com/api/chat.postMessage',
                  data={"token": "SLACK_TOKEN",
                        "channel": "SLACK_CHANNEL", "text": message})  
    logging.warning('WARNING: ' + message)


def get_dates(campaign_id, key):
    request = str(config_parser.get('requests', 'campaign_data')) + '&campaign_id=' + campaign_id + '&key=' + key
    get = requests.get(request)

    if 'rc' in str(args):
        try:
            yesterday = json.loads(get.content)['All']['data'][0]['Vi'][6]['Dt']
            today = json.loads(get.content)['All']['data'][0]['Vi'][7]['Dt']
        except IndexError:
            logging.warning(
                'WARNING: JSON received for campaign ' + campaign_id + ' was of unexpected length, could not get dates')
            return 0, 0
    else:
        try:
            yesterday = json.loads(get.content)['data']['Vi'][6]['Dt']
            today = json.loads(get.content)['data']['Vi'][7]['Dt']
        except IndexError:
            logging.warning(
                'WARNING: JSON received for campaign ' + campaign_id + ' was of unexpected length, could not get dates')
            return 0, 0
    return yesterday, today


def get_serp_features(campaign_id, key, date_end):
    request = str(config_parser.get('requests',
                                    'serp_features')) + '&campaign_id=' + campaign_id + '&key=' + key + '&date_end=' + date_end
    get = requests.get(request)
    serp_features = json.loads(get.content)['tracking_position_rankings_overview_organic']['Sfc']
    return dict(serp_features)


def compare_serp_features(campaign_id, yesterday, today):
    serp_features_yesterday = get_serp_features(campaign_id, KEY, yesterday)
    serp_features_today = get_serp_features(campaign_id, KEY, today)
    diff = [k for k in serp_features_yesterday if serp_features_yesterday[k] != serp_features_today[k]]

    for k in diff:
        message = k, ':', serp_features_yesterday[k], '->', serp_features_today[k]
        logging.info('Changes in campaign ' + campaign_id + str(message))

    if len(diff) == 0:
        logging.info('SERP features number did not change for campaign ' + campaign_id)


def check_visibility():
    ids = []

    for i in config_parser.options('ids'):
        ids.append(i)

    for id in ids:
        get_diff(id)
        yesterday, today = get_dates(id, KEY)
        if yesterday != 0 and today != 0:
            compare_serp_features(id, yesterday, today)
        else:
            logging.warning('WARNING: couldnt get SERP features for ' + id + ' because of unexpected campaign_data response')

    if achtung is False:
        if 'rc' in str(args):
            message = 'RC: no extreme Visibility changes detected'
        else:
            message = 'Prod: no extreme Visibility changes detected'
        requests.post('https://slack.com/api/chat.postMessage',
                      data={"token": "SLACK_TOKEN",
                        "channel": "SLACK_CHANNEL", "text": message}) 
        logging.info('No extreme visibility changes detected')


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', '-c', metavar='config', help='config ini file')
    arg_parser.add_argument('unittest_args', nargs='*')
    args = arg_parser.parse_args()
    config_parser = SafeConfigParser()
    config_parser.read(args.config)
    KEY = config_parser.get('credentials', 'key')
    check_visibility()
