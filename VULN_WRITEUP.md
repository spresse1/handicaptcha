This research was, to the best of my understanding, conducted within the bounds of the [hCaptcha bug bounty program](https://github.com/hCaptcha/bounties). Specifically it interacted only with the following resources:

* The hCaptcha dashboard, in the form of the [accessibility sign-up page](https://dashboard.hcaptcha.com/signup?type=accessibility).
* The hCaptcha dashboard, signed in as an Accessibility user for an account I registered and control.
* The [hCaptcha homepage](https://www.hcaptcha.com/), specifically the captcha test available there.

This exploit employs no phishing or social engineering and none was attempted.

# TL;DR

In order to provide a method for blind, visually-impaired users, motor-impaired or other disabled to pass hCaptcha challenges, hCaptcha allows a user to sign up with an email account and receive an "accessibility cookie". This cookie allows accessibility users to pass hCaptcha challenges without having to solve a puzzle.

The hCaptcha accessibility workflow can be automated by an attacker. The accessibility signup process requires only being able to navigate to a URL sent to a user-specified email address. By using an attacker-controlled domain, an attacker can sign up for many accessibility accounts without human interaction, therefore collecting many accessibility tokens and being able to bypass many challenges.

# Exploit

## Attack Scenario

An attacker wishes to bypass the hCaptcha challenge without human intervention. The attacker is able to navigate to the page where the hCaptcha prevents automation, but is stopped there by hCaptcha.

## Instructions for Reproduction

I have prepared a video of this attack being carried out. Due to its size, I cannot email it. However, I will gladly provide it via the secure transfer mechanism of your choice. (For example, an encrypted tarball on a webserver, with the password sent via email)

Additionally, I have written a fully automated proof-of-concept exploit which I will also gladly share via a secure channel.

### Required Materials

* An attacker controlled domain (or domains)
* An account with a hosting provider that allows API-based start and stop of virtual machines and assigns public IP addresses to the booted machines. This proof-of-concept only supports AWS, but other providers could easily be used.

### How this works

The PoC code performs several steps to automatically bypass hCaptcha challenges:

1. Sets up a VM which receives a public IP address
2. Sets up the DNS MX record for the attacker controlled-domain to point to the VM. This step is manual in the PoC.
3. If using AWS, sets up an `Internet Gateway`, which has a public IP and routes all traffic relevant to hCaptcha through this gateway. The internet gateway receives its own public IP address that is distinct from that of the VM.
4. Opens the [accessibility signup page](https://dashboard.hcaptcha.com/signup?type=accessibility) using a clean Firefox profile, started in an X11 session. This browser is unmodified, has no extensions, and is not under programmatic control (eg: selenium). It should therefore be indistinguishable from an actual user browser. All key presses from this point forward are done using `xdotool` to emulate actual keyboard input.
5. In the browser, `xdotool` injects tab keypresses until in the email form field. Then, it enters an email address at the attacker-controlled domain. It then tabs to and presses the submit button.
6. The VM is also running a very simple SMTP server (built on python's `smtpd` module). When this receives an email, it searches it for a URL that matches the pattern of an accessibility link.
7. Then the accessibility link is opened in Firefox (with a new clean profile) and the "Get Cookie" button is tabbed to and activated
8. The accessibility cookie is exported from Firefox's cookie jar
9. A new Firefox profile is created, and the accessibility cookie is stuffed into the cookie jar.
10. Using the profile from step 9, the hCaptcha instance on the hCaptcha homepage is activated, showing that the captcha is successfully bypassed. This is validated via a screen capture.
11. If another accessibility cookie is desired, the IP address of the Internet Gateway is changed and the process repeats from step 4.

### Replication instructions

I tested this using an up-to-date Ubuntu 20.04 system. Prior to these directions, I installed the AWS CLI and configured it to work with my AWS account.

These directions also assume you have unpacked the PoC tarball and changed into the `handicaptcha` directory.

1. Run the environment setup. This step handles the creation of the VM used throughout the rest of the steps.
   ```shell
   $ ./setup_env.sh
   ```
2. At the end of the output from the previous step, the public IP address of the VM is printed. Note this as VMIP
   ```shell
   $ export VMIP=YOUR_VM_IP_HERE
   ```
3. Configure DNS for your domain. You must configure it so that the root MX record points to your VM. So if the domain is `hcaptcha.example` and the IP is `1.2.3.4`, the result of `dig hcaptcha.example in MX` should look like this:
   ```shell
   $ dig +short hcaptcha.example in MX
   10 1.2.3.4
   ```
   Alternatively, you may set it up with an A-record for `mail.hcaptcha.example`, which would result in this series of lookups:
   ```shell
   $ dig +short hcaptcha.example in MX
   10 mail.hcaptcha.cexample.
   $ dig +short mail.hcaptcha.example
   1.2.3.4
   ```
3. SSH to the VM:
   ```shell
   $ ssh -XC -i hcaptcha ubuntu@${VMIP}
   ```
4. Optionally, install `xtigervncviwer`. You will need this to watch the exploit run. Otherwise, the X server is headless and you will only see console output.
   ```shell
   VM$ sudo apt install tigervnc-viewer
   ```
5. If you want to watch the exploit run, start an `xtigervncviewer` session:
   ```shell
   VM$ xtigervncviewer -SecurityTypes VncAuth -passwd /home/ubuntu/.vnc/passwd :1 &
   ```
   This will take a minute to start. When you see a black window with an instance of `xeyes` running in the corner, it has successfully started.
6. Change into the `handicaptcha` directory
   ```shell
   VM$ cd handicaptcha
   ```
7. Run the exploit code. The example invocation shown here uses the `hcaptcha.example` domain, is run on AWS, and gets at most 1 accessibility cookie. For more information on options, run `./handicaptcha.py --help`.
   ```shell
   VM$ ./handicaptcha.py --platform aws --max-count 1 --outfile ~/handicaptcha.out --domain hcaptcha.example --period 1
   ```
8. Sit back and watch. If you started `xtigervncviewer`, you will be able to observe the PoC go through the process of registering an account, getting the cookie and using it, all without human intervention.

### Troubleshooting

Honestly, this is a relatively fragile PoC. While I've done my best to make sure that it all works correctly, it is a prototype and very possible some small and subtle change may break it. I'm happy to give you a hand with any part that breaks.

One of the more likely places for this to go wrong is the DNS email setup. For this reason, the code does check the setup before running. Most everything else is automated setup from consistent base resources.

But again, do feel free to reach out as needed for assistance with replication.

## Security Impact

The fundamental point of a captcha is to prevent automated actions. This exploit allows automated bypass of captchas, therefore rendering the captcha useless. It therefore is of the most critical severity. Although this PoC is small and the instructions only generate a single account via automation, this process can be repeated up to the rate limits for registrations per IP address and registrations per domain. An attacker automating this process could quickly create many accounts. A malicous attacker might use a botnet to make such an attack come from various IP addresses that cannot be correlated or distinguished from normal human traffic while having a plthora of IP addresses available.

Further, because accessibility accounts do not expire, each account can be re-used up to the rate limit on hCaptcha challenge bypasses daily. Hundreds of accounts would become thousands of bypasses per day.

In conclusion, because each accessibility account can be reused over time to bypass many captchas, the cost-per-captcha-bypass of this exploit (if deployed at scale) amorizes to nearly zero.

There is a high likelihood of this being uncovered and exploited. hCaptcha has -- to their great credit -- made their accessibility option very obvious to users, even non-technical ones. The accessibility signup process is also well-described in documentation. Therefore an attacker need only be doing basic research and considering the system in order to uncover it. (Personally, I came across the exploit by accident while doing accessibility-related research).

However, this is somewhat mitigated by the technical complexity of such automation. Any attacker must at a minimum be familiar with writing code to automatically interact with a cloud provider/hosting API. They must also be familiar with DNS, email, and browser automation.

The following is my evaluation of this under the [OWASP Risk Rating Model](https://owasp.org/www-community/OWASP_Risk_Rating_Methodology).

### Likelihood

#### Threat agent factors

* Skill level - 7
* Motive - 9 (hCaptcha protects cloudflare, which protects 12-15% of the internet. Being able to bypass this captcha gets attackers the ability to automate a lot of major sites they previously could not. That has a lot of potential for sale on the grey or black markets)
* Opportunity - 7 (Requires spending money in AWS or other compute provider)
* Size - 9 (Everything used in this attack is public to unauthenticated users)

Average: 8

#### Vulnerability Factors

* Ease of discovery - 7 (Merely requires thought and examination of documentation)
* Ease of exploit - 4 (Would have to write their own tools and interact with several APIs. Not difficult, but not trivial)
* Awareness - Unknown. No good way for anyone outside hCaptcha/IMI to know if this is being exploited.
* Intrusion Detection - 8 (I was not subtle in some of my testing for this. None of my resources earned permanent bans, so I'm assuming there is no manual review)

Average: 6.333

### Impact

#### Technical impact

* Loss of confidentiality - 0 (No impact on confidential data. As the hCaptcha challenge has no confidential data, I would argue this point is likely invalid, but am including it anyway)
* Loss of integrity - 9 (Users count on hCaptcha to keep their systems bot-free and prevent automated interaction of many kinds. This exploit invalidates that protection, meaning they no longer will know that activity is human)
* Loss of availability - 9 (No services go down, but the gurantees that hCaptcha provides with respect to stopping automated interaction are no longer valid)
* Loss of accountability - 8 (It would likely take law enforcement cooperation to unmask an attacker using this exploit who performed minimal work to remain anonymous)

Average: 6.5

#### Business impact

I lack too much information about hCaptcha's business to make good estimates here.

### Overall averages

* Likelihood: 7.3 (High)
* Impact (technical only): 6.3 (High)

Under the OWASP framework, this is therefore a critical vulnerability.

## Conclusion

This exploit is a fully-automated circumvention of the hCaptcha challenge. It automates the accessibility workflow to create accounts and demonstrates how an attacker could easily generate as many accessibility accounts as they wish.  The attacker can then use those to bypass as many hCaptcha challenges as they wish.  Finally, this shows how it would cost an attacker almost nothing per challenge bypass.

## Potential Future Improvements

* Use browser automation (eg: Selenium) via ULA paper mechanism to avoid detection
* Automate DNS setup
* Automate domain registration
* Use IPv6 addresses (bigger address space, potentially under attacker's own control entirely and could be done without involving a public cloud)
* For a real attacker: use a botnet or other malware to get more IP addresses