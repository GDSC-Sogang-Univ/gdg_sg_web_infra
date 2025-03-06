from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct


class ManagementServiceStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        db_security_group: ec2.SecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        security_group = ec2.SecurityGroup(
            self,
            "ManagementServiceSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
        )

        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP inbound",
        )

        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS inbound",
        )

        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "SSH inbound",
        )

        # DB security group에 허용
        db_security_group.add_ingress_rule(
            security_group,
            ec2.Port.tcp(5432),
            "Allow PostgreSQL inbound",
        )

        ec2_instance_role = iam.Role(
            self,
            "SSMManagedInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                )
            ],
        )

        # Amazon Linux 2023 AMI기반 Docker & Docker Compose 설치
        customn_user_data = ec2.UserData.for_linux(shebang="#!/bin/bash\n")

        customn_user_data.add_commands(
            "sudo yum update -y",
            "sudo yum install -y docker",
            "sudo service docker start",
            "sudo usermod -a -G docker ec2-user",
            "sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/bin/docker-compose",
            "sudo chmod +x /usr/bin/docker-compose",
        )

        ec2_instance = ec2.Instance(
            self,
            "MemberManagementInstance",
            instance_name="MemberManagementInstance",
            security_group=security_group,
            role=ec2_instance_role,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO
            ),
            ssm_session_permissions=True,
            machine_image=ec2.MachineImage.latest_amazon_linux2(
                cpu_type=ec2.AmazonLinuxCpuType.ARM_64
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            user_data=customn_user_data,
        )
