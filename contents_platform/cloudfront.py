from aws_cdk import CfnOutput, Fn, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from constructs import Construct


class CloudFrontStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SSL/TLS 인증서 요청 (ACM을 통해 도메인 검증)
        bucket = s3.Bucket(
            self,
            "gdg-web-static",
            bucket_name="gdg-web-static",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,  # 퍼블릭 접근 허용
            block_public_access=s3.BlockPublicAccess(  # 퍼블릭 액세스 차단 설정
                block_public_acls=False,  # ACL 기반 차단 해제
                block_public_policy=False,  # 퍼블릭 버킷 정책 허용
                ignore_public_acls=True,  # 퍼블릭 ACL 무시
                restrict_public_buckets=False,  # 퍼블릭 버킷 제한 비활성화
            ),
            removal_policy=RemovalPolicy.DESTROY,  # 스택 삭제 시 버킷 삭제
        )

        stage_bucket = s3.Bucket(
            self,
            "gdg-web-static-stage",
            bucket_name="gdg-web-static-stage",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,  # 퍼블릭 접근 허용
            block_public_access=s3.BlockPublicAccess(  # 퍼블릭 액세스 차단 설정
                block_public_acls=False,  # ACL 기반 차단 해제
                block_public_policy=False,  # 퍼블릭 버킷 정책 허용
                ignore_public_acls=True,  # 퍼블릭 ACL 무시
                restrict_public_buckets=False,  # 퍼블릭 버킷 제한 비활성화
            ),
            removal_policy=RemovalPolicy.DESTROY,  # 스택 삭제 시 버킷 삭제
        )

        # CloudFront 배포 생성
        distribution = cloudfront.Distribution(
            self,
            "GdgWebCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(bucket),  # S3 버킷을 CloudFront 원본으로 설정
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            enable_ipv6=False,  # IPv6 비활성화
            price_class=cloudfront.PriceClass.PRICE_CLASS_200,
            geo_restriction=cloudfront.GeoRestriction.allowlist(  # 지리적 제한 설정
                "KR",  # 한국 지역 허용
            ),
            default_root_object="index.html",  # 기본 문서 설정
        )

        stage_distribution = cloudfront.Distribution(
            self,
            "GdgWebStageCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    stage_bucket
                ),  # S3 버킷을 CloudFront 원본으로 설정
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            enable_ipv6=False,  # IPv6 비활성화
            price_class=cloudfront.PriceClass.PRICE_CLASS_200,
            geo_restriction=cloudfront.GeoRestriction.allowlist(  # 지리적 제한 설정
                "KR",  # 한국 지역 허용
            ),
            default_root_object="index.html",  # 기본 문서 설정
        )

        # CloudFront 배포 URL 출력
        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="The CloudFront distribution URL for your website",
        )
