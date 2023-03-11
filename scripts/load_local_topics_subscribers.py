import os

from google.cloud import pubsub_v1

project_id = "test-project"
topic_id = "test-topic"
subscriber_name = "test-topic-sub"

os.environ['PUBSUB_EMULATOR_HOST'] = 'localhost:8681'

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

topic = publisher.create_topic(request={"name": topic_path})

print(f"Created topic: {topic.name}")

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscriber_name)

subscription = subscriber.create_subscription(
    request={"name": subscription_path, "topic": topic_path}
)

print(f"Created subscription: {subscription.name}")