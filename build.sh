#!/bin/bash

set -eu

APPLICATION_VERSION=$1
IMAGE="ecole96/projects:remote-wakeonlan-$APPLICATION_VERSION"

# -p flag indicates whether to publish the image
# if so, we build a multi-platform image without cache and push it to the Docker registry
# otherwise, builds a local image without pushing
PUBLISH=0
while getopts p flag
do
    case "${flag}" in
        p) PUBLISH=1 ;;
    esac
done

if [ $PUBLISH -eq 1 ]
    then
        echo "Building and publishing image: $IMAGE"
        docker buildx build --no-cache  --platform linux/amd64,linux/arm64 -t "$IMAGE" .
        docker push "$IMAGE"
    else
        echo "Building local image: $IMAGE"
        docker build -t "$IMAGE" .
fi  
