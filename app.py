#!/usr/bin/env python3
import os

import aws_cdk as cdk

from common.db import DBStack
from common.vpc import VpcStack
from contents_platform.cloudfront import CloudFrontStack
from contents_platform.post_upload import PostUploadStack
from manage_platform.ec2 import ManagementServiceStack

app = cdk.App()

vpc_stack = VpcStack(
    app,
    "VpcStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

db_stack = DBStack(
    app,
    "DBStack",
    vpc=vpc_stack.vpc,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

CloudFrontStack(
    app,
    "CloudFrontStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

PostUploadStack(
    app,
    "PostUploadStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

ManagementServiceStack(
    app,
    "ManagementServiceStack",
    vpc=vpc_stack.vpc,
    db_security_group=db_stack.security_group,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

# EcrToElasticBeanstalkPipelineStack(
#     app,
#     "EcrToElasticBeanstalkPipelineStack",
#     env=cdk.Environment(
#         account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
#     ),
# )
app.synth()
