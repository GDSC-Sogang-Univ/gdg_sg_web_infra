from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from constructs import Construct


class PostUploadStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 버킷 생성
        post_bucket = s3.Bucket(
            self,
            "PostUploadBucket",
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Lambda 함수 생성
        post_upload_lambda = _lambda.Function(
            self,
            "PostUploadLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("notion_lambda"),
            environment={
                "POST_BUCKET": post_bucket.bucket_name,
            },
        )

        post_upload_lambda.lambda_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[post_bucket.bucket_arn + "/*"],
            )
        )

        post_bucket.grant_read_write(post_upload_lambda.lambda_function)
