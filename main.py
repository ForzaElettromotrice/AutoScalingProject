import boto3

L = 20
U = 70
ALPHA = 0.5

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

def createEC2(n: int):
    ec2 = boto3.resource('ec2', region_name = 'us-east-1')

    instances = ec2.create_instances(
        ImageId = 'ami-0953476d60561c955',
        InstanceType = 't2.micro',
        MinCount = n,
        MaxCount = n,
    )

    print(f'Gli ID delle istanze create è: {instances}')

if __name__ == '__main__':
    createEC2(1)
