#!/bin/bash

ACTION_PATH=.github/workflows/unstable-cicd.yaml

path=$1/.github/workflows/unstable-cicd.yaml

if [ -f $path ]; then
  sed -i '' "s/-[ ]*master/ - '**'/g" $path
  cd $path
  git add .
  git commit -m "update action to build on branches"
  git push origin master
fi

exit 0

