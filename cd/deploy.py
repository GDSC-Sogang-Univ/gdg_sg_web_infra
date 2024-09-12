from aws_cdk import Stack
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_ecr as ecr
from constructs import Construct


class EcrToElasticBeanstalkPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # 1. ECR 리포지토리 생성
        repository = ecr.Repository(self, "MyRepository")

        # 2. 이미 존재하는 Elastic Beanstalk 애플리케이션과 환경 사용
        existing_application_name = "NextJsApp"
        existing_environment_name = "NextJsEnvironment"

        # 3. CodeBuild 프로젝트 생성 (이미지 빌드 및 푸시)
        project = codebuild.PipelineProject(
            self,
            "MyProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0, privileged=True
            ),
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "pre_build": {
                            "commands": [
                                "echo Logging in to Amazon ECR...",
                                "$(aws ecr get-login --no-include-email --region $AWS_REGION)",
                            ]
                        },
                        "build": {
                            "commands": [
                                "echo Build started on `date`",
                                "echo Building the Docker image...",
                                "docker build -t $REPOSITORY_URI:latest .",
                                "docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            ]
                        },
                        "post_build": {
                            "commands": [
                                "echo Build completed on `date`",
                                "docker push $REPOSITORY_URI:latest",
                                "docker push $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                                "echo Writing image definitions file...",
                                'printf \'[{"name":"container-name","imageUri":"%s"}]\' $REPOSITORY_URI:latest > imagedefinitions.json',
                            ]
                        },
                    },
                    "artifacts": {"files": "imagedefinitions.json"},
                }
            ),
        )

        # 4. CodePipeline 생성
        pipeline = codepipeline.Pipeline(self, "MyPipeline")

        # 5. Source Stage - ECR에서 소스 가져오기
        source_output = codepipeline.Artifact()
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.EcrSourceAction(
                    action_name="ECR_Source",
                    repository=repository,
                    image_tag="latest",
                    output=source_output,
                )
            ],
        )

        # 6. Build Stage - CodeBuild에서 이미지 빌드
        build_output = codepipeline.Artifact()
        pipeline.add_stage(
            stage_name="Build",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="Build",
                    project=project,
                    input=source_output,
                    outputs=[build_output],
                )
            ],
        )

        # 7. Deploy Stage - 기존 Elastic Beanstalk 환경에 배포
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.ElasticBeanstalkDeployAction(
                    action_name="Deploy",
                    application_name=existing_application_name,
                    environment_name=existing_environment_name,
                    input=build_output,
                )
            ],
        )
