import os
import boto3
import logging

import boto3

# Configure logging
tail = logging.getLogger()
tail.setLevel(logging.INFO)

# Environment variables
EC2_TAG_KEY = os.getenv('EC2_TAG_KEY', 'ManagedBy')  # Tag key for identifying managed instances
EC2_TAG_VALUE = os.getenv('EC2_TAG_VALUE', 'MyScaler')  # Tag value for identifying managed instances
REGION = os.getenv('AWS_REGION', 'us-east-1')
TARGET_GROUP_ARN = os.getenv('TARGET_GROUP_ARN')  # ARN of the existing target group

# AWS clients
elbv2 = boto3.client('elbv2', region_name=REGION)
ec2  = boto3.client('ec2', region_name=REGION)

def fetch_managed_instances() -> list[str]:
    """List EC2 instance IDs tagged for this scaler and in running state."""
    resp = ec2.describe_instances(
        Filters=[
            {'Name': f'tag:{EC2_TAG_KEY}', 'Values': [EC2_TAG_VALUE]},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    instances = [i['InstanceId'] for r in resp['Reservations'] for i in r['Instances']]
    logging.info(f"Managed instances: {instances}")
    return instances

def remove_instances(instance_ids: list[str]):
    """Terminate specified EC2 instances."""
    if not instance_ids:
        logging.info("No instances to remove.")
        return
    logging.info(f"Terminating instances: {instance_ids}")
    ec2.terminate_instances(InstanceIds=instance_ids)


def register_targets(instance_ids: list[str]):
    """Register instances into the target group."""
    targets = [{'Id': iid} for iid in instance_ids]
    elbv2.register_targets(TargetGroupArn=TARGET_GROUP_ARN, Targets=targets)
    logging.info(f"Registered to TG: {instance_ids}")


def deregister_targets(instance_ids: list[str]):
    """Deregister instances from the target group."""
    targets = [{'Id': iid} for iid in instance_ids]
    elbv2.deregister_targets(TargetGroupArn=TARGET_GROUP_ARN, Targets=targets)
    logging.info(f"Deregistered from TG: {instance_ids}")