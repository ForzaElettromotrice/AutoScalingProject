import json
from typing import Any

import boto3

ACCOUNT_ID = 975049967346
TARGET_ID = "d56e9f18cdf040d0"
L = 20
U = 50
ALPHA = 0.75

def scale_out(u: int, n: int) -> int:
    Ub = n * (u - L) / L
    Lb = n * (u - U) / U
    return round(ALPHA * Lb + (1.0 - ALPHA) * Ub)

def scale_in(u: int, n: int) -> int:
    Lb = n * (L - u) / L
    Ub = n * (U - u) / U
    return round(ALPHA * Ub + (1.0 - ALPHA) * Lb)

def daje(event: dict, context: dict):
    isntance_id = event["alarmData"]["configuration"]["metrics"][0]["metricStat"]["metric"]["dimensions"]["InstanceId"]
    u = event["alarmData"]["state"]["reasonData"]["recentDatapoints"][-1]
    n = None

def modify_alarm(instances:list[str], metrics:list[dict]):
    cloudwatch = boto3.client('cloudwatch')

    del metrics[-1]

    for idx, instance_id in enumerate(instances):
        metrics.append({
            'id': f'm{idx}',
            'metricstat': {
                'metric': {
                    'namespace': 'AWS/EC2',
                    'name': 'CPUUtilization',
                    'dimensions': [
                        {
                            'InstanceId': instance_id
                        },
                    ]
                },
                'period': 300,
                'stat': 'Average',
            },
            'returnData': False
        })

    # Definizione dell'espressione matematica per calcolare la media
    expression = {
        'Id': 'e1',
        'Expression': 'AVG(' + ','.join([f'm{idx}' for idx in range(len(instances))]) + ')',
        'Label': 'Average CPU Utilization',
        'ReturnData': True
    }

    # Aggiunta dell'espressione alla lista delle metriche
    metrics.append(expression)

    # Creazione dell'allarme
    cloudwatch.put_metric_alarm(
        AlarmName = 'Average_CPU_Utilization',
        AlarmDescription = 'Allarme quando l\'utilizzo medio delle CPU supera il 50%',
        ActionsEnabled = True,
        EvaluationPeriods = 1,
        Threshold = 50.0,
        ComparisonOperator = 'GreaterThanThreshold',
        Metrics = metrics,
        AlarmActions = [
            f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:scaleIn"
        ],
        TreatMissingData = 'missing',
        Unit = 'Percent'
    )

def modify_loadbalancer(instances:list[str]):

    elbv2 = boto3.client('elbv2')

    target_group_arn = f'arn:aws:elasticloadbalancing:us-east-1:{ACCOUNT_ID}:targetgroup/TargetTest/{TARGET_ID}'

    targets = [{ 'id': instance_id } for instance_id in instances]

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
    return instances



def lambdaScaleOut(event: dict, context: dict):
    u = event["alarmData"]["state"]["reasonData"]["recentDatapoints"][-1]
    n = len(event["alarmData"]["configuration"]["metrics"])-1
    toAdd = scale_out(u, n)
    if n <=0:
        return {
        'statusCode': 200,
        'body': json.dumps('Nothing to do!')
    }

    instances = createEC2(toAdd)
    modify_alarm(instances, event["alarmData"]["configuration"]["metrics"])
    modify_loadbalancer(instances)
    return {
        'statusCode': 200,
        'body': json.dumps('Scale out done with success!')
    }


if __name__ == '__main__':
    print(scale_in(10, 5))
    print(scale_out(60, 5))
