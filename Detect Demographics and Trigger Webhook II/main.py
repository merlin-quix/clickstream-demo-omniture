import quixstreams as qx
import pandas as pd
import time
from collections import defaultdict
from datetime import datetime, timedelta
import requests
import time
import os
import threading
from collections import deque

# Initialize Kafka consumer
client = qx.QuixStreamingClient()

topic_consumer = client.get_topic_consumer(os.environ['input'], auto_offset_reset=qx.AutoOffsetReset.Earliest, consumer_group = "window-calc3")

# Initialize state for unique user IDs
user_to_categories = defaultdict(lambda: {"age": None, "gender": None, "categories": []})

# Initialize a deque to keep track of webhook calls
webhook_calls = deque()

# Placeholder for webhook URL
webhook_url = 'https://hook.eu2.make.com/b0yr6fsuhu4fmaeoghrtwtmeb0i05ah1'

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


from datetime import datetime, timedelta
from collections import defaultdict

# Initialize state for unique user IDs
user_to_categories = defaultdict(lambda: {"age": None, "gender": None, "categories": []})

def on_dataframe_received_handler(stream_consumer, df):
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')
    timestamp = df['timestamp'].iloc[0]
    unique_id = df['Visitor Unique ID'].iloc[0]
    gender = df['UserGender'].iloc[0]
    age = df['UserAge'].iloc[0]
    category = df['Product Category'].iloc[0]

    # Update user-specific information
    user_data = user_to_categories[unique_id]
    user_data["age"] = age
    user_data["gender"] = gender
    user_data["categories"] = [(cat, ctime) for cat, ctime in user_data["categories"] if timestamp - ctime <= timedelta(hours=1)]
    user_data["categories"].append((category, timestamp))

    # Check conditions
    if user_data["gender"] == 'F' and 25 <= user_data["age"] <= 35:
        unique_categories = len(set(cat for cat, _ in user_data["categories"]))
        if all(cat in [x[0] for x in user_data["categories"]] for cat in ["clothing", "shoes", "handbags"]):
            # All conditions met, trigger the webhook
            call_webhook(webhook_url, unique_id, unique_categories)
            print(f'Triggered webhook for user {unique_id} matching all criteria.')


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
