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

CLOUDFLARE_NETMASKS="$(curl -s https://www.cloudflare.com/ips-v4 | tr '\n' ' ') 176.58.123.25/32"

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
# We want to use some VPC features, so make one...
VPCID=$(aws ec2 describe-vpcs --filter Name=tag-key,Values=handicaptcha | \
	jq -r ".Vpcs[0].VpcId" )
if [ "$VPCID" == "null" ]
then
	echo "Creating VPC"
	VPCID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/28 | jq -r ".Vpc.VpcId" )
	aws ec2 create-tags --resources $VPCID --tags Key=handicaptcha,Value=handicaptcha

	# We also have to create a subnet
	SUBNETID=$(aws ec2 create-subnet --cidr-block 10.0.0.0/28 \
		--vpc-id $VPCID | jq -r ".Subnet.SubnetId" )
	aws ec2 create-tags --resources $SUBNETID \
		--tags Key=handicaptcha,Value=handicaptcha
	aws ec2 modify-subnet-attribute --subnet-id $SUBNETID \
		--map-public-ip-on-launch
fi
VPCID=$(aws ec2 describe-vpcs --filter Name=tag-key,Values=handicaptcha | \
	jq -r ".Vpcs[0].VpcId" )
SUBNETID=$(aws ec2 describe-subnets \
	--filters Name=vpc-id,Values=$VPCID Name=tag-key,Values=handicaptcha | \
	jq -r ".Subnets[0].SubnetId" )
echo "VPC ID: $VPCID"
echo "Subnet ID: $SUBNETID"

SGS=$(aws ec2 describe-security-groups \
	--filters Name=vpc-id,Values=$VPCID \
		Name=group-name,Values=handicaptcha \
	| jq -r ".SecurityGroups[0].GroupId" )
if [ "$SGS" == "null" ]
then
	echo "Creating Security Group"
	SG_ID=$(aws ec2 create-security-group \
		--group-name handicaptcha \
		--description "handicaptcha permissions" \
		--vpc-id $VPCID | jq -r ".GroupId" )
	# Then add rules to allow in SSH...
	aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
		--protocol tcp --port 0-65535 --cidr '0.0.0.0/0'
	aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
		--protocol icmp --port -1 --cidr '0.0.0.0/0'

fi
SG_ID=$(aws ec2 describe-security-groups \
	--filters Name=vpc-id,Values=$VPCID \
		Name=group-name,Values=handicaptcha \
	| jq -r ".SecurityGroups[0].GroupId" )
echo "Security group ID: $SG_ID"

GWID=$(aws ec2 describe-internet-gateways \
	--filters Name=attachment.vpc-id,Values=$VPCID \
		Name=tag-key,Values=handicaptcha | \
	jq -r ".InternetGateways[0].InternetGatewayId" )
if [ "$GWID" == "null" ]
then
	echo "Creating Internet Gateway"
	GWID=$(aws ec2 create-internet-gateway | \
		jq -r ".InternetGateway.InternetGatewayId" )
	aws ec2 create-tags --resources $GWID \
		--tags Key=handicaptcha,Value=handicaptcha
	aws ec2 attach-internet-gateway --vpc-id $VPCID \
		--internet-gateway-id $GWID
fi

GWID=$(aws ec2 describe-internet-gateways \
        --filters Name=attachment.vpc-id,Values=$VPCID \
                Name=tag-key,Values=handicaptcha | \
        jq -r ".InternetGateways[0].InternetGatewayId" )
echo "Internet Gateway ID: $GWID"
RTID=$(aws ec2 describe-route-tables --filters Name=vpc-id,Values=$VPCID | \
	jq -r ".RouteTables[0].RouteTableId" )
RTSTATE=$(aws ec2 describe-route-tables --filters Name=vpc-id,Values=$VPCID | \
	jq -r '.RouteTables[0].Routes[] | select(.DestinationCidrBlock == "0.0.0.0/0")' )
if [ -z "$RTSTATE" ]
then
	echo "Adding route to Internet Gateway..."
	aws ec2 create-route --route-table-id $RTID \
		--destination-cidr-block '0.0.0.0/0' \
		--gateway-id $GWID > /dev/null
fi

# Start spinning up the instance...
INSTANCE_ID=$( aws ec2 describe-instances \
	--filter Name=tag-key,Values=handicaptcha \
	--filter Name=instance-state-name,Values=running \
	--filter Name=vpc-id,Values=$VPCID | \
	jq -r ".Reservations[0].Instances[0].InstanceId" )
if [ "$INSTANCE_ID" == "null" ]
then
	echo "Creating instance"
	INSTANCE_CREATE_OUT=$(aws ec2 run-instances --image-id "$AWS_AMI_ID" \
		--count 1 --instance-type "$AWS_INSTANCE_TYPE" \
		--key-name handicaptcha --security-group-ids "$SG_ID" \
		--subnet-id $SUBNETID \
		--enable-api-termination )
	INSTANCE_ID=$(echo "$INSTANCE_CREATE_OUT" | \
		jq -r '.Instances[0].InstanceId')
	sleep 10
	aws ec2 create-tags --resources $INSTANCE_ID --tags Key=vpc,Value=$VPCID
	echo -n "Waiting for instance to launch ($INSTANCE_ID)..."
	aws ec2 wait instance-running --instance-ids $INSTANCE_ID
	status=initializing
	while [ "$( aws ec2 describe-instance-status --instance-ids $INSTACE_ID | jq -r ".InstanceStatuses[0].InstanceStatus.Details[0].Status" )" != "passed" ]
	do
		sleep 10
		echo -n "."
	done
	echo "Done."
fi

