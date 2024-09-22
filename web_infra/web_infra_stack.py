from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_elasticbeanstalk as eb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from constructs import Construct


class WebInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define VPC for RDS (Elastic Beanstalk can use the default VPC)
        vpc = ec2.Vpc(
            self,
            "NextJsVPC",
            max_azs=2,  # Define how many availability zones to use
            nat_gateways=0,  # Allows outbound traffic to the internet
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )
        # Route 53 Hosted Zone lookup for gdsc.sg
        # hosted_zone = route53.HostedZone.from_lookup(
        #     self, "HostedZone", domain_name="gdsc.sg"
        # )

        # # Request an SSL Certificate for gdsc.sg
        # certificate = acm.Certificate(
        #     self,
        #     "GDSCCertificate",
        #     domain_name="gdsc.sg",  # TODO fix
        #     validation=acm.CertificateValidation.from_dns(hosted_zone),
        # )

        # Create the RDS instance
        db_instance = rds.DatabaseInstance(
            self,
            "NextJsDB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),  # Smallest RDS instance (t3.micro)
            allocated_storage=20,  # Minimum storage
            max_allocated_storage=100,  # Auto-scaling storage
            database_name="nextjsdb",
            credentials=rds.Credentials.from_generated_secret(
                "postgres_admin"
            ),  # Auto-generated password
            removal_policy=RemovalPolicy.DESTROY,  # Use RemovalPolicy directly
            delete_automated_backups=True,
            publicly_accessible=False,
        )

        # Reference existing ECR repository where the image was pushed
        ecr_repo = ecr.Repository.from_repository_name(
            self, "NextJsRepo", "next-production-image"
        )

        # Create an IAM role for Elastic Beanstalk
        instance_profile_role = iam.Role(
            self,
            "InstanceProfileRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSElasticBeanstalkWebTier"
                ),  # 웹 애플리케이션 용
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly"
                ),  # ECR에서 이미지 pull
            ],
        )

        # Create an instance profile for the role
        instance_profile = iam.CfnInstanceProfile(
            self, "InstanceProfile", roles=[instance_profile_role.role_name]
        )

        # Elastic Beanstalk application
        app = eb.CfnApplication(self, "NextJsApp", application_name="NextJsApp")

        # Elastic Beanstalk environment
        env = eb.CfnEnvironment(
            self,
            "NextJsEnvironment",
            environment_name="NextJsEnvironment",
            application_name=app.application_name,
            solution_stack_name="64bit Amazon Linux 2023 v4.3.7 running Docker",
            option_settings=[
                # Set LoadBalancerType to ALB
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:environment",
                    option_name="LoadBalancerType",
                    value="application",
                ),
                # Enable HTTPS on the ALB listener (port 443)
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elbv2:listener:443",
                    option_name="ListenerEnabled",
                    value="true",
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:ec2:vpc",
                    option_name="Subnets",
                    value=",".join([subnet.subnet_id for subnet in vpc.public_subnets]),
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="IamInstanceProfile",
                    value=instance_profile.ref,
                ),
                # eb.CfnEnvironment.OptionSettingProperty(
                #     namespace="aws:elbv2:listener:443",
                #     option_name="SSLCertificateArns",
                #     value=certificate.certificate_arn,
                # ),
                # eb.CfnEnvironment.OptionSettingProperty(
                #     namespace="aws:elbv2:listener:443",
                #     option_name="Protocol",
                #     value="HTTPS",
                # ),
                # Docker image from ECR
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:asg",
                    option_name="MinSize",
                    value="1",  # 최소 인스턴스 수
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:asg",
                    option_name="MaxSize",
                    value="2",  # 최대 인스턴스 수
                ),
                # Database environment variables for Next.js app
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DB_HOST",
                    value=db_instance.db_instance_endpoint_address,
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DB_PORT",
                    value=str(db_instance.db_instance_endpoint_port),
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DB_NAME",
                    value="nextjsdb",
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DB_USER",
                    value="postgres_admin",  # Username as generated above
                ),
                # eb.CfnEnvironment.OptionSettingProperty(
                #     namespace="aws:elasticbeanstalk:application:environment",
                #     option_name="DB_PASSWORD",
                #     value=db_instance.secret.secret_value_from_json(
                #         "password"
                #     ).to_string(),
                # ),
            ],
        )
        # route53.ARecord(
        #     self,
        #     "AliasRecord",
        #     zone=hosted_zone,
        #     target=route53.RecordTarget.from_alias(
        #         targets.LoadBalancerTarget(env.attr_endpoint_url)
        #     ),
        # )
