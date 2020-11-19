#! /usr/bin/env python3

import argparse
import iprotator.aws
import uuid
import requests
import dns.resolver
import socket
import re
import emailHandler
from time import sleep
from emailHandler import EmailServer
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

HCAPTCHA_SIGNUP_ADDR="https://dashboard.hcaptcha.com/signup?type=accessibility"
LINK_REGEX = re.compile('http[s]{0,1}://accounts.hcaptcha.com/verify_email/[0-9a-fA-F\-]{0,36}')

GET_COOKIE_BUTTON_XPATH = '//button[@data-cy="setAccessibilityCookie"]'

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

def get_accessibility_link(body):
    """Gets the link for accessibility signup out of an email body"""
    matches = LINK_REGEX.findall(body)
    if matches is not None:
        return matches[0]
    return None

def get_accessibility_cookie(link):
    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(link)

        # Wait until we can see the button
        WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, GET_COOKIE_BUTTON_XPATH))
            )

        print(driver.get_cookies())

        print(dir(driver))
        # driver.add_cookie({'domain': '.hcaptcha.com', 'expiry': 1608247607, 'httpOnly': True, 'name': 'session', 'path': '/', 'secure': True, 'value': 'fad254ea-63e1-43df-bfbe-ec64b6a7b6f6'})
        # driver.add_cookie({'domain': '.hcaptcha.com', 'expiry': 1608161205, 'httpOnly': True, 'name': '__cfduid', 'path': '/', 'sameSite': 'Lax', 'secure': True, 'value': 'dbacb5aad1d90367d112cd52d3711756f1605569205'})
        # driver.add_cookie({'domain': '.hcaptcha.com', 
        #     'expiry': 1608161205, 
        #     'httpOnly': True, 
        #     'name': 'hc_accessibility', 
        #     'path': '/',
        #     'secure': True, 
        #     'value': '4F2EVjOcgiQI3dG+SFG4/y2yYU6g0WS8XKX+4v9wHaPVb3VEDobj6vmyhCY+VCPEgAPd4aYNW8Vwz3cdwhfKmpkl5cLvqgy6gl03LJ+yYtunYAe7wxt1RBs+TYRGOJxeBIPg0/YjO/3rN0dJVMn5QvmDhaxpyNk1c8u2P4o0s8Zo4xpLhokhfaLKYwHe06FAlfN+B9qtg0TpZeJvfsdgpDoQ2AflwUTQuoAS1HeT5zrL6VNQoBEgoQhuhpZCQxvrtI2Sw4FT0hEwnloO8eYWhIlLrKX1JODpc6qkbUGglkDonnvQa48VKrST7Fkz9tzWVNnkQ2mfIx3/ye1HYPjO1WHFTlC9t0VSVpHyrVJzRd27YuNjjRgsi4LYKko2Tdcs7K5pvUG8HvRzfjrQ5mcIMYTwwy6dyPUU1PFWknZBG18=yhGHvNLBwpTvoo4o'})

        driver.save_screenshot("screenshot_1prebutton.png")
        
        button = driver.find_element(By.XPATH, GET_COOKIE_BUTTON_XPATH)
        #button.click()

        import pdb; pdb.set_trace()
        sleep(5)
        driver.save_screenshot("screenshot_2postbutton.png")

        cookieJar = driver.get_cookies()
        print(cookieJar)

        driver.get("https://www.hcaptcha.com/")

        driver.save_screenshot("screenshot_3precaptcha.png")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[@title="widget containing checkbox for hCaptcha security challenge"]'))
            )
        except:
            print("Couldn't find the widget!")
            return
        iframe = driver.find_element(By.XPATH, '//iframe[@title="widget containing checkbox for hCaptcha security challenge"]')
        driver.switch_to.frame(iframe)

        sleep(1)

        checkbox = driver.find_elements_by_xpath('//div[@id="checkbox"]')[0]

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[@id="checkbox"]')))

        checkbox.click()

        sleep(10)

        driver.save_screenshot("screenshot_4postcaptcha.png")

        print(cookieJar)
    finally:
        driver.close()
    return cookieJar

def main(args):
    if not check_domain_config(args.domain):
        print("Unable to verify that %s is set up correctly for mail; check DNS configuration" % args.domain)
        return

    es = EmailServer()

    count = 0
    while count <0:
        addr = get_email_addr(args.domain)
        print("Addr is: ", addr)
        count += 1

        # Do the sign up

        # Wait for email...
        m = es.getEmail()

        # Ge tthe body
        body = emailHandler.decodeEmailBody(m)

        # Pull the link out of the body
        link = get_accessibility_link(body)

        # Open that in a broswer, click the button, get cookie.


if __name__=="__main__":
    #args = parser.parse_args()

    #rotator = rotatorClasses[args.platform]

    #main(args)

    #with open("../testemaildata") as f:
    #    text = "\r\n".join(f.readlines())
    #    body = emailHandler.decodeEmailBody(text).decode("UTF-8")
    #    print(get_accessibility_link(body))
    print(get_accessibility_cookie("https://accounts.hcaptcha.com/verify_email/21933c8a-2034-4bff-9816-5aed2558f698"))