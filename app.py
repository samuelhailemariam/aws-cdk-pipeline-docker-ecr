from aws_cdk import (
    aws_ecr as _ecr,
    aws_codebuild as _codebuild,
    aws_iam as _iam,
    aws_codepipeline as _codepipeline,
    aws_codepipeline_actions as _pipelineactions,
    core,
)

class CicdcdkstackStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR Repo
        ecrRepo = _ecr.Repository(self, 'EcrRepo');
        
        gitHubSource = _codebuild.Source.git_hub(
            owner='samuelhailemariam',
            repo='aws-cdk-cicd-docker-ecr',
            webhook=True,
            webhook_filters= [
                _codebuild.FilterGroup.in_event_of(_codebuild.EventAction.PUSH).and_branch_is('main'),
            ],
        );

        # CODEBUILD - project
        
        project = _codebuild.Project(
            self, 'MyProject', 
            project_name=self.stack_name,
            source= gitHubSource,
            environment= _codebuild.BuildEnvironment(
                build_image= _codebuild.LinuxBuildImage.AMAZON_LINUX_2_2,
                privileged= True
            ),
            environment_variables= {
                'ECR_REPO_URI': {
                  'value': ecrRepo.repository_uri
                }
            },
            build_spec= _codebuild.BuildSpec.from_object({
                'version': "0.2",
                'phases': {
                  'pre_build': {
                    'commands': [
                      'env',
                      'export TAG=$CODEBUILD_RESOLVED_SOURCE_VERSION'
                    ]
                  },
                  'build': {
                    'commands': [
                      'cd docker-app',
                      'docker build -t $ECR_REPO_URI:$TAG .',
                      '$(aws ecr get-login --no-include-email)',
                      'docker push $ECR_REPO_URI:$TAG'
                    ]
                  },
                  'post_build': {
                    'commands': [
                      'echo "In Post-Build Stage"',
                      'cd ..',
                      "printf '[{\"name\":\"flask-app\",\"imageUri\":\"%s\"}]' $ECR_REPO_URI:$TAG > imagedefinitions.json",
                      'pwd',
                      'ls -al',
                      'cat imagedefinitions.json'
                    ]
                  }
                },
                'artifacts': {
                  'files': [
                    'imagedefinitions.json'  
                  ]
                }
            })
        );
        
        ecrRepo.grant_pull_push(project.role)
        
        sourceOutput = _codepipeline.Artifact();
        buildOutput = _codepipeline.Artifact();
        
        sourceAction = _pipelineactions.GitHubSourceAction(
          action_name= 'GitHub_Source',
          owner= 'samuelhailemariam',
          repo= 'aws-cdk-cicd-docker-ecr',
          branch= 'master',
          oauth_token= core.SecretValue.secrets_manager("/my/github/token"),
          output= sourceOutput
        );
        
        buildAction = _pipelineactions.CodeBuildAction(
          action_name= 'CodeBuild',
          project= project,
          input= sourceOutput,
          outputs= [buildOutput]
        );
        
        pipeline = _codepipeline.Pipeline(self, "MyPipeline")
        
        source_stage = pipeline.add_stage(
          stage_name="Source",
          actions=[sourceAction]
        )
        
        build_stage = pipeline.add_stage(
          stage_name="Build",
          actions=[buildAction]
        )
        
        
        
        
        
        
        
        