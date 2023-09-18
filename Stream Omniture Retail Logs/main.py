# This code will publish the CSV data to a stream as if the data were being generated in real-time.

import quixstreams as qx
import pandas as pd
import time
from datetime import datetime
import os
import threading
import zipfile

# Specify the path to the ZIP file and the extraction directory
log_file_path = 'cleaned-omniture-logs.zip'
users_file_path = 'users.zip'
extract_dir = '.'

# Open the ZIP files and extract their contents (yes this is hacky, bad code)
with zipfile.ZipFile(log_file_path, 'r') as zip_ref:
     zip_ref.extractall(extract_dir)
     print(f'Extracted all contents of {log_file_path} to {extract_dir}')
     
with zipfile.ZipFile(users_file_path, 'r') as zip_ref:
     zip_ref.extractall(extract_dir)
     print(f'Extracted all contents of {users_file_path} to {extract_dir}')


# True = keep original timings.
# False = No delay! Speed through it as fast as possible.
keep_timing = False

# If the process is terminated on the command line or by the container
# setting this flag to True will tell the loops to stop and the code
# to exit gracefully.
shutting_down = False

# Quix Platform injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient('sdk-8c379dcac1d64713b2787faa520cd808')

# print("Using local kafka")
# client = qx.KafkaStreamingClient('127.0.0.1:9092')

# The producer topic is where the data will be published to
# It's the output from this demo data source code.
print("Opening output topic")
producer_topic = client.get_topic_producer(os.environ["output"])

# counters for the status messages
row_counter = 0
published_total = 0

# how many times you want to loop through the data
iterations = 10

def publish_row(row):
    global row_counter
    global published_total

    # create a DataFrame using the row
    df_row = pd.DataFrame([row])

    # add a new timestamp column with the current data and time
    df_row['Timestamp'] = datetime.now()
    streamid = df_row['Visitor Unique ID'].iloc[0]
    streamid = streamid.replace("{","").replace("}","")

    # publish the data to the Quix stream created earlier
    stream_producer = producer_topic.get_or_create_stream(streamid)
    stream_producer.timeseries.buffer.time_span_in_milliseconds = 100
    stream_producer.timeseries.publish(df_row)

    row_counter += 1

    if row_counter == 10:
        row_counter = 0
        published_total += 10
        print(f"Published {published_total} rows")


def process_csv_file(csv_file):
    global shutting_down
    global iterations

    # Read the CSV file into a pandas DataFrame
    print("TSV file loading.")
    df = pd.read_csv(csv_file, sep="\t")
    #df.columns = ['col_' + str(i + 1) for i in range(len(df.columns))]
    # Get subset of columns
    df = df[["Unix Timestamp","Date and Time","Visitor ID","Session ID","Version Information","Image Request","Purchase ID","IP Address","JavaScript Version","Cookies Enabled","Browser Color Depth","Product Page URL","Visitor Unique ID"]]

    print("File loaded.")

    row_count = len(df)
    print(f"Publishing {row_count * iterations} rows.")

    has_timestamp_column = False

    # If the data contains a 'Timestamp'
    if "Unix Timestamp" in df:
        has_timestamp_column = True
        # keep the original timestamp to ensure the original timing is maintained
        df = df.rename(columns={"Unix Timestamp": "original_timestamp"})
        print("Timestamp column renamed.")

    # Get the column headers as a list
    headers = df.columns.tolist()

    # repeat the data 10 times to ensure the replay lasts long enough to
    # inspect and play with the data
    for _ in range(0, iterations):

        # If shutdown has been requested, exit the loop.
        if shutting_down:
            break

        # Iterate over the rows and send them to the API
        for index, row in df.iterrows():

            # If shutdown has been requested, exit the loop.
            if shutting_down:
                break

            # Create a dictionary that includes both column headers and row values
            row_data = {header: row[header] for header in headers}
            publish_row(row_data)

            if not keep_timing or not has_timestamp_column:
                # Don't want to keep the original timing or no timestamp? Thats ok, just sleep for 200ms
                time.sleep(0.11)
            else:
                # Delay sending the next row if it exists
                # The delay is calculated using the original timestamps and ensure the data
                # is published at a rate similar to the original data rates
                if index + 1 < len(df):
                    current_timestamp = pd.to_datetime(row['original_timestamp'], unit='s')
                    next_timestamp = pd.to_datetime(df.at[index + 1, 'original_timestamp'], unit='s')
                    time_difference = next_timestamp - current_timestamp
                    delay_seconds = time_difference.total_seconds()

                    # handle < 0 delays
                    if delay_seconds < 0:
                        delay_seconds = 0

                    time.sleep(delay_seconds)


# Run the CSV processing in a thread
processing_thread = threading.Thread(target=process_csv_file, args=('omniture-logs.tsv',))
processing_thread.start()


# Run this method before shutting down.
# In this case we set a flag to tell the loops to exit gracefully.
def before_shutdown():
    global shutting_down
    print("Shutting down")

    # set the flag to True to stop the loops as soon as possible.
    shutting_down = True


# keep the app running and handle termination signals.
qx.App.run(before_shutdown=before_shutdown)

print("Exiting.")
