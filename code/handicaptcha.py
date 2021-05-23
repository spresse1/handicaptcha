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
import traceback
import sys
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
        #print("firefox open...")
        sleep(15)
        # DISPLAY=:1 xdotool mousemove 630 375
        # Forces focus on the window
        #print("moving mouse...")
        subprocess.run(
            ["xdotool", "mousemove", "630", "440"],
            env=env)
        # Tab key to get to the field
        #print("pressing tab")
        subprocess.run(
            ["xdotool", "key", "Tab"],
            env=env)
        # DISPLAY=:1 xdotool type "someemail"
        #print("typing")
        for char in addr:
            sleep(random.uniform(0,5))
            subprocess.run(
                ["xdotool", "type", char],
                env=env)
        # DISPLAY=:1 xdotool key "Return"
        sleep(random.uniform(0,5))
        #print("Pressing return")
        subprocess.run(
            ["xdotool", "key", "Return"],
            env=env)
        #print("Triggered email to {}" % (addr))
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
    #print("Converted cookie: ", ret)
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

def stuff_cookies(cookies, profileDir):
    conn = sqlite3.connect(os.path.join(profileDir, "cookies.sqlite"))
    with conn:
        for cookie in cookies:
            #print(cookie)
            #conn.execute("select * from moz_cookies where host=\".hcaptcha.com\"")
            conn.execute("insert into moz_cookies"
                "(name, value, host, path, expiry, lastAccessed, "
                "creationTime, isSecure, isHttpOnly) "
                "VALUES "
                "(:name, :value, :host, :path, :expiry, :lastAccessed, "
                ":creationTime, :isSecure, :isHttpOnly)", cookie)
        conn.commit()

