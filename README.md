# Automated hCaptcha Bypass

Code and configuration on evading hCaptcha in an automated manner. This code automates the accessibility workflow to get a bypass cookie, pull it out of the cookie jar, put it in a fresh jar, and bypass the hCaptcha challenge. Note that the accessibility workflow looks to have been turned off and therefore this code will not currently work!

For way more detail, see https://pressers.name/enigma2022

## Running code

The following commands are examples and could help guide usage. You will need to substitute in your own VM IP address ($VM_IP) and domain name ($DOMAIN)

```shell
./setup_env.sh
# At this point you need to do the manual step of setting up the domain so that the DNS MX record points to $VM_IP
ssh -XC -i handicaptcha ubuntu@$VM_IP
xtigervncviewer -SecurityTypes VncAuth -passwd /home/ubuntu/.vnc/passwd :1 &
./handicaptcha.py --platform aws --max-count 1 --outfile ~/handicaptcha.out --domain $DOMAIN --period 1
```

# Measures hCaptcha has against abuse of this

As best as I can tell, rate limiting, basically.

* There is a rate limit on how frequently one may request accessibility cookies
* There is a rate limit on how fast one may sign up for accounts using the same TLD or same IP.
* Having active and detectable browser automation overrides the presence of the accessibility cookie
* Others? They're an Intuition Machines/hCaptcha secret.

# Accessibility shortcomings

* It's weird to get to the checkbox with just a keyboard
* PrivacyPass doesn't appear to function with accessibility cookies

# What's "handicaptcha"?

When I was first working on this project, I was talking with a friend with a disability about the project. I was concerned that the work might make things worse for people with disabilities by getting this (ultimately) useful workflow taken away. She pointed out it was probably worth it to improve the tools available to those with disabilities and to hopefully push hCaptcha to make this workflow truely equitable.

Additionally, she suggested the name "handicaptcha". She felt the name was ironic, clever, memorable and would capture that this was a broken workflow impeding people with disabilities. Additionally, she felt it could help destigmatize or reclaim the term handicapped.

Ultimately, I decided that as a non-disabled/temporarily-able-bodied person, I was not the right person to try to reclaim a term. Additionally, I don't want a name that uses a controversial term to distract from the impact of the rest of the project. However, I didn't come to that realization until very late in the project, so I can no longer remove the name from all the locations I used it. In short, I put the name in some indelable places and can't change it, even though I'd like to.
