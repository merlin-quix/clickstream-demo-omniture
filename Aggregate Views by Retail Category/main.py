import quixstreams as qx
import os
import pandas as pd
import redis

client = qx.QuixStreamingClient()

topic_consumer = client.get_topic_consumer('clickstream-cats', consumer_group = "category-counts")

# Initialize Redis connection
r = redis.Redis(
  host='redis-13263.c304.europe-west1-2.gce.cloud.redislabs.com',
  port=13263,
  username='csaggregator',
  password='M3rl1n-06')

def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):

    # Transform data frame here in this method. You can filter data or add new features.
    # Assume df is your dataframe and 'product_id' is the column with product IDs
    # Since each DataFrame only contains one row, directly extract the 'Product Page URL'
    cat_name = df.loc[0, 'product_name']

    # Check if this URL already has a total in Redis
    previous_count = r.get(cat_name)

    # If it exists, add 1 to the old count
    if previous_count:
        new_count = int(previous_count) + 1
    else:
        new_count = 1

    # Update Redis
    r.set(cat_name, new_count)

    # Output the updated count
    print(f"The running total for {cat_name} is {new_count}.")
    # Pass modified data frame to output stream using stream producer.

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