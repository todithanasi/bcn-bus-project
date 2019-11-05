# TMB Information of Buses and Lines (Cloud Computing Project) 

This repository contains the web application to search for different stops and lines for buses in Barcelona. It also includes a dashboard where you can see the stops and lines based on the most frequent requests visualize on charts and map.

The application contains 2 services:

## Citizen Service:

This service is for citizen of barcelona to search for stops and lines on the website. They can search for real time bus timings per stop, they have also an option to view all stops per line.

## Visual Dashboard for Analysis:

The Dashboard page contains the chart showing the number of times a stop was searched for the most frequently search stops and another chart shows the same for lines. Dashboard also includes a heatmap showing the frequency of searched stops as a heatmap. There is also a filter to filter the dashboard by user specified dates.

### Technologies used: 

This application is Python Django Web Application connected with S3 and DynamoDb for data. It also uses several javascript libraries, including leaflet.js, Chart.js,heatmap-leaflet.js and Bootstrap for design responsiveness. 

Data is populated in the Dynamodb and S3 bucket by the help of a lambda function getting the information from TMB APIs, for more details on lambda function used, following are links to the lambda function repositories: 

- [Lambda function for realtime data insertion with bus arrival times in DynamoDB](https://github.com/todithanasi/bcn-bus-project/lambda-functions/CCLambda-realtime/)

- [Lambda function for weekly data updation of stops and lines with names and locations in S3 bucket](https://github.com/todithanasi/bcn-bus-project/lambda-functions/CCLambda-weekly)


## Report

The final report of this project is available inside the report folder of this repository.
[Report](https://github.com/todithanasi/bcn-bus-project/report/Final_Report.pdf)