INSTANCE_ID=$( aws ec2 describe-instances \
	--filter Name=tag-key,Values=handicaptcha \
	--filter Name=instance-state-name,Values=running \
	--filter Name=vpc-id,Values=$VPCID | \
	jq -r ".Reservations[0].Instances[0].InstanceId" )

echo "AWS Instance ID: $INSTANCE_ID"

#############################################
# Create a second NIC to be our control nic #
#############################################
EGRESS_NWINTF_ID=$(aws ec2 describe-network-interfaces \
	--filters Name=vpc-id,Values=$VPCID Name=description,Values=handicaptcha-outbound | \
	jq -r ".NetworkInterfaces[0].NetworkInterfaceId")
if [ "$EGRESS_NWINTF_ID" == "null" ]
then
	EGRESS_NWINTF_ID=$(aws ec2 create-network-interface --description handicaptcha-outbound \
		--subnet-id $SUBNETID | jq -r ".NetworkInterface.NetworkInterfaceId" )
fi
EGRESS_NWINTF_ID=$(aws ec2 describe-network-interfaces \
	--filters Name=vpc-id,Values=$VPCID Name=description,Values=handicaptcha-outbound | \
	jq -r ".NetworkInterfaces[0].NetworkInterfaceId")

# Check that for assigned IP
EIP=$(aws ec2 describe-addresses --filter Name=tag-key,Values=handicaptcha-outbound | jq -r ".Addresses[0].AllocationId")
if [ "$EIP" == "null" ]
then
	# Allocate and attach an IP address:
	EIP=$(aws ec2 allocate-address --domain vpc | \
		jq -r ".AllocationId")
	aws ec2 create-tags --resources $EIP \
		--tags Key=handicaptcha-outbound,Value=handicaptcha-outbound
fi

IPNICASSOC=$(aws ec2 describe-network-interfaces --network-interface-ids $EGRESS_NWINTF_ID | \
	jq -r ".NetworkInterfaces[0].PrivateIpAddresses[0].Association.PublicIp")	
if [ "$IPNICASSOC" == "null" ]
then
	aws ec2 associate-address --network-interface-id $EGRESS_NWINTF_ID \
		--allocation-id $EIP
fi

# And associate the nic to the instance.
NICINSTASSOC=$(aws ec2 describe-instances --instance-id $INSTANCE_ID | \
	jq -r ".Reservations[0].Instances[0].NetworkInterfaces[] | select(.NetworkInterfaceId == \"$EGRESS_NWINTF_ID\") | .Attachment.AttachmentId")
if [ -z "$NICINSTASSOC" ]
then
	aws ec2 attach-network-interface --instance-id $INSTANCE_ID \
		--network-interface-id $EGRESS_NWINTF_ID --device-index 1 > /dev/null
fi

###################################
# Update and install requirements #
###################################
#aws ec2 describe-instances --instance-ids $INSTANCE_ID
INSTANCE_DNS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID | \
	jq -r ".Reservations[0].Instances[0].PublicIpAddress")

echo "DNS Name: $INSTANCE_DNS"

ssh -o "StrictHostKeyChecking=no" -i ./handicaptcha ec2-user@$INSTANCE_DNS \
	"mkdir -p handicaptcha"

scp -o "StrictHostKeyChecking=no" -i ./handicaptcha \
	-r ${CODEDIR}/code/* ec2-user@$INSTANCE_DNS:handicaptcha
echo "SCP done"

ssh -o "StrictHostKeyChecking=no" -i ./handicaptcha ec2-user@$INSTANCE_DNS \
	"sudo yum update -y &&
	sudo amazon-linux-extras install epel &&
	sudo yum install -y python3-pip chromium chromedriver xorg-x11-xauth &&
	sudo pip3 install awscli selenium &&
	sudo pip3 install -r handicaptcha/requirements.txt"
#	Ksudo amazon-linux-extras install mate-desktop1.x &&
#	sudo bash -c 'echo PREFERRED=/usr/bin/mate-session > /etc/sysconfig/desktop' &&

AWS_ACCESS_KEY=$(aws configure get aws_access_key_id)
AWS_SECRET_KEY=$(aws configure get aws_secret_access_key)
AWS_REGION=$(aws configure get region)

ssh -o "StrictHostKeyChecking=no" -i ./handicaptcha ec2-user@$INSTANCE_DNS \
	"aws configure set region $AWS_REGION
	aws configure set aws_access_key_id $AWS_ACCESS_KEY
	aws configure set aws_secret_access_key $AWS_SECRET_KEY"


ssh -o "StrictHostKeyChecking=no" -i ./handicaptcha ec2-user@$INSTANCE_DNS \
	"for IPRANGE in $CLOUDFLARE_NETMASKS; do sudo ip route add \$IPRANGE dev eth1; done"
echo "Cleanup:
aws ec2 delete-key-pair --key-name handicaptcha
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
# Go into AWS console and delete internet gateway, then the VPC as a whole
"
#aws ec2 detach-internet-gateway --internet-gateway-id $GWID
#[ wait a bit ]
#aws ec2 delete-security-group --group-id $SG_ID
#aws ec2 delete-subnet --subnet-id $SUBNETID
#aws ec2 delete-vpc --vpc-id $VPCID
#"

ssh -o "StrictHostKeyChecking=no" -i ./handicaptcha ec2-user@$INSTANCE_DNS \
	"echo \"My external IP: \$(curl -s https://v4.ident.me)\""

echo "VPC ID: $VPCID"
echo "Subnet ID: $SUBNETID"
echo "Security group ID: $SG_ID"
echo "Internet Gateway ID: $GWID"
echo "AWS Instance ID: $INSTANCE_ID"
echo "DNS Name: $INSTANCE_DNS"