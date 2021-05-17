import requests
import boto3
from botocore.exceptions import ClientError

class NullRotator:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass
