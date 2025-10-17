- Locate the container for `*-python-test-rig` and copy the container id
- Copy the downloaded `*.whl` file from local to the container. Command - ```docker cp /local/path/to/whl {{Container ID}}/.```
- Log on the container. Command - ```docker exec -it {{Container ID}} bash```
- Install the `*.whl` file. Command - ```pip3 install {{whl file name}} ```
- Open a python3 prompt by typing `python3`, and follow the example for Producer/Consumer

# Python Producer Example

```python
# Import the generated classes
from {{Entity}}Event_lib import {{Entity}}Event, {{Entity}}EventProducer

# Create an event, similar to below, when Entity is UserSignUp  
event = UserSignupEvent(
    userId="bwayne",
    email="bruce@wayne-industries.com",
    signupTimestamp=1699564800000,
    source="batmobile"
)

# Send to Kafka
producer = {{Entity}}EventProducer.create()
producer.send_sync(event)
producer.close()
```

# Python Consumer Example

```python
# Import the generated classes
from {{Entity}}Event_lib import {{Entity}}Event, {{Entity}}EventConsumer

# Consume from Kafka
def handle_incoming(event: {{Entity}}Event):
    print(f"Inbound: {event}")

# Change the consumer group at will
consumer = {{Entity}}EventConsumer.create('{{Entity}}EventConsumerGroup')
consumer.subscribe(handle_incoming)
```