def test_cookie(cookies):
    with tempfile.TemporaryDirectory() as tempdir:
        subprocess.run(
            ["firefox", "-createprofile",
                "handicaptcha %s" % (tempdir),
                "-no-remote"]
        )

        #DISPLAY=:1 firefox $URL --kiosk
        env = os.environ.copy()
        env["DISPLAY"] = ":1"

        # This forces firefox to create  the `moz_cookies` tables (admittedly)
        # filling it with a google cookie, but whatever.
        p = subprocess.Popen(
            ["firefox", "https://hcaptcha.com", "--kiosk",
                "--profile", tempdir],
            env=env)
        sleep(2)
        p.kill()

        # Put the hCaptcha cookies back into the firefox profile
        stuff_cookies(cookies, tempdir)
        #print(tempdir)
        
        ffproc = subprocess.Popen(
            ["firefox", "https://hcaptcha.com", "--kiosk",
                "--profile", tempdir],
            env=env)
        sleep(15)
        #DISPLAY=:1 xdotool mousemove 385 510
        subprocess.run(
            ["xdotool", "mousemove", "385", "540"],
            env=env)
        sleep(1)

        # This complicated bit is required to get to the captcha checkbox to
        # activate it. For whatever reason, the checkbox is not present in the
        # tab order until after you go pas tthe iframe surrounding it! This is
        # stupid And very much imprefect accessibility. As an accessibility
        # user, I would expect that when the page tells me I'm on a captcha
        # I can either activate it (press enter, doesn't work here) or that
        # one fo the next elements would let me work with it. This "go forward
        # then go backwards" is stupid.
        # Proceedure:
        # * Press tab 15 times
        # * Press shift+tab
        # * Press enter to activate pseudo-checkbox
        # TLDR: hCaptcha accessibility behaves in an unexpected way, this 
        # works around that
        #print("pressing tab")
        for x in range(15):
            subprocess.run(
                ["xdotool", "key", "Tab"],
                env=env)
            sleep(random.uniform(0,2))   
     
        sleep(random.uniform(0,2))
        subprocess.run(
            ["xdotool", "key", "shift+Tab"],
            env=env)

        sleep(random.uniform(0,2))
        subprocess.run(
            ["xdotool", "key", "Tab"],
            env=env)
        sleep(random.uniform(0,2))
        print("Pressing enter to activate captcha")
        subprocess.run(
            ["xdotool", "key", "Return"],
            env=env)
     
        # Now that we've activted the button, grab a screenshot to verify it turned green.
        sleep(5)
        print("Grabbing screencap")
        subprocess.run(
            ["import", "-window", "root", os.path.join(tempdir, "screenshot.png")],
            env=env
        )

        ffproc.kill()

        subprocess.run(
            ["convert", os.path.join(tempdir, "screenshot.png"), "-crop", "34x34+228+855", os.path.join(tempdir, "screenshot_cropped.png")],
            env=env
        )
        #print(os.path.join(os.path.dirname(__file__), "reference_result.png"))
        p = subprocess.run(
            ["compare", "-metric", "AE", 
                os.path.join(os.path.dirname(__file__), "reference_result.png"), 
                os.path.join(tempdir, "screenshot_cropped.png"),
                os.path.join(tempdir, "screenshot_diff.png")
            ],
            env=env
        )
        return p.returncode == 0

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
            ["xdotool", "mousemove", "385", "540"],
            env=env)
        # import pdb;pdb.set_trace()
        # subprocess.run(
        #     ["xdotool", "click", "1"],
        #     env=env)

        # The "Set Cookie" button is the 4th tabable element
        #print("pressing tab")
        for x in range(4):
            subprocess.run(
                ["xdotool", "key", "Tab"],
                env=env)
            sleep(random.uniform(0,2))
        
        #import pdb; pdb.set_trace()
        # DISPLAY=:1 xdotool key "Return"
        sleep(random.uniform(0,5))
        #print("Pressing return")
        subprocess.run(
            ["xdotool", "key", "Return"],
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
        #print(cookies)
        pass
    return cookies

def write_cookies(file, cookieJar):
    with open(file, "w") as wf:
        wf.write(json.dumps(cookieJar))

def main(args, rotator):
    if not check_domain_config(args.domain):
        print("Unable to verify that %s is set up correctly for mail; check DNS configuration" % args.domain)
        return

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
            print(m)
            # Get the body
            #body = emailHandler.decodeEmailBody(m)
            #print(body)
            # Pull the link out of the body
            link = get_accessibility_link(m)
            #link = "https://accounts.hcaptcha.com/verify_email/4205d8c2-edff-4cd6-9850-74e9ef16a152"
            print("Accessibility link: " + link)
            # Open that in a broswer, click the button, get cookie.
            cookieJar = get_accessibility_cookie(link)
            # cookieJar = json.loads("""
            # [{"id": 6, "originAttributes": "", "name": "hc_accessibility", "value": "IfJfJEmJaHm5Ystlnx8Bz6k3iGtCS5hSFOHo9a92BESII16p1LRO0AgLYODs8WTKUu90YRwSOY9a1VeCD/wAT2h6WABathAcpGLWZ0M2nCI5IwGAjDjLO4yBqwz2k4Jah2RYWGukR4v7Iw0OeyLVcFLoZd7JsuzZ72xbq8IT5alA2fMLxMUSywE7q2yC6mRrU1vTLswUMVNCiJ+wG9j5umRons9BMy+U5FMb1UMyKP+BJFus3kJ731dDw7HQk35SlK/vCBsWx9HqlmENtqmLK+vefQJndUtWEJwiSHr17vvwYoRxIR5b6j7zOxZCk0uTaLGqyRR01U+HAeQBUvX81/uRpH4w/sE1FOkAz7XrtWh5lZqkG9i9A6w3FlFk76qNOoc9IdhH7Wc9YEhZV8eXEoVCk+PZe1BHJhZyVw8MTuMTPHo1OeSglkGDDNBhGv7OlQ1PmJ0/o0eFI3aByRD+HQXZ6wBlVHo4", "host": ".hcaptcha.com", "path": "/", "expiry": 1621742599, "lastAccessed": 1621699399315867, "creationTime": 1621699399315867, "isSecure": 1, "isHttpOnly": 0, "inBrowserElement": 0, "sameSite": 0, "rawSameSite": 0, "schemeMap": 2}, {"id": 8, "originAttributes": "", "name": "session", "value": "7f4c66b1-f291-40d2-b320-31d77e14fd48", "host": ".hcaptcha.com", "path": "/", "expiry": 1624377799, "lastAccessed": 1621699399317173, "creationTime": 1621699381972405, "isSecure": 1, "isHttpOnly": 1, "inBrowserElement": 0, "sameSite": 0, "rawSameSite": 0, "schemeMap": 2}]
            # """)
            print("Cookie jar:")
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