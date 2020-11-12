#! /bin/bash

set -e

###################
# Basic variables #
###################
AWS_PROFILE=handicaptcha
AWS_INSTANCE_TYPE="t1.micro"
AWS_AMI_ID="ami-0947d2ba12ee1ff75" # Basic Amazon Linux

RUNDIR=. #$(mktemp -d ./tmp_XXXXXXXX)
SSH_KEY_LOCATION=handicaptcha
CODEDIR=$(pwd)

##########
# Basics #
##########
# cd to runtime dir
cd "$RUNDIR"

# Set up basic enviornment
python3 -m venv venv

# move into it
. venv/bin/activate

# install our basics
pip3 install -r "${CODEDIR}/requirements.txt"

#############
# AWS Setup #
#############
# Configure the AWS CLI, including profile, if not already set up
aws configure list --profile handicaptcha >/dev/null 2>&1 || \
	aws configure --profile handicaptcha

export AWS_PROFILE=$AWS_PROFILE

if [ ! -e ./handicaptcha.pub ]
then
	# SSH keys... (No passphrase)
	ssh-keygen -f ./handicaptcha -N ""
fi

# Remove any old SSH key
aws ec2 delete-key-pair --key-name handicaptcha

# Add SSH key
aws ec2 import-key-pair --key-name handicaptcha \
	--public-key-material "$(cat ./handicaptcha.pub)"

exit 0

# Start spinning up the instance...
aws ec2 run-instances --image-id "$AWS_AMI_ID" --count 1 \
  --instance-type "$AWS_INSTANCE_TYPE" --key-name
