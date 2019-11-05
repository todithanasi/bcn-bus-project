@ECHO OFF
SET /p AccountNr="Enter AWS Account Number >"

SET /p DeploymentEnvironment="Enter the environment of Deployment (dev, test, prod) >"

SET DeploymentEnvironmentNameExtension=

IF  "%DeploymentEnvironment%" == "dev" ( 
	SET DeploymentEnvironmentNameExtension=-dev
)
IF  "%DeploymentEnvironment%" == "test" ( 
    SET DeploymentEnvironmentNameExtension=-test
)
IF  "%DeploymentEnvironment%" == "prod" ( 
    SET DeploymentEnvironmentNameExtension=-prod
)
REM else echo -n "The entered value for the environment is not correct. Please choose a value between (dev, test, prod)."


REM Default settings for the used variables or names for the created objects are set in the below section.

REM S3 Buckets parameters
SET StackNameS3PublicBucket=CreateS3PublicBucket%DeploymentEnvironmentNameExtension%
SET S3PublicBucket=bcn-bus-cache%DeploymentEnvironmentNameExtension%
SET StackNameS3CodePipeline=CreateS3PipelineBucket%DeploymentEnvironmentNameExtension%
SET S3CodePipeline=bcn-bus-pipeline%DeploymentEnvironmentNameExtension%

REM DynamoDb "UserRequest" Table parameters
SET StackNameDynamoDBUserRequest=CreateDynamoDBUserRequest%DeploymentEnvironmentNameExtension%
SET DynameDBTableUserRequest=UserRequest%DeploymentEnvironmentNameExtension%
SET UserRequestReadCapacity=5
SET UserRequestWriteCapacity=5

REM EBS parameters
SET StackNameEBS=CreateEBS%DeploymentEnvironmentNameExtension%
SET StackNameEBSRole=CreateEBSRole%DeploymentEnvironmentNameExtension%
SET EbsRoleName=EbsRole%DeploymentEnvironmentNameExtension%
REM CI/CD Pipeline parameters
SET StackNamePipeline=CreatePipeline%DeploymentEnvironmentNameExtension%

REM Logs parameters
SET StackNameLogs=CreateLogs%DeploymentEnvironmentNameExtension%

echo "Creating S3PublicBucket"
CALL aws cloudformation deploy --stack-name %StackNameS3PublicBucket% --template-file CloudFormationScripts/S3PublicBucket.yaml --parameter-overrides BucketName=%S3PublicBucket%

echo "Creating S3CodePipeline"
CALL aws cloudformation deploy --stack-name %StackNameS3CodePipeline% --template-file CloudFormationScripts/S3CodePipeline.yaml --parameter-overrides BucketName=%S3CodePipeline%

REM echo -n "Creating CloudFront for the public bucket"

echo "Creating DynamoDB tables"
CALL aws cloudformation deploy --stack-name %StackNameDynamoDBUserRequest% --template-file CloudFormationScripts/CreateDynamoDBTable.yaml --parameter-overrides ReadCapacityUnits=%UserRequestReadCapacity% WriteCapacityUnits=%UserRequestWriteCapacity% TableNameVar=%DynameDBTableUserRequest%

echo "Creating EBS role"
CALL aws cloudformation deploy --stack-name %StackNameEBSRole% --template-file CloudFormationScripts/EBSRole.yaml --capabilities CAPABILITY_NAMED_IAM --parameter-overrides EbsRoleName=%EbsRoleName% 

echo "Creating EBS environment to host the Web application"
CALL aws cloudformation deploy --stack-name %StackNameEBS% --template-file CloudFormationScripts/EBS.yaml --parameter-overrides S3Bucket=%S3CodePipeline% EbsRoleName=%EbsRoleName%

REM AppName='' AwsRegion='' S3TmbData='' S3Url='' S3Cache='' RealTimeTable='' RequestsTable=''

echo "Creating CI/CD Pipeline"
aws cloudformation deploy --stack-name %StackNamePipeline% --template-file CloudFormationScripts/CodePipeline.yaml --capabilities CAPABILITY_NAMED_IAM --parameter-overrides CodePipeLineBucket=%S3CodePipeline% 

REM echo "Creating Alarms for Logs (CloudTrail and CloudWatch)"
REM aws cloudformation deploy --stack-name %StackNameLogs% --template-file CloudFormationScripts/CloudWatchLogs.yaml --parameter-overrides Email=todi.thanasi@gmail.com

