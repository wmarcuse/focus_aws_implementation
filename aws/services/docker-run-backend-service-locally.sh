winpty docker run -it --rm \
-p 8989:8989 \
-e AWS_ACCESS_KEY=$AWS_ACCESS_KEY \
-e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
-e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION \
-e AWS_APP_CONTEXT=$AWS_APP_CONTEXT \
575950781373.dkr.ecr.eu-central-1.amazonaws.com/focus/backend:$1
