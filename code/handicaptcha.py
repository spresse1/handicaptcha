#! /usr/bin/env python3

import argparse
import iprotator.aws
import iprotator.null
import uuid
import requests
import dns.resolver
import socket
import re
import emailHandler
import subprocess
import tempfile
import os
import json
import sqlite3
import random
import string
from time import sleep
from emailHandler import EmailServer
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

HCAPTCHA_SIGNUP_ADDR="https://dashboard.hcaptcha.com/signup?type=accessibility"
LINK_REGEX = re.compile('http[s]{0,1}://accounts.hcaptcha.com/verify_email/[0-9a-fA-F\-]{0,36}')

GET_COOKIE_BUTTON_XPATH = '//button[@data-cy="setAccessibilityCookie"]'

rotator = None
rotatorClasses = {
    'aws': iprotator.aws.AWSRotator,
    'null': iprotator.null.NullRotator,
}

parser = argparse.ArgumentParser(description="Get hCaptcha bypass cookies")
parser.add_argument("--platform", type=str, choices=rotatorClasses.keys(), required=True)
parser.add_argument("--domain", type=str, required=True)
parser.add_argument("--period", type=int, required=True)
parser.add_argument("--outfile", type=str, required=True, 
    help="File to write successful cookie fetches to. JSON blobs of jars, one per line.")
parser.add_argument("--max-count", type=int)


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
    return "%s@%s" % (''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(random.randint(1,20))), domain)

def trigger_email(addr):
    with tempfile.TemporaryDirectory() as tempdir:
        subprocess.run(
            ["firefox", "-createprofile",
                "handicaptcha %s" % (tempdir),
                "-no-remote"]
        )
        #DISPLAY=:1 firefox $URL --kiosk
        env = os.environ.copy()
        env["DISPLAY"] = ":1"
        ffproc = subprocess.Popen(
            ["firefox", HCAPTCHA_SIGNUP_ADDR, "--kiosk",
                "--profile", tempdir],
            env=env)
        print("firefox open...")
        sleep(15)
        # DISPLAY=:1 xdotool mousemove 630 375
        # Forces focus on the window
        print("moving mouse...")
        subprocess.run(
            ["xdotool", "mousemove", "630", "440"],
            env=env)
        # Tab key to get to the field
        print("pressing tab")
        subprocess.run(
            ["xdotool", "key", "Tab"],
            env=env)
        # DISPLAY=:1 xdotool type "someemail"
        print("typing")
        for char in addr:
            sleep(random.uniform(0,5))
            subprocess.run(
                ["xdotool", "type", char],
                env=env)
        # DISPLAY=:1 xdotool key "Return"
        sleep(random.uniform(0,5))
        print("Pressing return")
        subprocess.run(
            ["xdotool", "key", "Return"],
            env=env)
        
        sleep(15)

        ffproc.terminate()
    return

def get_accessibility_link(body):
    """Gets the link for accessibility signup out of an email body"""
    matches = LINK_REGEX.findall(body)
    if matches is not None:
        return matches[0]
    return None

def _convert_cookie(cookie):
    keyMap = {
        "name": "name",
        "value": "value",
        "host": "domain",
        "path": "path",
        "expiry":"expiry",
        # "sameSite"
        # "secure",
        # "httpOnly"
    }

    ret = {}
    for key in cookie.keys():
        if key in keyMap:
            ret[keyMap[key]] = cookie[key]
    print("Converted cookie: ", ret)
    return ret

# Class from selenium docs: https://selenium-python.readthedocs.io/waits.html
class element_has_css_class(object):
  """An expectation for checking that an element has a particular css class.

  locator - used to find the element
  returns the WebElement once it has the particular css class
  """
  def __init__(self, locator, css_class):
    self.locator = locator
    self.css_class = css_class

  def __call__(self, driver):
    element = driver.find_element(*self.locator)   # Finding the referenced element
    if self.css_class in element.get_attribute("class"):
        return element
    else:
        return False

