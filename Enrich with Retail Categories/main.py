import quixstreams as qx
import os
import pandas as pd
import redis

# Quix injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient()

# Use Input / Output topics to stream data in or out of your service
topic_consumer = client.get_topic_consumer(os.environ["input"], auto_offset_reset=qx.AutoOffsetReset.Earliest, consumer_group = "lookup-data-id1")
topic_producer = client.get_topic_producer(os.environ["output"])

# Create a Redis client
r = redis.Redis(
  host=os.environ["redishost"],
  port=11226,
  username=os.environ["redisuser"],
  password=os.environ["redispw"])

# Function to fetch product name from Redis
def get_product_name(product_id):
    return r.get(product_id).decode('utf-8')

def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):

    # Transform data frame here in this method. You can filter data or add new features.
    # Assume df is your dataframe and 'product_id' is the column with product IDs
    df['product_name'] = df['Product Page URL'].apply(get_product_name)
    # Pass modified data frame to output stream using stream producer.
    # Set the output stream id to the same as the input stream or change it,
    # if you grouped or merged data with different key.
    stream_producer = topic_producer.get_or_create_stream(stream_id = stream_consumer.stream_id)
    stream_producer.timeseries.buffer.publish(df)


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