#! /bin/bash

set -e

#############################
# Check binary requirements #
#############################
if [ -z "$(which jq)" ]
then
	echo "jq is required but not installed!"
	exit 1
fi

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

############################
# Do deletes, if requested #
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

# Add SSH key
IKP=$(aws ec2 describe-key-pairs --key-names handicaptcha 2>/dev/null || : )
if [ -z "$IKP" ]
then
	echo "Uploading key pair..."
	aws ec2 import-key-pair --key-name handicaptcha \
		--public-key-material "$(cat ./handicaptcha.pub)"
fi

# exit 0

SGS=$(aws ec2 describe-security-groups --group-names handicaptcha \
	2>/dev/null || : )
if [ -z "$SGS" ]
then
	echo "Creating Security Group"
	SG_ID=$(aws ec2 create-security-group \
		--group-name handicaptcha \
		--description "handicaptcha permissions" | jq -r ".GroupId" )
	# Then add rules to allow in SSH...
	aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
		--protocol tcp --port 22 --cidr '0.0.0.0/0'

fi
SG_ID=$(aws ec2 describe-security-groups --group-names handicaptcha \
	| jq -r ".SecurityGroups[0].GroupId" )
echo "Security group ID: $SG_ID"

# Start spinning up the instance...
INSTANCE_ID=$( aws ec2 describe-instances \
	--filter Name=tag-key,Values=handicaptcha \
	--filter Name=instance-state-name,Values=running | \
	jq -r ".Reservations[0].Instances[0].InstanceId" )

if [ "$INSTANCE_ID" == "null" ]
then
	INSTANCE_CREATE_OUT=$(aws ec2 run-instances --image-id "$AWS_AMI_ID" \
		--count 1 --instance-type "$AWS_INSTANCE_TYPE" \
		--key-name handicaptcha --security-group-ids "$SG_ID" \
		--enable-api-termination )
	INSTANCE_ID=$(echo $INSTANCE_CREATE_OUT | \
		jq -r '.Instances[0].InstanceId')
	echo -n "Waiting for instance to launch ($INSTANCE_ID)..."
	aws ec2 wait instance-running --instance-ids $INSTANCE_ID
	status=initializing
	while [ "$( aws ec2 describe-instance-status --instance-ids $INSTACE_ID | jq -r ".InstanceStatuses[0].InstanceStatus.Details[0].Status" )" != "passed" ]
	do
		aws ec2 describe-instance-status --instance-ids $INSTACE_ID | jq -r ".InstanceStatuses[0].InstanceStatus.Details[0].Status"
		sleep 10
		echo -n "."
	done
	echo "Done."
fi

INSTANCE_ID=$( aws ec2 describe-instances \
	--filter Name=tag-key,Values=handicaptcha \
	--filter Name=instance-state-name,Values=running | \
	jq -r ".Reservations[0].Instances[0].InstanceId" )

echo "AWS Instance ID: $INSTANCE_ID"

###################################
# Update and install requirements #
###################################
INSTANCE_DNS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID | \
	jq -r ".Reservations[0].Instances[0].PublicDnsName")

echo "DNS Name: $INSTANCE_DNS"
scp -o "StrictHostKeyChecking=no" -i ./handicaptcha \
	-r ${CODEDIR}/code ec2-user@$INSTANCE_DNS:handicaptcha
echo "SCP done"

ssh -o "StrictHostKeyChecking=no" -i ./handicaptcha ec2-user@$INSTANCE_DNS \
	"sudo yum update -y; sudo yum install -y python3-pip; cd handicaptcha"

echo "Cleanup:
aws ec2 delete-key-pair --key-name handicaptcha
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
[ wait a bit ]
aws ec2 delete-security-group --group-name handicaptcha
"
