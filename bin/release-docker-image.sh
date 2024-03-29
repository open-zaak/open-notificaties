#!/bin/bash

set -e # exit on error
set -x # echo commands

CONTAINER_REPO=openzaak/open-notificaties

git_tag=$(git tag --points-at HEAD) &>/dev/null
git_branch=$(git rev-parse --abbrev-ref HEAD)
git_commit=$(git rev-parse HEAD)


build_image() {
    tag=$1
    docker build \
        --build-arg COMMIT_HASH=${git_commit} \
        --target production \
        -t ${CONTAINER_REPO}:$tag \
        -f Dockerfile .
}

get_release_tag() {
    if [[ -n "$git_tag" ]]; then
        release_tag=$git_tag
    elif [[ $git_branch == "develop" ]]; then
        release_tag=develop
    else
        release_tag=${RELEASE_TAG:-latest}
    fi
    echo $release_tag
}

push_image() {
    # JOB_NAME is set in .travis.yml
    # only push the image if running in CI
    release_tag=$1
    if [[ -n "$JOB_NAME" ]]; then
        docker push ${CONTAINER_REPO}:$release_tag

        # if this is a tag, and this is main -> push latest as well
        if [[ -n "$git_tag" && $git_branch -eq "main" ]]; then
            build_image latest
            docker push ${CONTAINER_REPO}:latest
        fi
    else
        echo "Not pushing image, set the JOB_NAME envvar to push after building"
    fi
}


if [[ -n "$git_tag" ]]; then
    echo "Building image for git tag $git_tag"
fi

release_tag=$(get_release_tag)
build_image $release_tag
push_image $release_tag
