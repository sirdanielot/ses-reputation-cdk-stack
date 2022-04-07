from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_source,
    aws_ec2 as ec2,
    aws_iam as iam
)

import os
import json
import boto3
import math
from constructs import Construct

class SesEnvironmentStack(Stack):

    def get_ses_daily_quota(self) -> int:
        client = boto3.client("ses")
        result = client.get_send_quota()
        if result != None:
            if 'Max24HourSend' in result:
                return int(result['Max24HourSend'])
        return 200
    
    def create_cloudwatch_alarm(self, metric_name: str, metric_namespace: str, alarm_name: str, alarm_description: str, alarm_threshold: int, alarm_sns_topic: sns.Topic):
        metric = cloudwatch.Metric(
            metric_name=metric_name,
            namespace=metric_namespace,
            period=Duration.hours(24),
            statistic="Sum"
        )

        new_alarm = cloudwatch.Alarm(
            self,
            id=alarm_name,
            alarm_name=alarm_name,
            alarm_description=alarm_description,
            metric=metric,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            threshold=alarm_threshold
        )

        new_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_sns_topic))

    def import_lambda(self, lambda_function_name: str, lambda_vpc: ec2.Vpc, lambda_vpc_subnets: ec2.SubnetSelection, lambda_security_group: ec2.SecurityGroup, lambda_role: iam.Role, lambda_trigger_sns_topic: sns.Topic, lambda_environment_variables: dict):
        imported_function = lambda_.Function(
            self, 
            id="Imported-Function",
            function_name=lambda_function_name,
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(os.getcwd(), "resources/lambda-package.zip")),
            environment=lambda_environment_variables,
            vpc=lambda_vpc,
            security_groups=[lambda_security_group],
            role=lambda_role,
            vpc_subnets=lambda_vpc_subnets
        )

        imported_function.add_event_source(lambda_event_source.SnsEventSource(lambda_trigger_sns_topic))

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        config = json.loads(open("config.json", "r").read())

        ## Create CloudWatch Alarms
        ses_daily_quota = self.get_ses_daily_quota()

        for alarm in config['alarms']:
            alarm_name = alarm['name']
            alarm_description = alarm['description']
            alarm_percent = alarm['percent']
            alarm_sns = alarm['sns_arn']
            alarm_metric_namespace = alarm['metric']['namespace']
            alarm_metric_name = alarm['metric']['name']

            # Existing Resource Lookup: SNS Topic
            alarm_topic = sns.Topic.from_topic_arn(
                self, 
                id='{}-SNS-Lookup'.format(alarm_name), 
                topic_arn=alarm_sns
                )

            # Create CloudWatch Alarm
            self.create_cloudwatch_alarm(
                metric_name=alarm_metric_name,
                metric_namespace=alarm_metric_namespace,
                alarm_name=alarm_name,
                alarm_description=alarm_description,
                alarm_threshold=math.ceil((ses_daily_quota / 100) * alarm_percent),
                alarm_sns_topic=alarm_topic
            )

        ## Import Lambda Function
        lambda_vpc = ec2.Vpc.from_lookup(
            self, 
            id='Lambda-VPC-Lookup',
            vpc_id=config['rds_vpc']
        )

        # Existing Resource Lookup: RDS + Lambda Security Group
        lambda_security_group_id = config['rds_security_group']
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            id="Lambda-Security-Group-Lookup",
            security_group_id=lambda_security_group_id
        )
    
        lambda_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(lambda_security_group_id), 
            connection=ec2.Port.tcp(3306)
        )

        # Existing Resource Lookup: Lambda SNS Topic Trigger
        lambda_trigger_sns_topic = sns.Topic.from_topic_arn(
                self, 
                id='Lambda-SNS-Lookup', 
                topic_arn=config['lambda']['sns_trigger_arn']
            )
        
        # Lambda Environment Variables
        lambda_environment_variables = config['lambda']['environment_variables']
        
        # Lambda VPC Subnet Selection
        lambda_vpc_subnets = ec2.SubnetSelection(
            subnet_filters=[ec2.SubnetFilter.by_ids(config['rds_subnets_ids'])]
        )

        lambda_name = config['lambda']['function_name']
        lambda_role_name = '{}-Lambda-Role'.format(lambda_name)

        # Create new IAM Role for Lambda Function
        lambda_role = iam.Role(
            self, 
            id="Lambda-Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Lambda role assigned to {}".format(lambda_name),
            role_name=lambda_role_name
        )

        # Add Lambda Managed Policy
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"))

        # Create custom Policy Document for CloudWatch / Secrets Manager access
        lambda_role_policy_document = iam.PolicyDocument.from_json(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "VisualEditor0",
                        "Effect": "Allow",
                        "Action": [
                            "cloudwatch:PutMetricData",
                            "cloudwatch:GetMetricData",
                            "cloudwatch:ListMetrics",
                            "secretsmanager:ListSecrets"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "VisualEditor1",
                        "Effect": "Allow",
                        "Action": "logs:CreateLogGroup",
                        "Resource": "arn:aws:logs:*:*:log-group:*"
                    },
                    {
                        "Sid": "VisualEditor2",
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue",
                            "logs:PutLogEvents"
                        ],
                        "Resource": [
                            "arn:aws:secretsmanager:*:*:secret:{}{}".format(config['lambda']['environment_variables']['SECRETS_MANAGER_SECRET'], '*'),
                            "arn:aws:logs:*:*:log-group:*:log-stream:*"

                        ]
                    }
                ]
            }
        )
        
        # Create the new Role Policy from the Policy Document
        lambda_role_policy = iam.Policy(
            self,
            id='Lambda-Role-Policy',
            policy_name='{}-Policy'.format(lambda_role_name),
            document=lambda_role_policy_document
        )

        # Attach policy to Lambda Role
        lambda_role_policy.attach_to_role(lambda_role)

        # Create the Lambda Function from /resources/lambda-package.zip
        self.import_lambda(
            lambda_function_name=lambda_name,
            lambda_vpc=lambda_vpc,
            lambda_vpc_subnets=lambda_vpc_subnets,
            lambda_security_group=lambda_security_group,
            lambda_role=lambda_role,
            lambda_trigger_sns_topic=lambda_trigger_sns_topic, 
            lambda_environment_variables=lambda_environment_variables
        )