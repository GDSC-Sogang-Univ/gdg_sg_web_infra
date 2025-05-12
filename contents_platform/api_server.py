from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from constructs import Construct


class ContentsPlatformAPIStack(Stack):

    def __init__(
        self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR 리포지토리 생성
        repository = ecr.Repository(
            self,
            "ContentsPlatformServerRepository",
            repository_name="contents-platform-api",
        )

        # ECS 클러스터 생성
        cluster = ecs.Cluster(
            self,
            "ContentsPlatformCluster",
            vpc=vpc,
            cluster_name="EcsCluster",
            container_insights=True,
        )

        # Fargate Task 정의
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=256,
            memory_limit_mib=512,
        )

        # 컨테이너 추가 - ECR 이미지 사용
        container = task_definition.add_container(
            "ApiContainer",
            image=ecs.ContainerImage.from_ecr_repository(repository, tag="latest"),
        )

        container.add_port_mappings(ecs.PortMapping(container_port=8000))

        # Fargate 서비스 생성
        service = ecs.FargateService(
            self,
            "ContentsPlatformAPIService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            assign_public_ip=True,
            service_name="FargateService",
        )
