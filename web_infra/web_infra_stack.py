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
        vpc = ec2.Vpc(self, "NextJsVPC", max_azs=2)

        # Route 53 Hosted Zone lookup for gdsc.sg
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone", domain_name="gdsc.sg"
        )

        # Request an SSL Certificate for gdsc.sg
        certificate = acm.Certificate(
            self,
            "GDSCCertificate",
            domain_name="gdsc.sg",  # TODO fix
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        # Create the RDS instance
        db_instance = rds.DatabaseInstance(
            self,
            "NextJsDB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_12_5  # TODO fix
            ),
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO
            ),  # Smallest RDS instance (t2.micro)
            allocated_storage=20,  # Minimum storage
            max_allocated_storage=100,  # Auto-scaling storage
            database_name="nextjsdb",
            credentials=rds.Credentials.from_generated_secret(
                "admin"
            ),  # Auto-generated password
            removal_policy=RemovalPolicy.DESTROY,  # Use RemovalPolicy directly
            delete_automated_backups=True,
            publicly_accessible=False,
        )

        # Reference existing ECR repository where the image was pushed
        ecr_repo = ecr.Repository.from_repository_name(
            self, "NextJsRepo", "next-production-image"
        )

        # Elastic Beanstalk application
        app = eb.CfnApplication(self, "NextJsApp", application_name="NextJsApp")

        # Elastic Beanstalk environment
        env = eb.CfnEnvironment(
            self,
            "NextJsEnvironment",
            environment_name="NextJsEnvironment",
            application_name=app.application_name,
            solution_stack_name="64bit Amazon Linux 2 v3.3.10 running Docker",
            option_settings=[
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="REPOSITORY_URI",
                    value=ecr_repo.repository_uri,
                ),
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
                    namespace="aws:elbv2:listener:443",
                    option_name="SSLCertificateArns",
                    value=certificate.certificate_arn,
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elbv2:listener:443",
                    option_name="Protocol",
                    value="HTTPS",
                ),
                # Docker image from ECR
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:container:docker",
                    option_name="Image",
                    value=ecr_repo.repository_uri + ":latest",
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
                    value="admin",  # Username as generated above
                ),
                eb.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DB_PASSWORD",
                    value=db_instance.secret.secret_value_from_json(
                        "password"
                    ).to_string(),
                ),
            ],
        )

        # Grant Elastic Beanstalk permissions to pull from ECR
        eb_role = iam.Role(
            self,
            "ElasticBeanstalkRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSElasticBeanstalkWebTier"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly"
                ),
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
