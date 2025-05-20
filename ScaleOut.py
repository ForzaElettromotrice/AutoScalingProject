import json

import boto3

TARGET_ID = "d56e9f18cdf040d0"
L = 20
U = 50
ALPHA = 0.75

def scale_out(u: int, n: int) -> int:
    Ub = n * (u - L) / L
    Lb = n * (u - U) / U
    return round(ALPHA * Lb + (1.0 - ALPHA) * Ub)

def modify_alarm_out(instances:list[str], metrics:list[dict], accountId: str):
    cloudwatch = boto3.client('cloudwatch')

    del metrics[-1]

    for idx, instance_id in enumerate(instances):
        metrics.append({
            'Id': f'm{idx}',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CpuUtilization',
                    'Dimensions': [
                        {
                            "Name": "InstanceId",
                            'Value': instance_id
                        },
                    ]
                },
                'Period': 300,
                'Stat': 'Average',
                'Unit': 'Percent'
            },
            'ReturnData': False
        })

    # Definizione dell'espressione matematica per calcolare la media
    expression = {
        'Id': 'e1',
        'Expression': 'AVG([' + ','.join([f'm{idx}' for idx in range(len(instances))]) + '])',
        'Label': 'Average CPU Utilization',
        'ReturnData': True
    }

    # Aggiunta dell'espressione alla lista delle metriche
    metrics.append(expression)

    # Creazione dell'allarme
    cloudwatch.put_metric_alarm(
        AlarmName = 'UpperBoundCpuUtilization',
        AlarmDescription = 'Allarme quando l\'utilizzo medio delle CPU supera il 50%',
        ActionsEnabled = True,
        EvaluationPeriods = 1,
        Threshold = 50.0,
        ComparisonOperator = 'GreaterThanThreshold',
        Metrics = metrics,
        AlarmActions = [
            f"arn:aws:lambda:us-east-1:{accountId}:function:scaleOut"
        ],
        TreatMissingData = 'missing'
    )

def modify_alarm_in(instances: list[str], metrics: list[dict], accountId: str):
    cloudwatch = boto3.client('cloudwatch')

    del metrics[-1]

    for idx, instance_id in enumerate(instances):
        metrics.append({
            'Id': f'm{idx}',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CpuUtilization',
                    'Dimensions': [
                        {
                            "Name": "InstanceId",
                            'Value': instance_id
                        },
                    ]
                },
                'Period': 300,
                'Stat': 'Average',
                'Unit': 'Percent'
            },
            'ReturnData': False
        })

    # Definizione dell'espressione matematica per calcolare la media
    expression = {
        'Id': 'e1',
        'Expression': 'AVG([' + ','.join([f'm{idx}' for idx in range(len(instances))]) + '])',
        'Label': 'Average CPU Utilization',
        'ReturnData': True
    }

    # Aggiunta dell'espressione alla lista delle metriche
    metrics.append(expression)

    # Creazione dell'allarme
    cloudwatch.put_metric_alarm(
        AlarmName = 'LowerBoundCpuUtilization',
        AlarmDescription = 'Allarme quando l\'utilizzo medio delle CPU è sotto il 20%',
        ActionsEnabled = True,
        EvaluationPeriods = 1,
        Threshold = 20.0,
        ComparisonOperator = 'LessThanThreshold',
        Metrics = metrics,
        AlarmActions = [
            f"arn:aws:lambda:us-east-1:{accountId}:function:scaleIn"
        ],
        TreatMissingData = 'missing'
    )

def add_to_loadbalancer(instances:list[str], accountId: str):

    elbv2 = boto3.client('elbv2')

    target_group_arn = f'arn:aws:elasticloadbalancing:us-east-1:{accountId}:targetgroup/TargetTest/{TARGET_ID}'

    targets = [{ 'Id': instance_id } for instance_id in instances]

    # Registra le istanze nel gruppo target
    response = elbv2.register_targets(
        TargetGroupArn = target_group_arn,
        Targets = targets
    )

    print("Istanze registrate con successo:", response)

def createEC2(n: int) ->list:
    ec2 = boto3.resource('ec2', region_name = 'us-east-1')

    instances = ec2.create_instances(
        ImageId = 'ami-0953476d60561c955',
        InstanceType = 't2.micro',
        MinCount = n,
        MaxCount = n,
    )

    print(f'Gli ID delle istanze create è: {instances}')

    for instance in instances:
        instance.wait_until_running()
        instance.reload()

    return instances



def lambda_handler(event, context):
    u = event["alarmData"]["state"]["reasonData"]["recentDatapoints"][-1]
    n = len(event["alarmData"]["configuration"]["metrics"])-1
    accountId = event["accountId"]
    
    toAdd = scale_out(u, n)
    if n <=0:
        return {
        'statusCode': 200,
        'body': json.dumps('Nothing to do!')
    }

    instances = createEC2(toAdd)
    modify_alarm_out(instances, event["alarmData"]["configuration"]["metrics"], accountId)
    modify_alarm_in(instances, event["alarmData"]["configuration"]["metrics"], accountId)
    add_to_loadbalancer(instances, accountId)
    return {
        'statusCode': 200,
        'body': json.dumps('Scale out done with success!')
    }

