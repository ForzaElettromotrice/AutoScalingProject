import json

import boto3

TARGET_ID = "d56e9f18cdf040d0"
AMI_ID = "ami-041eaed69816f260a"
SUBNET_ID = "subnet-00d174113e459d337"
SECURIT_GROUP = "sg-0f56b43bd8d304e75"
L = 20.0
U = 50.0
ALPHA = 0.75

def scale_out(u: int, n: int) -> int:
    Ub = n * (u - L) / L
    Lb = n * (u - U) / U
    return round(ALPHA * Lb + (1.0 - ALPHA) * Ub)

def scale_in(u: int, n: int) -> int:
    Lb = n * (L - u) / L
    Ub = n * (U - u) / U
    return round(ALPHA * Ub + (1.0 - ALPHA) * Lb)

def remove_expression(metrics: list[dict]):
    idx = -1
    for i in range(len(metrics)):
        if "expression" in metrics[i]:
            idx = i
            break
    if idx == -1:
        return
    del metrics[idx]

def modify_alarm_out(instances: list[str], account_id: str):
    cloudwatch = boto3.client('cloudwatch')
    new_metrics = []

    for idx, instance_id in enumerate(instances):
        new_metrics.append({
            'Id': f'm{idx}',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CPUUtilization',
                    'Dimensions': [
                        {
                            "Name": "InstanceId",
                            'Value': instance_id
                        },
                    ]
                },
                'Period': 60,
                'Stat': 'Average',
                'Unit': 'Percent'
            },
            'ReturnData': False
        })

    # Definizione dell'espressione matematica per calcolare la media
    expression = {
        'Id': 'e1',
        'Expression': 'AVG([' + ','.join([f'm{idx}' for idx in range(len(new_metrics))]) + '])',
        'Label': 'Average CPU Utilization',
        'ReturnData': True
    }

    # Aggiunta dell'espressione alla lista delle metriche
    new_metrics.append(expression)

    print(new_metrics)

    # Creazione dell'allarme
    cloudwatch.put_metric_alarm(
        AlarmName = 'UpperBoundCpuUtilization',
        AlarmDescription = f'Allarme quando l\'utilizzo medio delle CPU supera il {U}%',
        ActionsEnabled = True,
        EvaluationPeriods = 1,
        Threshold = U,
        ComparisonOperator = 'GreaterThanThreshold',
        Metrics = new_metrics,
        AlarmActions = [
            f"arn:aws:lambda:us-east-1:{account_id}:function:autoScale"
        ],
        TreatMissingData = 'missing'
    )
def modify_alarm_in(instances: list[str], account_id: str):
    cloudwatch = boto3.client('cloudwatch')
    new_metrics = []

    for idx, instance_id in enumerate(instances):
        new_metrics.append({
            'Id': f'm{idx}',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CPUUtilization',
                    'Dimensions': [
                        {
                            "Name": "InstanceId",
                            'Value': instance_id
                        },
                    ]
                },
                'Period': 60,
                'Stat': 'Average',
                'Unit': 'Percent'
            },
            'ReturnData': False
        })

    # Definizione dell'espressione matematica per calcolare la media
    expression = {
        'Id': 'e1',
        'Expression': 'AVG([' + ','.join([f'm{idx}' for idx in range(len(new_metrics))]) + '])',
        'Label': 'Average CPU Utilization',
        'ReturnData': True
    }

    # Aggiunta dell'espressione alla lista delle metriche
    new_metrics.append(expression)

    # Creazione dell'allarme
    cloudwatch.put_metric_alarm(
        AlarmName = 'LowerBoundCpuUtilization',
        AlarmDescription = f'Allarme quando l\'utilizzo medio delle CPU è sotto il {L}%',
        ActionsEnabled = True,
        EvaluationPeriods = 1,
        Threshold = L,
        ComparisonOperator = 'LessThanThreshold',
        Metrics = new_metrics,
        AlarmActions = [
            f"arn:aws:lambda:us-east-1:{account_id}:function:autoScale"
        ],
        TreatMissingData = 'missing'
    )
