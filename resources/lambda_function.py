import os
import json
import boto3
import mysql.connector

from dateutil import tz
from datetime import datetime
from dateutil.parser import parse

def get_secrets_manager_secret(secret_name):
    secrets_manager = boto3.client("secretsmanager")
    return secrets_manager.get_secret_value(SecretId=secret_name)

def get_user_id_from_email(connection, email):
    cursor = connection.cursor()
    query = ("SELECT user_id from user WHERE email_address = %s")
    cursor.execute(query, email)
    result = cursor.fetchall()
    if (len(result) > 0):
        return result[0][0]
    else:
        return -1

def get_database_connection():
    secrets_manager_secret = os.getenv('SECRETS_MANAGER_SECRET')
    database = os.getenv('DATABASE_NAME')

    secrets = json.loads(get_secrets_manager_secret(secrets_manager_secret)['SecretString'])
    username = secrets['username']
    password = secrets['password']
    host = secrets['host']
    port = secrets['port']

    return mysql.connector.connect(
        host=host,
        user=username,
        password=password,
        port=port,
        database=database
    )

def add_custom_metric(metric_namespace, metric_name):
    cloudwatch = boto3.client("cloudwatch")
    cloudwatch.put_metric_data(
        Namespace=metric_namespace,
        MetricData=[
            {
                'MetricName': metric_name,
                'Timestamp': datetime.now(),
                'Value': 1.0
            }
        ]
    )
    print("Adding +1 datapoint to {}/{}".format(metric_namespace, metric_name))

def lambda_handler(event, context):
    connection = get_database_connection()
    records = event['Records']
    for record in records:
        print(record)
        
        message = json.loads(record['Sns']['Message'])
        notification_type_lower = message['notificationType'].lower()

        # ---- #
        mail = message['mail']
        headers = mail['headers']

        # ---- #
        timestamp = mail['timestamp']
        message_id = mail['messageId']
        source_address = mail['source']
        source_ip = mail['sourceIp']
        source_arn = mail['sourceArn']
        # ---- #

        if notification_type_lower == "bounce":
            recipients = message[notification_type_lower]['bouncedRecipients']
        elif notification_type_lower == 'delivery':
            recipients = message[notification_type_lower]['recipients']

        # Get Subject from headers
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
        
        # Get all recipients
        for recipient in recipients:
            if notification_type_lower == "bounce":
                destination_address = recipient['emailAddress']
                diagnostic_code = recipient['diagnosticCode']
            elif notification_type_lower == "delivery":
                destination_address = recipient
                diagnostic_code = "OK"
            
            timestamp = parse(timestamp)

            user_id = get_user_id_from_email(connection, [destination_address])

            if user_id > -1:
                query = "INSERT INTO `user_email_log` (user_id, aws_sns_message_id, source_address, subject, source_ip, source_arn, timestamp, status, diagnostic_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                values = (user_id, message_id, source_address, subject, source_ip, source_arn, timestamp, notification_type_lower, diagnostic_code)
                add_custom_metric(os.getenv('METRIC_NAMESPACE'), os.getenv('METRIC_NAME'))
            else:
                query = "INSERT INTO `unvalidated_email_log` (aws_sns_message_id, source_address, destination_address, subject, source_ip, source_arn, timestamp, status, diagnostic_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                values = (message_id, source_address, destination_address, subject, source_ip, source_arn, timestamp, notification_type_lower, diagnostic_code)
         
            timestamp = timestamp.astimezone(tz.tzlocal())

            datetime_query = timestamp.strftime("%Y-%m-%d")

            # Insert Record for each recipient
            cursor = connection.cursor()
            cursor.execute(query, values)
        connection.commit()

    return {
        'statusCode': 200,
        'body': 'Please check logs for details.'
    }