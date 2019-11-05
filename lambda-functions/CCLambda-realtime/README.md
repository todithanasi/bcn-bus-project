# Realtime ingestion of TMB data with AWS Lambda functions

## Installation
 - Install serverless
 ```bash
npm install -g serverless
 ```

 - Configure your aws profile, with the default profile or adding a new profile name:

 ```bash
 aws configure --profile newProfileName
 ```

 - Configure the [serverless.yml](./serverless.yml) file with functions, events, plugins and AWS resources required for the Lambda functions.

 - You can run your function locally using your AWS account resources.

 ```bash
 serverless invoke local -f functionName
 ```

 - Deploy your serverless application to the cloud!

 ```bash
serverless Deploy
 ```

 - You can also apply an alias to your code and resources in order to mantain different environments working

 ```bash
serverless deploy --stage aliasName
 ```