def add_to_loadbalancer(instances: list[str], account_id: str):
    elbv2 = boto3.client('elbv2')

    target_group_arn = f'arn:aws:elasticloadbalancing:us-east-1:{account_id}:targetgroup/TargetTest/{TARGET_ID}'

    targets = [{ 'Id': instance_id } for instance_id in instances]

    # Registra le istanze nel gruppo target
    response = elbv2.register_targets(
        TargetGroupArn = target_group_arn,
        Targets = targets
    )

    print("Istanze registrate con successo:", response)
def remove_from_loadbalancer(instances: list[str], account_id: str):
    elbv2 = boto3.client('elbv2')

    target_group_arn = f'arn:aws:elasticloadbalancing:us-east-1:{account_id}:targetgroup/TargetTest/{TARGET_ID}'

    targets = [{ 'Id': instance_id } for instance_id in instances]

    # Deregistra le istanze dal gruppo target
    response = elbv2.deregister_targets(
        TargetGroupArn = target_group_arn,
        Targets = targets
    )

    print("Istanze deregistrate con successo:", response)
def create_ec2(n: int) -> list:
    ec2 = boto3.resource('ec2', region_name = 'us-east-1')

    instances = ec2.create_instances(
        ImageId = AMI_ID,
        InstanceType = 't2.micro',
        MinCount = n,
        MaxCount = n,
        SubnetId = SUBNET_ID,
        SecurityGroupIds = [SECURIT_GROUP]
    )

    for instance in instances:
        instance.wait_until_running()
        instance.reload()

    return instances

def lambda_scale_out(n, u, account_id, metrics):
    to_add = scale_out(u, n)
    if n + to_add >= 9:
        to_add = 9 - n

    if to_add <= 0:
        return {
            'statusCode': 200,
            'body': json.dumps('Nothing to do!')
        }

    remove_expression(metrics)

    instances = [instance.id for instance in create_ec2(to_add)]
    instances.extend([metric["metricStat"]["metric"]["dimensions"]["InstanceId"] for metric in metrics])

    modify_alarm_out(instances, account_id)
    modify_alarm_in(instances, account_id)

    add_to_loadbalancer(instances, account_id)
    return {
        'statusCode': 200,
        'body': json.dumps('Scale out done with success!')
    }
def lambda_scale_in(n, u, account_id, metrics):
    to_remove = scale_in(u, n)
    if n - to_remove <= 0:
        to_remove = n - 1

    if to_remove <= 0:
        return {
            'statusCode': 200,
            'body': json.dumps('Nothing to do!')
        }

    remove_expression(metrics)

    ids = []
    for i in range(to_remove):
        ids.append(metrics[i]["metricStat"]["metric"]["dimensions"]["InstanceId"])

    ec2 = boto3.client('ec2', region_name = 'us-east-1')
    ec2.terminate_instances(InstanceIds = ids)

    instances = [metric["metricStat"]["metric"]["dimensions"]["InstanceId"] for metric in metrics[to_remove:]]

    modify_alarm_out(instances, account_id)
    modify_alarm_in(instances, account_id)

    remove_from_loadbalancer(ids, account_id)

    return {
        'statusCode': 200,
        'body': json.dumps('Scale in done with success!')
    }

def lambda_handler(event, context):
    event["alarmData"]["state"]["reasonData"] = json.loads(event["alarmData"]["state"]["reasonData"])
    u = event["alarmData"]["state"]["reasonData"]["recentDatapoints"][-1]
    account_id = event["accountId"]
    metrics = event["alarmData"]["configuration"]["metrics"]
    n = max(1, len(metrics) - 1)

    if event["alarmData"]["alarmName"] == "UpperBoundCpuUtilization":
        lambda_scale_out(n, u, account_id, metrics)
    elif event["alarmData"]["alarmName"] == "LowerBoundCpuUtilization":
        lambda_scale_in(n, u, account_id, metrics)
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Unknown alarm name!')
        }
    return {
        'statusCode': 200,
        'body': json.dumps('Scaling done with success!')
    }