#!/usr/bin/env python3
import os

import aws_cdk as cdk

from contents_platform.cloudfront import CloudFrontStack
from contents_platform.post_upload import PostUploadStack

app = cdk.App()

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


# EcrToElasticBeanstalkPipelineStack(
#     app,
#     "EcrToElasticBeanstalkPipelineStack",
#     env=cdk.Environment(
#         account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
#     ),
# )
app.synth()
