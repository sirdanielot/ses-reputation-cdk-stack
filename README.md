![alt text](https://github.com/SirDanielot/ses-reputation-cdk-stack/blob/master/assets/environment-diagram.png)

# SES Reuptation CDK Stack

If you haven't used or deployed using CDK before, it is worth reading the [Working with the AWS CDK in Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html) documentation.

This stack will launch CloudWatch Alarms for the following SES Metrics:
 - Daily SES Send Count - (Warning: 60% | Alert: 80%)
 - Daily SES Bounce Count - (Warning: 5% | Alert: 10%)
 - Daily SES Complaint Count - (Warning: 0.1% | Alert 0.5%)

..and also deploy a Lambda function that will integrate with your RDS, to log email sends, bouncebacks and a seperate table to log emails that aren't within the database.

## How to use this Stack?

Update the 'config.json' file and update any missing values.

- rds_vpc = The VPC that the RDS is contained in, as the Lambda function will be provisioned in the same VPC. (This CDK could be modified to include VPC peering if required.
- rds_subnet_ids = The subnet(s) the RDS is contained in.
- rds_security_group = Any Security Group ID that is attached to the RDS, to allow for a MySQL connection from Lambda <-> RDS.

For each alarm, you will also need to add in the SNS Topic ARN that you want the alarms to send to.

```json
{
    "rds_vpc": "",
    "rds_subnets_ids": [""],
    "rds_security_group": ""
}
{
  "alarms": [
   {
     "sns_arn": ""   
   }
  ]
}
```

## MySQL Database Structure

The MySQL database structure file has been included in [sql/database.sql](https://github.com/sirdanielot/ses-reputation-cdk-stack/blob/master/sql/database.sql)

Note: You don't neccessarily have to follow this structure, it was just provided as a base example.

If changes are required to integrate with your database, you can modify the Lambda function in [resources](https://github.com/sirdanielot/ses-reputation-cdk-stack/blob/master/resources/lambda_function.py).
