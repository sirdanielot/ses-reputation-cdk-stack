#!/usr/bin/env python3
import os
import aws_cdk as cdk

from ses_environment_stack import SesEnvironmentStack

app = cdk.App()

environment = cdk.Environment(region='', account='')

SesEnvironmentStack(app, "SesEnvironmentStack", env=environment)

app.synth()