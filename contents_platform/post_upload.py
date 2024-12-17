from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

NOTION_DATABASE_ID = "2c248e8d495b4722b002958aa4b8e70e"


class PostUploadStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 버킷 생성
        post_bucket = s3.Bucket(
            self,
            "PostUploadBucket",
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,  # 버킷 삭제 시 객체 유지
        )

        # Secrets Manager에 저장된 Notion API 키
        notion_api_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "NotionApiKey", "notion-api-key"
        )

        # Lambda 함수 생성
        post_upload_lambda = _lambda.Function(
            self,
            "PostUploadLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="main.lambda_handler",
            code=_lambda.Code.from_asset("notion_lambda"),
            timeout=Duration.minutes(15),
            environment={
                "POST_BUCKET": post_bucket.bucket_name,
                "SECRET_NAME": "notion-api-key",
                "DATABASE_ID": NOTION_DATABASE_ID,
            },
        )

        # Lambda의 IAM 역할에 S3 권한 추가
        post_bucket.grant_read_write(post_upload_lambda)

        # Lambda의 IAM 역할에 Secrets Manager 읽기 권한 추가
        notion_api_secret.grant_read(post_upload_lambda)

        # Lambda의 실행 역할에 추가 정책 (S3 및 Secrets Manager 권한 보장)
        post_upload_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "secretsmanager:GetSecretValue",
                ],
                resources=[
                    post_bucket.bucket_arn + "/*",  # S3 버킷의 모든 객체
                    notion_api_secret.secret_arn,  # Secrets Manager ARN
                ],
            )
        )

        # API Gateway 생성
        api = apigateway.RestApi(
            self,
            "PostUploadApi",
            rest_api_name="PostUploadService",
            description="API Gateway for the PostUpload Lambda function.",
        )

        # Lambda 통합 추가
        post_upload_integration = apigateway.LambdaIntegration(
            post_upload_lambda,
            proxy=True,  # 요청을 Lambda에 그대로 전달
        )

        # API 경로 및 메서드 추가
        api_resource = api.root.add_resource("upload")
        api_resource.add_method(
            "POST",
            post_upload_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                    },
                ),
                apigateway.MethodResponse(
                    status_code="403",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                ),
            ],
            request_parameters={
                "method.request.header.Authorization": True,
            },
        )

        # API Gateway에 CORS 추가
        api.root.add_method(
            "OPTIONS",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Headers": "'Authorization'",
                            "method.response.header.Access-Control-Allow-Methods": "'OPTIONS,POST'",
                            "method.response.header.Access-Control-Allow-Origin": "'*'",
                        },
                    )
                ],
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                )
            ],
        )

        # Lambda 함수의 ARN 출력
        CfnOutput(
            self,
            "LambdaFunctionArn",
            value=post_upload_lambda.function_arn,
            description="ARN of the Lambda function",
        )

        # API Gateway 엔드포인트 URL 출력
        CfnOutput(
            self,
            "ApiEndpoint",
            value=api.url,
            description="URL of the API Gateway endpoint (requires Authorization header)",
        )

        # S3 버킷 이름 출력
        CfnOutput(
            self,
            "S3BucketName",
            value=post_bucket.bucket_name,
            description="Name of the S3 bucket",
        )

        # Secrets Manager ARN 출력
        CfnOutput(
            self,
            "SecretsManagerArn",
            value=notion_api_secret.secret_arn,
            description="ARN of the Secrets Manager secret",
        )
