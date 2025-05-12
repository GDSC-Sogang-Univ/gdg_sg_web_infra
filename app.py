#!/usr/bin/env python3
import os

import aws_cdk as cdk

from common.db import DBStack
from common.vpc import VpcStack
from contents_platform.api_server import ContentsPlatformAPIStack
from contents_platform.cloudfront import CloudFrontStack
from contents_platform.post_upload import PostUploadStack

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

ContentsPlatformAPIStack(
    app,
    "ContentsPlatformAPIStack",
    vpc=vpc_stack.vpc,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

app.synth()
