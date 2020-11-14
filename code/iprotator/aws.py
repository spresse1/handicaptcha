import requests
import boto3
from botocore.exceptions import ClientError

class AWSRotator:

    def __init__(self):
        self.client = boto3.client('ec2')
        self.ec2 = boto3.resource('ec2')
        self.allocationId = None
        self.associationId = None

        my_id = requests.get("http://169.254.169.254/latest/meta-data/instance-id")
        
        if my_id.status_code != 200:
            raise Exception("Unable to get own AWS ID: %s: %s", my_id.status_code, my_id.text)

        self.id = my_id.text
        print("My Instance ID is ", self.id)
        self.instance = self.ec2.Instance(self.id)

        self.outboundNic = None
        # Look for a second NIC
        for nic in self.instance.network_interfaces_attribute:
            if nic["Description"] == "handicaptcha-outbound":
                self.outboundNic = nic
        assert self.outboundNic != None
        print("Outbound nic: ", self.outboundNic)

    def disassociate(self):
        if self.allocationId is None:
            return
        try:
            response = self.client.disassociate_address(AssociationId=self.associationId)
            print("Address detached: ", response)
            response = self.client.release_address(AllocationId=self.allocationId)
            self.allocationId = None
            print('Address released: ', response)
        except ClientError as e:
            print(e)

    def associate(self):
        try:
            allocation = self.client.allocate_address(Domain='vpc')
            self.allocationId=allocation['AllocationId']
            response = self.client.associate_address(AllocationId=allocation['AllocationId'],
                                            NetworkInterfaceId=self.outboundNic["NetworkInterfaceId"])
            self.associationId=response["AssociationId"]
            print(response)
        except ClientError as e:
            print(e)
            raise e
    
    def __enter__(self):
        self.associate()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disassociate()

# For testing...
if __name__=="__main__":
    a = AWSRotator()
    with a:
        print(requests.get("https://v4.ident.me").text)
    with a:
        print(requests.get("https://v4.ident.me").text)
