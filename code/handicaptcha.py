#! /usr/bin/env python3

import argparse
import iprotator.aws
import uuid
import requests
import dns.resolver
import socket

HCAPTCHA_SIGNUP_ADDR="https://dashboard.hcaptcha.com/signup?type=accessibility"

parser = argparse.ArgumentParser(description="Get hCaptcha bypass cookies")
parser.add_argument("--platform", type=str, choices=['aws'], required=True)
parser.add_argument("--domain", type=str, required=True)
parser.add_argument("--period", type=int, required=True)

rotator = None
rotatorClasses = {
    'aws': iprotator.aws.AWSRotator
}

def check_domain_config(domain):
    my_ip = requests.get("http://169.254.169.254/latest/meta-data/public-ipv4").text
    try:
        dns_r = dns.resolver.resolve(domain, "MX").rrset.items.keys()
    except dns.resolver.NoAnswer as e:
        print("No DNS record found!: ", e)
        return False

    count=0
    mx_dns=None
    for rr in dns_r:
        mx_dns=rr.exchange.to_unicode()
        count += 1
    if count != 1:
        print("There should be exactly one MX record for %s, not %d" % (domain, count))
        return False
    
    mx_ip = socket.gethostbyname(mx_dns)

    if mx_ip != my_ip:
        print("MX record found for %s, but doesn't point to us. It points to %s, should be %s" % (
            domain, mx_ip, my_ip
        ))
        return False
    
    return True

def get_email_addr(domain):
    return "%s@%s" % (uuid.uuid4(), domain)

def trigger_email(addr):
    raise NotImplementedError()

def main(args):
    if not check_domain_config(args.domain):
        print("Unable to verify that %s is set up correctly for mail; check DNS configuration" % args.domain)
        return

    count = 0
    while count <1:
        addr = get_email_addr(args.domain)
        print("Addr is: ", addr)
        count += 1

if __name__=="__main__":
    args = parser.parse_args()

    rotator = rotatorClasses[args.platform]

    main(args)