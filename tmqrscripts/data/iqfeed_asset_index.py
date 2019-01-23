import pyiqfeed as iq
import time

dtn_product_id = 'NIKOLAS_JOYCE_13424'
dtn_login = '470998'
dtn_password = '43354519'


IQ_FEED = iq.FeedService(product=dtn_product_id,
                         version="IQFEED_LAUNCHER",
                         login=dtn_login,
                         password=dtn_password)


IQ_FEED.launch(timeout=15,
               check_conn=False,
               headless=False,
               nohup=False)
time.sleep(10)

lookup_conn = iq.LookupConn()
#hist_listener = iq.VerboseIQFeedListener("History Bar Listener")
#lookup_conn.add_listener(hist_listener)


with iq.ConnConnector([lookup_conn]) as connector:
    response = lookup_conn.request_symbols_by_filter('ES')

print(response)