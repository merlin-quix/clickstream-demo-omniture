import quixstreams as qx
import pandas as pd
import time
from collections import defaultdict
import requests
import os
from collections import deque
from datetime import datetime

# Initialize Kafka consumer
client = qx.QuixStreamingClient()

topic_consumer = client.get_topic_consumer(os.environ["input"], auto_offset_reset=qx.AutoOffsetReset.Earliest, consumer_group = "window-calc")

# Initialize state
ip_to_urls = defaultdict(list)

# Initialize a deque to keep track of webhook calls
webhook_calls = deque()

# Placeholder for webhook URL
webhook_url = 'https://hook.eu2.make.com/vdlchysoq63ejngltbji6co037wi748g'

def call_webhook(webhook_url,ip_address,unique_urls):
    global webhook_calls

    # Get the current time
    current_time = time.time()

    # Remove timestamps older than an hour (3600 seconds)
    webhook_calls = deque([t for t in webhook_calls if current_time - t < 3600])

    # Check if we've exceeded the rate limit
    if len(webhook_calls) >= 10:
        print("Rate limit exceeded. Skipping webhook call.")
        return

    # Call the webhook (replace with actual call)
    print("######### CALLING WEBHOOK ######### ")
    requests.post(webhook_url, json={'ip_address': ip_address, 'unique_urls': unique_urls})

    # Add the current timestamp to the deque
    webhook_calls.append(current_time)


def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    # Transform data frame here in this method. You can filter data or add new features.
    # Parse the message
    #print(df.to_markdown())
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')
    timestamp = df['timestamp'].iloc[0]
    #print(f"TIMESTAMP: {timestamp}")
    ip_address = df['IP Address'].iloc[0]
    #print(f"IP ADDRESS: {ip_address}")
    product_url = df['Product Page URL'].iloc[0]
    print(f"Page Interaction: at {timestamp}, {ip_address} visited {product_url}")
    #current_time = timestamp

    # Update state
    ip_to_urls[ip_address] = [(url, vtime) for url, vtime in ip_to_urls[ip_address] if timestamp - vtime <= timedelta(minutes=60)]
    ip_to_urls[ip_address].append((product_url, timestamp))
    #print(ip_to_urls)

    # Check condition
    unique_urls = len(set(url for url, _ in ip_to_urls[ip_address]))
    if unique_urls >= 3:
        # Trigger webhook
        call_webhook(webhook_url, ip_address, unique_urls)
        print(f'Triggered webhook for IP {ip_address} with {unique_urls} unique URLs.')

# Handle event data from samples that emit event data
def on_event_data_received_handler(stream_consumer: qx.StreamConsumer, data: qx.EventData):
    print(data)
    # handle your event data here

def on_stream_received_handler(stream_consumer: qx.StreamConsumer):
    # subscribe to new DataFrames being received
    # if you aren't familiar with DataFrames there are other callbacks available
    # refer to the docs here: https://docs.quix.io/sdk/subscribe.html
    stream_consumer.events.on_data_received = on_event_data_received_handler # register the event data callback
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_received_handler


# subscribe to new streams being received
topic_consumer.on_stream_received = on_stream_received_handler

print("Listening to streams. Press CTRL-C to exit.")

# Handle termination signals and provide a graceful exit
qx.App.run()