def test_cookie(cookies):
    driver = webdriver.Firefox()
    try:

        driver.get("https://www.hcaptcha.com/")

        # Add in the cookies extracted previously.
        for cookie in cookies:
            driver.add_cookie(_convert_cookie(cookie))

        # reload with cookies
        driver.get("https://www.hcaptcha.com/")

        driver.save_screenshot("1_screenshot_precaptcha.png")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[@title="widget containing checkbox for hCaptcha security challenge"]'))
            )
        except:
            print("Couldn't find the widget!")
            return
        sleep(3)
        wrapper = driver.find_element(By.XPATH, '//div[@class="form-wrap homepage-version"]')
        coordinates = wrapper.location_once_scrolled_into_view # returns dict of X, Y coordinates
        
        iframe = driver.find_element(By.XPATH, '//iframe[@title="widget containing checkbox for hCaptcha security challenge"]')
        driver.switch_to.frame(iframe)

        sleep(10)

        checkbox = driver.find_elements_by_xpath('//div[@id="checkbox"]')[0]

        r = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[@id="checkbox"]')))
        if not r:
            print("Checkbox is not clickable?!")

        sleep(1)

        checkbox.click()

        # Wait for it to pick up class "checked"
        # (or not, and we return false)
        try:
            res = WebDriverWait(driver, 10).until(element_has_css_class((By.XPATH, '//div[@id="checkbox"]'), "checked"))
        except TimeoutException:
            res = False

        driver.save_screenshot("2_screenshot_postcaptcha.png")

        return res != False
    finally:
        driver.close()

def get_accessibility_cookie(link):
    with tempfile.TemporaryDirectory() as tempdir:
        subprocess.run(
            ["firefox", "-createprofile",
                "handicaptcha %s" % (tempdir),
                "-no-remote"]
        )
        #DISPLAY=:1 firefox $URL --kiosk
        env = os.environ.copy()
        env["DISPLAY"] = ":1"
        ffproc = subprocess.Popen(
            ["firefox", link, "--kiosk",
                "--profile", tempdir],
            env=env)
        sleep(15)
        #DISPLAY=:1 xdotool mousemove 385 510
        subprocess.run(
            ["xdotool", "mousemove", "385", "510"],
            env=env)
        subprocess.run(
            ["xdotool", "click", "1"],
            env=env)
        
        sleep(5)

        ffproc.terminate()
        conn = sqlite3.connect(os.path.join(tempdir, "cookies.sqlite"))
        with conn:
            res = conn.execute("select * from moz_cookies where host=\".hcaptcha.com\"")
        cookies = []
        for row in res:
            cookie = {}
            for col in range(len(res.description)):
                cookie[res.description[col][0]] = row[col]
            cookies.append(cookie)
        print(cookies)
        pass
    return cookies

def write_cookies(file, cookieJar):
    with open(file, "w") as wf:
        wf.write(json.dumps(cookieJar))

def main(args, rotator):
    #if not check_domain_config(args.domain):
    #    print("Unable to verify that %s is set up correctly for mail; check DNS configuration" % args.domain)
    #    return

    es = EmailServer()

    count = 0
    while count <args.max_count:
        count += 1

        # fetch new instance IP
        # TODO, invoke
        with rotator:

            addr = get_email_addr(args.domain)
            #print("Addr is: ", addr)
            
            # Do the sign up
            trigger_email(addr)

            # Wait for email...
            m = es.getEmail()

            # Ge tthe body
            body = emailHandler.decodeEmailBody(m)

            # Pull the link out of the body
            link = get_accessibility_link(body)

            # Open that in a broswer, click the button, get cookie.
            cookieJar = get_accessibility_cookie(link)

            print(cookieJar)
            if test_cookie(cookieJar):
                print("Success!", cookieJar)
                write_cookies(args.outfile, cookieJar)
            else:
                raise Exception("Cookie didn't work!")
        
        sleep(args.period)

if __name__=="__main__":
    args = parser.parse_args()

    rotator = rotatorClasses[args.platform]()

    main(args, rotator)

    #with open("../testemaildata") as f:
    #    text = "\r\n".join(f.readlines())
    #    body = emailHandler.decodeEmailBody(text).decode("UTF-8")
    #    print(get_accessibility_link(body))
    #cookieJar = get_accessibility_cookie("https://accounts.hcaptcha.com/verify_email/")
    #print(cookieJar)
    #res = test_cookie(cookieJar)
    #if res:
    #    print("It worked!")
    #else:
    #    print("No good.")