import requests
from enum import Enum
from lxml import etree
# from xml.etree.ElementTree import fromstring
from xmljson import badgerfish as bf
import json

from tmqr.settings import *

from tmqr.logs import log

class ORDER_CMD(Enum):
    SIGNAL = 'signal'
    REVERSE = 'reverse'
    POSITION_STATUS = 'positionstatus'

class ORDER_ACTIONS(Enum):
    BUY_TO_OPEN = 'BTO'
    SELL_SHORT = 'SSHORT'
    SELL_TO_OPEN = 'STO'
    BUY_TO_CLOSE = 'BTC'
    SELL_TO_CLOSE = 'STC'

class INSTRUMENT_TYPE(Enum):
    STOCK = 'stock'
    FUTURE = 'future'
    OPTION = 'option'
    FOREX = 'forex'

class ORDER_DURATION_TYPE(Enum):
    DAY_ORDER = 'DAY'
    GOOD_TIL_CANCEL = 'GTC'

class Collective2_Order_Routing:



    def __init__(self, systemid, api_key, pwd):
        log.setup('scripts', 'Collective2_Order_Routing', to_file=True)
        log.info('Collective2_Order_Routing')

        # self.url_main = 'http://www.collective2.com/cgi-perl/signal.mpl?'
        self.url_main = 'https://api.collective2.com/world/apiv3/'
        self.systemid = systemid
        self.api_key = api_key
        self.pwd = pwd

    def __repr__(self):
        # pass
        return f'Collective2_Order_Routing({self.systemid!r},{self.pwd!r})'

    def generate_future_order_params(self, cmd, instrument_type, quantity, symbol, action=None, limit=None, stop=None, duration=None):
        #https://www.collective2.com/cgi-perl/signal.mpl?cmd=signal&systemid=116517033&pw=test&instrument=stock&action=BTO&quant=1&symbol=IBM&duration=DAY
        PARAMS = {
            'cmd':cmd,
            'systemid':self.systemid,
            'pw':self.pwd,
            'instrument':instrument_type,
            'quant':str(quantity),
            'symbol':symbol
        }

        if action != None:
            PARAMS['action'] = action

        if limit != None:
            PARAMS['limit'] = limit

        if stop != None:
            PARAMS['stop'] = stop

        if duration != None:
            PARAMS['duration'] = duration

        return PARAMS

    def send_futures_order(self,order_params):
        #https://www.collective2.com/cgi-perl/signal.mpl?cmd=signal&systemid=116517033&pw=test&instrument=stock&action=BTO&quant=1&symbol=IBM&duration=DAY

        print(order_params)

        return_message = None

        if order_params['cmd'] == ORDER_CMD.SIGNAL.value:
            return_message = self.send_futures_order_signal(order_params)
        elif order_params['cmd'] == ORDER_CMD.REVERSE.value:
            return_message = self.send_futures_order_reversal(order_params)

        return return_message

    def get_system_roster(self):

        sr_json = {
            "apikey" : self.api_key,
            "filter" : "active"
        }

        sr_url = f"{self.url_main}getSystemRoster"

        r = requests.post(url=sr_url,json=sr_json)
        # print(r.text)

        parsed_json = json.loads(r.text)

        # root = etree.fromstring(r.text)

        # print(parsed_json)
        return (parsed_json['ok'])

    

    def send_futures_order_signal(self,order_params):
        #https://www.collective2.com/cgi-perl/signal.mpl?cmd=signal&systemid=116517033&pw=test&instrument=stock&action=BTO&quant=1&symbol=IBM&duration=DAY

        log.setup('scripts', 'Collective2_Order_Routing', to_file=True)

        print(order_params)

        r = requests.post(url=self.url_main, params=order_params)

        log.info(f'Sending Collective2_Order_Routing {order_params}')

        # print(r.content)
        # print(r.headers)
        # print(r.request)
        # print('raw',r.raw)
        # print('response',r.text)

        root = etree.fromstring(r.text)

        print(bf.data(root))

        response = bf.data(root)

        log.info(f'Sending Collective2_Order_Routing {response}')

        return_message = {}
        if 'collective2' in response and 'status' in response['collective2']:
            status = list(response['collective2']['status'].values())
            if 'OK' in status:
                if 'signalid' in response['collective2']:
                    return_message['signalid'] = list(response['collective2']['signalid'].values())[0]

                # if 'price' in response['collective2']:
                #     return_message['price1'] = list(response['collective2']['price'].values())[0]

                if 'comment' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comment'].values())[0]
                if 'comments' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comments'].values())[0]

            if 'error' in status:
                return_message['errortype'] = list(response['collective2']['errortype'].values())[0]

                log.warning('Order error {}'.format(return_message['errortype']))

                if 'comment' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comment'].values())[0]
                    log.warning('Order error comment {}'.format(return_message['comments']))

                if 'comments' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comments'].values())[0]
                    log.warning('Order error comment {}'.format(return_message['comments']))

        # print(signalid)

        # for element in root.iter("ack"):
        #     print(element,element.text)
        # for n in root.iter('')

        return return_message

    def send_futures_order_reversal(self,order_params):
        #https://www.collective2.com/cgi-perl/signal.mpl?cmd=signal&systemid=116517033&pw=test&instrument=stock&action=BTO&quant=1&symbol=IBM&duration=DAY

        log.setup('scripts', 'Collective2_Order_Routing', to_file=True)

        print(order_params)

        r = requests.get(url=self.url_main, params=order_params)

        log.info(f'Sending Collective2_Order_Routing {order_params}')

        root = etree.fromstring(r.text)

        print(bf.data(root))

        response = bf.data(root)

        log.info(f'Sending Collective2_Order_Routing {response}')

        return_message = {}
        signalid = None
        if 'collective2' in response and 'status' in response['collective2']:
            status = list(response['collective2']['status'].values())
            if 'OK' in status:
                if 'signalid1' in response['collective2']:
                    return_message['signalid1'] = list(response['collective2']['signalid1'].values())[0]
                if 'signalid2' in response['collective2']:
                    return_message['signalid2'] = list(response['collective2']['signalid2'].values())[0]

                if 'price1' in response['collective2']:
                    return_message['price1'] = list(response['collective2']['price1'].values())[0]
                if 'price2' in response['collective2']:
                    return_message['price2'] = list(response['collective2']['price2'].values())[0]

                if 'comment' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comment'].values())[0]
                if 'comments' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comments'].values())[0]
            if 'error' in status:
                return_message['errortype'] = list(response['collective2']['errortype'].values())[0]

                log.warning('Order error {}'.format(return_message['errortype']))

                if 'comment' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comment'].values())[0]
                    log.warning('Order error comment {}'.format(return_message['comments']))

                if 'comments' in response['collective2']:
                    return_message['comments'] = list(response['collective2']['comments'].values())[0]
                    log.warning('Order error comment {}'.format(return_message['comments']))

        # print(signalid)

        # for element in root.iter("ack"):
        #     print(element,element.text)
        # for n in root.iter('')

        return return_message

    def position_status_request(self,symbol):
        #http://www.collective2.com/cgi-perl/signal.mpl?cmd=positionstatus&systemid=123&pw=abcd

        PARAMS = {
            'cmd': ORDER_CMD.POSITION_STATUS.value,
            'systemid': self.systemid,
            'pw': self.pwd,
            'symbol': symbol
        }

        log.setup('scripts', 'Collective2_Order_Routing', to_file=True)

        print(PARAMS)

        r = requests.get(url=self.url_main, params=PARAMS)

        log.info(f'Sending Collective2_Order_Routing {PARAMS}')

        print(r.text)

        root = etree.fromstring(r.text)

        print(bf.data(root))

        response = bf.data(root)

        print(response)

        log.info(f'Sending Collective2_Order_Routing {response}')

        return response

        # return_message = {}
        # signalid = None
        # if 'collective2' in response and 'status' in response['collective2']:
        #     status = list(response['collective2']['status'].values())
        #     if 'OK' in status:
        #         if 'signalid1' in response['collective2']:
        #             return_message['signalid1'] = list(response['collective2']['signalid1'].values())[0]
        #         if 'signalid2' in response['collective2']:
        #             return_message['signalid2'] = list(response['collective2']['signalid2'].values())[0]
        #
        #         if 'price1' in response['collective2']:
        #             return_message['price1'] = list(response['collective2']['price1'].values())[0]
        #         if 'price2' in response['collective2']:
        #             return_message['price2'] = list(response['collective2']['price2'].values())[0]
        #
        #         if 'comment' in response['collective2']:
        #             return_message['comments'] = list(response['collective2']['comment'].values())[0]
        #         if 'comments' in response['collective2']:
        #             return_message['comments'] = list(response['collective2']['comments'].values())[0]
        #     if 'error' in status:
        #         return_message['errortype'] = list(response['collective2']['errortype'].values())[0]
        #
        #         log.warning('Order error {}'.format(return_message['errortype']))
        #
        #         if 'comment' in response['collective2']:
        #             return_message['comments'] = list(response['collective2']['comment'].values())[0]
        #             log.warning('Order error comment {}'.format(return_message['comments']))
        #
        #         if 'comments' in response['collective2']:
        #             return_message['comments'] = list(response['collective2']['comments'].values())[0]
        #             log.warning('Order error comment {}'.format(return_message['comments']))

        # print(signalid)

        # for element in root.iter("ack"):
        #     print(element,element.text)
        # for n in root.iter('')

        # return return_message

if __name__ == "__main__":
    cor = Collective2_Order_Routing('116517033','test')
    print(cor)
