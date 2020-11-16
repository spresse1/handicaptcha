import socket
import sys
import quopri

class emailServer:
    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = ('0.0.0.0', 25)
        print('starting up on %s port %s' % server_address, file=sys.stderr)
        sock.bind(server_address)

        sock.listen(1)

        self.sock = sock

    def getEmail(self):
        print('waiting for a connection', file=sys.stderr)
        connection, client_address = self.sock.accept()
        try:
            print('connection from', client_address, file=sys.stderr)

            connection.sendall(b"220 Don\'t even try to guess, I'm a python special!\r\n")

            data = connection.recv(1024)
            print('received "%s"' % data, file=sys.stderr)
            while data[0:4] != b'HELO':
                print('Command was not HELO', file=sys.stderr)
                connection.sendall(b"502 Command Not Supported\r\n")
                data = connection.recv(1024)
                print('received "%s"' % data, file=sys.stderr)
            connection.sendall(b"250 Go ahead\r\n")

            data = connection.recv(1024)
            print('received "%s"' % data, file=sys.stderr)
            cmd = data[0:4]
            if cmd==b"MAIL":
                connection.sendall(b'250 Go ahead\r\n')
            else:
                print("Not a MAIL command, bailing", file=sys.stderr)
                connection.sendall(b'500 Oopsie\r\n')
                return

            data = connection.recv(1024)
            print('received "%s"' % data, file=sys.stderr)
            cmd = data[0:4]
            if cmd==b"RCPT":
                connection.sendall(b'250 Go ahead\r\n')
            else:
                print("Not a RCPT command, bailing", file=sys.stderr)
                connection.sendall(b'500 Oopsie\r\n')
                return

            data = connection.recv(1024)
            print('received "%s"' % data, file=sys.stderr)
            cmd = data[0:4]
            if cmd==b"DATA":
                connection.sendall(b'354 I\'m listening...\r\n')
            else:
                print("Not a DATA command, bailing", file=sys.stderr)
                connection.sendall(b'500 Oopsie\r\n')
                return

            body = ""
            while body[-5:] != '\r\n.\r\n':
                data = connection.recv(1024)
                print('received "%s"' % data, file=sys.stderr)
                body += data.decode("utf-8")
            print('Body is "%s"' % body, file=sys.stderr)

            connection.sendall(b'250 aye aye cap\'n\r\n')

            data = connection.recv(1024)
            print('received "%s"' % data, file=sys.stderr)
            cmd = data[0:4]
            if cmd==b"QUIT":
                connection.sendall(b'221 See ya!\r\n')
            else:
                print("Not a QUIT command, bailing", file=sys.stderr)
                connection.sendall(b'500 Oopsie\r\n')
                return

            print("Done recieving mail", file=sys.stderr)
            return body
                
        finally:
            # Clean up the connection
            connection.close()
    
def decodeEmailBody(body):
    return quopri.decodestring(body)

if __name__=="__main__":
    #es = emailServer()
    #es.getEmail()

    print(decodeEmailBody('''Received: by mail-qt1-f178.google.com with SMTP id g17so13705950qts.5
        for <test@handicaptcha.com>; Mon, 16 Nov 2020 11:04:22 -0800 (PST)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=pressers.name; s=google;
        h=subject:references:to:from:message-id:date:user-agent:mime-version
         :in-reply-to;
        bh=U7uKAw+Rx9vk3+PdMqTWvB+wr6+k0qahkqy/c/tg2lQ=;
        b=c67HG4iVZzS7X2FtPk0IhIwo3wloxix1pKTfcF/XTwd6dCCCpFZlpi2WtZZ0GgmPrn
         gCLAVZs5SDyev1flikOhhJWlUYNswUcEHPB0l/mb4JIl9MM/mQrrDxP1IZJ2eU7/f2Mu
         DvCvU8uU6wTYfGpiNM5sNBRF+LNlOCodRKe2M=
X-Google-DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=1e100.net; s=20161025;
        h=x-gm-message-state:subject:references:to:from:message-id:date
         :user-agent:mime-version:in-reply-to;
        bh=U7uKAw+Rx9vk3+PdMqTWvB+wr6+k0qahkqy/c/tg2lQ=;
        b=JmC/4r6mfF6DI9aBLX1kAdua4805BP1Cb9XjS/E+aNZHBGDeuxnk9uNnRmKShVjiv+
         ckk9TBqavnUEYUeVaSCzZOVbuXzpCE74kb5R6CAB9bqWImKY58lqzIp6xiOvdeQc0BFv
         h4kWwqm0SDuufo6mknudEi/PFK778KA1TsXpFQO5CLSAfQePTiZSEJhginNcarcO232/
         R4WueRlKJzjQZIE9qHgZf4/w1MFfn/79y04ElRwqnKWs8xlghaC69ORInqcpqcMAGADA
         SnZs28iHXVgpxMj9W0/GcYVx+CAFe2psLca7Oh+7jJKS27I2LXCl4kdqit3JZn9RlqiS
         ieyw==
X-Gm-Message-State: AOAM532sIVPDnBMX7teEmA9ikUjDklhAJdpoGLZld6khIs5+aWNoMn4H
	X0o6cM8OD2iyHDYBUh9P7hIIOdlRqM7saA==
X-Google-Smtp-Source: ABdhPJzVHfoBZlpAfNZMzvA+MdKUxvBbNsVje3gVExDNCLVqciX8OKrgO0DnaSfz7Eda1/QkQrCg5Q==
X-Received: by 2002:ac8:6601:: with SMTP id c1mr15909700qtp.106.1605553461440;
        Mon, 16 Nov 2020 11:04:21 -0800 (PST)
Return-Path: <steve@pressers.name>
Received: from [10.0.0.165] (c-76-19-6-127.hsd1.ma.comcast.net. [76.19.6.127])
        by smtp.googlemail.com with ESMTPSA id h26sm13168454qkh.127.2020.11.16.11.04.19
        for <test@handicaptcha.com>
        (version=TLS1_3 cipher=TLS_AES_128_GCM_SHA256 bits=128/128);
        Mon, 16 Nov 2020 11:04:20 -0800 (PST)
Subject: Fwd: Instructions for using hCaptcha Accessibility
References: <01010175b97be4c7-d4075b64-8ea1-46cc-8909-e0419be58085-000000@us-west-2.amazonses.com>
To: test@handicaptcha.com
From: Steven Presser <steve@pressers.name>
X-Forwarded-Message-Id: <01010175b97be4c7-d4075b64-8ea1-46cc-8909-e0419be58085-000000@us-west-2.amazonses.com>
Message-ID: <8954b837-0487-89e7-a637-3cde1454218d@pressers.name>
Date: Mon, 16 Nov 2020 14:04:19 -0500
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101
 Thunderbird/68.9.0
MIME-Version: 1.0
In-Reply-To: <01010175b97be4c7-d4075b64-8ea1-46cc-8909-e0419be58085-000000@us-west-2.amazonses.com>
Content-Type: multipart/signed; protocol="application/pkcs7-signature"; micalg=sha-256; boundary="------------ms080405020801060903060803"

This is a cryptographically signed message in MIME format.

--------------ms080405020801060903060803
Content-Type: multipart/alternative;
 boundary="------------28E5DB59E77A557B629CCEDF"
Content-Language: en-US

This is a multi-part message in MIME format.
--------------28E5DB59E77A557B629CCEDF
Content-Type: text/plain; charset=windows-1252; format=flowed
Content-Transfer-Encoding: quoted-printable




-------- Forwarded Message --------
Subject: 	Instructions for using hCaptcha Accessibility
Date: 	Wed, 11 Nov 2020 22:45:05 +0000
From: 	status@hcaptcha.com
Reply-To: 	status@hcaptcha.com
To: 	hcaptchatest3@pressers.name



=09
hCaptcha logo
Please click here to log in to hCaptcha.


  Welcome to hCaptcha Accessibility!

Please click here to log in to hCaptcha.

Get Accessibility Cookie=20
<https://accounts.hcaptcha.com/verify_email/bfb6b5a4-c0cd-4328-8385-d2da4=
77972ea>=20


This will let you set a cookie that enables you to skip requests for=20
hCaptcha challenges.

Save this email or bookmark the link above, then open it and click the=20
link again in order to refresh the cookie if you start to see challenges =

again.

Please note that the number of requests per day is limited, and your IP=20
and account will be banned in the event of abuse.

Please email support@hcaptcha.com if you have any questions or difficulti=
es.

=A9 2020.hCaptcha is a service and registered trademark of Intuition=20
Machines, Inc.

This is a service-related email. If you wish to remove your account and=20
no longer receive service-related emails, contact support via our=20
website or reply to this email with "Delete My Account" in the subject li=
ne.

hCaptcha respects your privacy. For a complete description of our=20
privacy policy, please visit our website. hCaptcha.com/privacy=20
<https://www.hcaptcha.com/privacy>

=09


--------------28E5DB59E77A557B629CCEDF
Content-Type: multipart/related;
 boundary="------------83D7012FD96A12EF997380E6"


--------------83D7012FD96A12EF997380E6
Content-Type: text/html; charset=windows-1252
Content-Transfer-Encoding: quoted-printable

<html>
  <head>

    <meta http-equiv=3D"content-type" content=3D"text/html; charset=3Dwin=
dows-1252">
  </head>
  <body>
    <p><br>
    </p>
    <div class=3D"moz-forward-container"><br>
      <br>
      -------- Forwarded Message --------
      <table class=3D"moz-email-headers-table" cellspacing=3D"0"
        cellpadding=3D"0" border=3D"0">
        <tbody>
          <tr>
            <th valign=3D"BASELINE" nowrap=3D"nowrap" align=3D"RIGHT">Sub=
ject:
            </th>
            <td>Instructions for using hCaptcha Accessibility</td>
          </tr>
          <tr>
            <th valign=3D"BASELINE" nowrap=3D"nowrap" align=3D"RIGHT">Dat=
e: </th>
            <td>Wed, 11 Nov 2020 22:45:05 +0000</td>
          </tr>
          <tr>
            <th valign=3D"BASELINE" nowrap=3D"nowrap" align=3D"RIGHT">Fro=
m: </th>
            <td><a class=3D"moz-txt-link-abbreviated" href=3D"mailto:stat=
us@hcaptcha.com">status@hcaptcha.com</a></td>
          </tr>
          <tr>
            <th valign=3D"BASELINE" nowrap=3D"nowrap" align=3D"RIGHT">Rep=
ly-To:
            </th>
            <td><a class=3D"moz-txt-link-abbreviated" href=3D"mailto:stat=
us@hcaptcha.com">status@hcaptcha.com</a></td>
          </tr>
          <tr>
            <th valign=3D"BASELINE" nowrap=3D"nowrap" align=3D"RIGHT">To:=
 </th>
            <td><a class=3D"moz-txt-link-abbreviated" href=3D"mailto:hcap=
tchatest3@pressers.name">hcaptchatest3@pressers.name</a></td>
          </tr>
        </tbody>
      </table>
      <br>
      <br>
      <meta name=3D"viewport" content=3D"width=3Ddevice-width">
      <meta http-equiv=3D"Content-Type" content=3D"text/html;
        charset=3Dwindows-1252">
      <title></title>
      <style>
      /* -------------------------------------
          GLOBAL RESETS
      ------------------------------------- */
      img {
        border: none;
        -ms-interpolation-mode: bicubic;
        max-width: 100%; }

      body {
        background-color: #f6f6f6;
        font-family: sans-serif;
        -webkit-font-smoothing: antialiased;
        font-size: 14px;
        line-height: 1.4;
        margin: 0;
        padding: 0;
        -ms-text-size-adjust: 100%;
        -webkit-text-size-adjust: 100%; }

      table {
        border-collapse: separate;
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
        width: 100%; }
        table td {
          font-family: sans-serif;
          font-size: 14px;
          vertical-align: top; }

      /* -------------------------------------
          BODY & CONTAINER
      ------------------------------------- */

      .body {
        background-color: #f6f6f6;
        width: 100%; }

      /* Set a max-width, and make it display as block so it will automat=
ically stretch to that width, but will also shrink down on a phone or som=
ething */
      .container {
        display: block;
        Margin: 0 auto !important;
        /* makes it centered */
        max-width: 580px;
        padding: 10px;
        width: 580px; }

      /* This should also be a block element, so that it will fill 100% o=
f the .container */
      .content {
        box-sizing: border-box;
        display: block;
        Margin: 0 auto;
        max-width: 580px;
        padding: 10px; }

      /* -------------------------------------
          HEADER, FOOTER, MAIN
      ------------------------------------- */
      .main {
        background: #ffffff;
        border-radius: 3px;
        width: 100%; }

      .wrapper {
        box-sizing: border-box;
        padding: 20px; }

      .content-block {
        padding-bottom: 10px;
        padding-top: 10px;
      }

      .footer {
        clear: both;
        Margin-top: 10px;
        text-align: center;
        width: 100%; }
        .footer td,
        .footer p,
        .footer span,
        .footer a {
          color: #999999;
          font-size: 12px;
          text-align: center; }

      /* -------------------------------------
          TYPOGRAPHY
      ------------------------------------- */
      h1,
      h2,
      h3,
      h4 {
        color: #000000;
        font-family: sans-serif;
        font-weight: 400;
        line-height: 1.4;
        margin: 0;
        Margin-bottom: 30px; }

      h1 {
        font-size: 35px;
        font-weight: 300;
        text-align: left; }

      p,
      ul,
      ol {
        font-family: sans-serif;
        font-size: 14px;
        font-weight: normal;
        margin: 0;
        Margin-bottom: 15px; }
        p li,
        ul li,
        ol li {
          list-style-position: inside;
          margin-left: 5px; }

      a {
        color: #3498db;
        text-decoration: underline; }

      /* -------------------------------------
          BUTTONS
      ------------------------------------- */
      .btn {
        box-sizing: border-box;
        width: 100%;
        }
        .btn > tbody > tr > td {
          padding-bottom: 15px; }
        .btn table {
          width: auto; }
        .btn table td {
          background-color: #ffffff;
          border-radius: 5px;
          text-align: center; }
        .btn a {
          background-color: #ffffff;
          border: solid 1px #00615e;
          border-radius: 5px;
          box-sizing: border-box;
          color: #3498db;
          cursor: pointer;
          display: inline-block;
          font-size: 14px;
          font-weight: bold;
          margin: 0;
          padding: 12px 25px;
          text-decoration: none; }

      .btn-primary table td {
        background-color: #3498db; }

      .btn-primary a {
        background-color: #00615e;
        color: #ffffff; }

      /* -------------------------------------
          OTHER STYLES THAT MIGHT BE USEFUL
      ------------------------------------- */
        .logo {
            max-width:100%;
            width: 180px;
            margin: 20px;
            margin-left:auto;
            margin-right:auto;
        }
      .last {
        margin-bottom: 0; }

      .first {
        margin-top: 0; }

      .align-center {
        text-align: center; }

      .align-right {
        text-align: right; }

      .align-left {
        text-align: left; }

      .clear {
        clear: both; }

      .mt0 {
        margin-top: 0; }

      .mb0 {
        margin-bottom: 0; }

      .preheader {
        color: transparent;
        display: none;
        height: 0;
        max-height: 0;
        max-width: 0;
        opacity: 0;
        overflow: hidden;
        mso-hide: all;
        visibility: hidden;
        width: 0; }

      hr {
        border: 0;
        border-bottom: 1px solid #f6f6f6;
        Margin: 20px 0; }

      /* -------------------------------------
          RESPONSIVE AND MOBILE FRIENDLY STYLES
      ------------------------------------- */
      @media only screen and (max-width: 620px) {
        table[class=3Dbody] h1 {
          font-size: 28px !important;
          margin-bottom: 10px !important; }
        table[class=3Dbody] p,
        table[class=3Dbody] ul,
        table[class=3Dbody] ol,
        table[class=3Dbody] td,
        table[class=3Dbody] span,
        table[class=3Dbody] a {
          font-size: 16px !important; }
        table[class=3Dbody] .wrapper,
        table[class=3Dbody] .article {
          padding: 10px !important; }
        table[class=3Dbody] .content {
          padding: 0 !important; }
        table[class=3Dbody] .container {
          padding: 0 !important;
          width: 100% !important; }
        table[class=3Dbody] .main {
          border-left-width: 0 !important;
          border-radius: 0 !important;
          border-right-width: 0 !important; }
        table[class=3Dbody] .btn table {
          width: 100% !important; }
        table[class=3Dbody] .btn a {
          width: 100% !important; }
        table[class=3Dbody] .img-responsive {
          height: auto !important;
          max-width: 100% !important;
          width: auto !important; }}

      /* -------------------------------------
          PRESERVE THESE STYLES IN THE HEAD
      ------------------------------------- */
      @media all {
        .ExternalClass {
          width: 100%; }
        .ExternalClass,
        .ExternalClass p,
        .ExternalClass span,
        .ExternalClass font,
        .ExternalClass td,
        .ExternalClass div {
          line-height: 100%; }
        .apple-link a {
          color: inherit !important;
          font-family: inherit !important;
          font-size: inherit !important;
          font-weight: inherit !important;
          line-height: inherit !important;
          text-decoration: none !important; }
        .btn-primary table td:hover {
          background-color: #00807b !important; }
        .btn-primary a:hover {
          background-color: #00807b !important;
          border-color: #00807b !important; } }

    </style>
      <table class=3D"body" role=3D"presentation" cellspacing=3D"0"
        cellpadding=3D"0" border=3D"0">
        <tbody>
          <tr>
            <td>=A0</td>
            <td class=3D"container">
              <div class=3D"content">
                <div class=3D"logo"> <img
                    src=3D"cid:part1.B4F33976.D98061D1@pressers.name"
                    alt=3D"hCaptcha logo" class=3D""> </div>
                <!-- START CENTERED WHITE CONTAINER --> <span
                  class=3D"preheader">Please click here to log in to
                  hCaptcha.</span>
                <table class=3D"main">
                  <!-- START MAIN CONTENT AREA --> <tbody>
                    <tr>
                      <td class=3D"wrapper">
                        <table cellspacing=3D"0" cellpadding=3D"0"
                          border=3D"0">
                          <tbody>
                            <tr>
                              <td>
                                <h1>Welcome to hCaptcha Accessibility!</h=
1>
                                <p>Please click here to log in to
                                  hCaptcha.</p>
                                <table class=3D"btn btn-primary"
                                  cellspacing=3D"0" cellpadding=3D"0"
                                  border=3D"0">
                                  <tbody>
                                    <tr>
                                      <td align=3D"left">
                                        <table cellspacing=3D"0"
                                          cellpadding=3D"0" border=3D"0">=

                                          <tbody>
                                            <tr>
                                              <td> <a
href=3D"https://accounts.hcaptcha.com/verify_email/bfb6b5a4-c0cd-4328-838=
5-d2da477972ea"
                                                  target=3D"_blank"
                                                  moz-do-not-send=3D"true=
">Get
                                                  Accessibility Cookie</a=
>
                                              </td>
                                            </tr>
                                          </tbody>
                                        </table>
                                      </td>
                                    </tr>
                                  </tbody>
                                </table>
                                <p>This will let you set a cookie that
                                  enables you to skip requests for
                                  hCaptcha challenges.</p>
                                <p>Save this email or bookmark the link
                                  above, then open it and click the link
                                  again in order to refresh the cookie
                                  if you start to see challenges again.</=
p>
                                <p>Please note that the number of
                                  requests per day is limited, and your
                                  IP and account will be banned in the
                                  event of abuse.</p>
                                <p>Please email <a class=3D"moz-txt-link-=
abbreviated" href=3D"mailto:support@hcaptcha.com">support@hcaptcha.com</a=
> if
                                  you have any questions or
                                  difficulties.</p>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                    <!-- END MAIN CONTENT AREA -->
                  </tbody>
                </table>
                <!-- START FOOTER -->
                <div class=3D"footer" role=3D"contentinfo">
                  <table cellspacing=3D"0" cellpadding=3D"0" border=3D"0"=
>
                    <tbody>
                      <tr>
                        <td class=3D"content-block"> <span
                            class=3D"apple-link">=A9 2020.hCaptcha is a
                            service and registered trademark of
                            Intuition Machines, Inc. <br>
                            <br>
                            This is a service-related email. If you wish
                            to remove your account and no longer receive
                            service-related emails, contact support via
                            our website or reply to this email with
                            "Delete My Account" in the subject line.<br>
                            <br>
                            hCaptcha respects your privacy. For a
                            complete description of our privacy policy,
                            please visit our website. <a
                              href=3D"https://www.hcaptcha.com/privacy"
                              moz-do-not-send=3D"true">hCaptcha.com/priva=
cy</a>
                          </span> </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <!-- END FOOTER -->
                <!-- END CENTERED WHITE CONTAINER --> </div>
            </td>
            <td>=A0</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>

--------------83D7012FD96A12EF997380E6
Content-Type: image/png;
 name="horizontal-logo.png"
Content-Transfer-Encoding: base64
Content-ID: <part1.B4F33976.D98061D1@pressers.name>
Content-Disposition: inline;
 filename="horizontal-logo.png"

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
--------------83D7012FD96A12EF997380E6--

--------------28E5DB59E77A557B629CCEDF--

--------------ms080405020801060903060803
Content-Type: application/pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"
Content-Description: S/MIME Cryptographic Signature

MIAGCSqGSIb3DQEHAqCAMIACAQExDzANBglghkgBZQMEAgEFADCABgkqhkiG9w0BBwEAAKCC
C3cwggTsMIID1KADAgECAhA80zZxJTi8LJZclBwe+ti2MA0GCSqGSIb3DQEBCwUAMIGNMQsw
CQYDVQQGEwJJVDEQMA4GA1UECAwHQmVyZ2FtbzEZMBcGA1UEBwwQUG9udGUgU2FuIFBpZXRy
bzEjMCEGA1UECgwaQWN0YWxpcyBTLnAuQS4vMDMzNTg1MjA5NjcxLDAqBgNVBAMMI0FjdGFs
aXMgQ2xpZW50IEF1dGhlbnRpY2F0aW9uIENBIEcyMB4XDTE5MTIwNTIyMzAwOVoXDTIwMTIw
NTIyMzAwOVowHjEcMBoGA1UEAwwTc3RldmVAcHJlc3NlcnMubmFtZTCCASIwDQYJKoZIhvcN
AQEBBQADggEPADCCAQoCggEBAKMs4AbFBf3WFrzGclBrFjMiVh8qB3Zw+8lRsgQkvdQweUkw
BPBM/+62U1ArPW1qaJ36MKMt5leB6hzfhDI8222sj5gzl//H8ZEG2Mm/AjIQy6zusLtjZzSd
rdC8EFhDWPf/N66jsXhNkqg1XYyRWXMzEY824aIxslyqqmIVVOIuQHGWI58gY0MZ+TfMfO0R
n56F+ilx2F13OI9Wn9J428EEzE4BkKxMlj0V6xPbLI4FXz+V0Q4a5CbZvgwdvblzHCxX/fdE
QrP6ErcHuDWp5bHiyHKpiftZEio/A6QzH5GtgowhXQ5xmAS9FrLjd8iF4ICJstYwcucsEH2m
SS4zQzMCAwEAAaOCAbQwggGwMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAUa/KNnmjBJQQf
UTRX9hZclOpNaRowfgYIKwYBBQUHAQEEcjBwMDsGCCsGAQUFBzAChi9odHRwOi8vY2FjZXJ0
LmFjdGFsaXMuaXQvY2VydHMvYWN0YWxpcy1hdXRjbGlnMjAxBggrBgEFBQcwAYYlaHR0cDov
L29jc3AwOS5hY3RhbGlzLml0L1ZBL0FVVEhDTC1HMjAeBgNVHREEFzAVgRNzdGV2ZUBwcmVz
c2Vycy5uYW1lMEcGA1UdIARAMD4wPAYGK4EfARgBMDIwMAYIKwYBBQUHAgEWJGh0dHBzOi8v
d3d3LmFjdGFsaXMuaXQvYXJlYS1kb3dubG9hZDAdBgNVHSUEFjAUBggrBgEFBQcDAgYIKwYB
BQUHAwQwSAYDVR0fBEEwPzA9oDugOYY3aHR0cDovL2NybDA5LmFjdGFsaXMuaXQvUmVwb3Np
dG9yeS9BVVRIQ0wtRzIvZ2V0TGFzdENSTDAdBgNVHQ4EFgQUFvt2+8MHYHa01m3gjvmC0Zrb
NygwDgYDVR0PAQH/BAQDAgWgMA0GCSqGSIb3DQEBCwUAA4IBAQANL0YvyfJ691ZL/q005KrH
OVMRlK68ZrWxFOOQSVVYjGvS4hLX0mL7lBsnbsk9ht4LJzlPGUjwkQyLIPCRvnLG+iyfaZx4
qCHoLyzSbo0JeX30yWeDuytxtUS0civbM2LvIXGSASqYSLOebuuymBVErXt69KmkaiGdOaME
iBncZnV+LBrHZl8njgRZDKhWev+1FQdQdQfg51cncpH4qnjzqH89JQ+ELzDJW0932tQ/p6kN
vWaEzGXTgzy8W0n2L3sDkpWEdMOHGkdIdpBvWDS0gD8Xdo1qebS8zyVGjU48OM8r1VxZehtD
q46UGbgwIUHKz7I5CvzVqtcMH+Z8lpAvMIIGgzCCBGugAwIBAgIQT94QS+2VW96LrWWHzEFe
4zANBgkqhkiG9w0BAQsFADBrMQswCQYDVQQGEwJJVDEOMAwGA1UEBwwFTWlsYW4xIzAhBgNV
BAoMGkFjdGFsaXMgUy5wLkEuLzAzMzU4NTIwOTY3MScwJQYDVQQDDB5BY3RhbGlzIEF1dGhl
bnRpY2F0aW9uIFJvb3QgQ0EwHhcNMTkwOTIwMDcxMjA1WhcNMzAwOTIyMTEyMjAyWjCBjTEL
MAkGA1UEBhMCSVQxEDAOBgNVBAgMB0JlcmdhbW8xGTAXBgNVBAcMEFBvbnRlIFNhbiBQaWV0
cm8xIzAhBgNVBAoMGkFjdGFsaXMgUy5wLkEuLzAzMzU4NTIwOTY3MSwwKgYDVQQDDCNBY3Rh
bGlzIENsaWVudCBBdXRoZW50aWNhdGlvbiBDQSBHMjCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBALdoc3rZPNQv+9xnyj3OlHz/iRnO2hpj8xlHkCdYKNwnRabAT6J0RA11A3Zk
QiEZEw66B99ES7Ezv9IRBYmIwsr720lUptObF5L3yVzl3nzaittXwWsq+CQoDEci1cKkWF5S
iO22+Np2Epu2HFxkw5nXMnZibrqnC6hUGsFogTDUUVRIuLlublwWYFhpqvDaCh//ucRgRW3+
rTU1nBoT1XHkXrLsCteefjoh+o01tNTWvGi4+3OyABidGPXuoYh7UbYX1u0sG1O8rO92t5zV
7/Cr/Vza9EbySh6DrCqsY333sNxikKzFyBwebZv43t1xJyMVE/CRt7BLJOyHxd1Yq0sCAwEA
AaOCAf4wggH6MA8GA1UdEwEB/wQFMAMBAf8wHwYDVR0jBBgwFoAUUtiIOsifeGbtifN7OHCU
yQICNtAwQQYIKwYBBQUHAQEENTAzMDEGCCsGAQUFBzABhiVodHRwOi8vb2NzcDA1LmFjdGFs
aXMuaXQvVkEvQVVUSC1ST09UMEUGA1UdIAQ+MDwwOgYEVR0gADAyMDAGCCsGAQUFBwIBFiRo
dHRwczovL3d3dy5hY3RhbGlzLml0L2FyZWEtZG93bmxvYWQwJwYDVR0lBCAwHgYIKwYBBQUH
AwIGCCsGAQUFBwMEBggrBgEFBQcDCTCB4wYDVR0fBIHbMIHYMIGWoIGToIGQhoGNbGRhcDov
L2xkYXAwNS5hY3RhbGlzLml0L2NuJTNkQWN0YWxpcyUyMEF1dGhlbnRpY2F0aW9uJTIwUm9v
dCUyMENBLG8lM2RBY3RhbGlzJTIwUy5wLkEuJTJmMDMzNTg1MjA5NjcsYyUzZElUP2NlcnRp
ZmljYXRlUmV2b2NhdGlvbkxpc3Q7YmluYXJ5MD2gO6A5hjdodHRwOi8vY3JsMDUuYWN0YWxp
cy5pdC9SZXBvc2l0b3J5L0FVVEgtUk9PVC9nZXRMYXN0Q1JMMB0GA1UdDgQWBBRr8o2eaMEl
BB9RNFf2FlyU6k1pGjAOBgNVHQ8BAf8EBAMCAQYwDQYJKoZIhvcNAQELBQADggIBAGBEuhmi
q3L7DkGaRMG6FTm9na4v3ya3KW+xkhFvSZgPinqeBi5qfV+dCL/BCuO/JMH9mgI5z57DnYiL
QC3CIHnEtalcTfhGPleRgjRMuFQLAeYM5UAZiiPT+D8S7faZ0CZ3glRLw51QTGQJZSC+bN7m
goiBG/HmGahvLWjlkjNZ6o6AmVC3HIV1mGowamiYNEVDmen+SAdJW9uhwP+xFFZodZ0lYJQ6
FHg+3pSDVx6YdM94n9e9tlMnXKB+CY92WmPXbUOMCUjYUmTsxEu9lJEusHv+eehThrO6HiVr
kHvEathHnkhphpYmSlG2KOIwfwtqJjJ9C+EMCOcDDa1ndhUTVFMMTAZmyWLRGg0U0O9hzwPA
520ZL0Q0iZI7E6KlOmaQZQX+LORMK4V6hVW9qzPZhgjw2SYux8N8vAWA/3d4ky+j1uVIzk0q
RXJ0iD+B1uTyOjEx15fmm+mowp7ycOhNUxi4d8ycqb+QkPBbZtM+zCi7eWa9hOI6I2V3mZ9b
FKUqonWcqfZhvy2DEZhzJLYQ0Zw5ztrR7+fmDjuHFBG07eQcMBOUT46qL7J3ncneUooyCvpN
TAlxSzE3xEc96lDd4v38Lnl3BsuIxH9p/xb2LBGNxgR12QjFVj33wX25fyE47PUPTRt+2wBJ
v5oNsjatNjS4w20CCoLfVtGgVPUrMYIEFzCCBBMCAQEwgaIwgY0xCzAJBgNVBAYTAklUMRAw
DgYDVQQIDAdCZXJnYW1vMRkwFwYDVQQHDBBQb250ZSBTYW4gUGlldHJvMSMwIQYDVQQKDBpB
Y3RhbGlzIFMucC5BLi8wMzM1ODUyMDk2NzEsMCoGA1UEAwwjQWN0YWxpcyBDbGllbnQgQXV0
aGVudGljYXRpb24gQ0EgRzICEDzTNnElOLwsllyUHB762LYwDQYJYIZIAWUDBAIBBQCgggJF
MBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTIwMTExNjE5MDQx
OVowLwYJKoZIhvcNAQkEMSIEIBrtJqbx4LOTfGLrIb8WblJHH72rPk8e53K3haCzCsPTMGwG
CSqGSIb3DQEJDzFfMF0wCwYJYIZIAWUDBAEqMAsGCWCGSAFlAwQBAjAKBggqhkiG9w0DBzAO
BggqhkiG9w0DAgICAIAwDQYIKoZIhvcNAwICAUAwBwYFKw4DAgcwDQYIKoZIhvcNAwICASgw
gbMGCSsGAQQBgjcQBDGBpTCBojCBjTELMAkGA1UEBhMCSVQxEDAOBgNVBAgMB0JlcmdhbW8x
GTAXBgNVBAcMEFBvbnRlIFNhbiBQaWV0cm8xIzAhBgNVBAoMGkFjdGFsaXMgUy5wLkEuLzAz
MzU4NTIwOTY3MSwwKgYDVQQDDCNBY3RhbGlzIENsaWVudCBBdXRoZW50aWNhdGlvbiBDQSBH
MgIQPNM2cSU4vCyWXJQcHvrYtjCBtQYLKoZIhvcNAQkQAgsxgaWggaIwgY0xCzAJBgNVBAYT
AklUMRAwDgYDVQQIDAdCZXJnYW1vMRkwFwYDVQQHDBBQb250ZSBTYW4gUGlldHJvMSMwIQYD
VQQKDBpBY3RhbGlzIFMucC5BLi8wMzM1ODUyMDk2NzEsMCoGA1UEAwwjQWN0YWxpcyBDbGll
bnQgQXV0aGVudGljYXRpb24gQ0EgRzICEDzTNnElOLwsllyUHB762LYwDQYJKoZIhvcNAQEB
BQAEggEANwy3W0q2s6XwXGut3Thp1+YHCuDNFGJy8dMtTvT8gVSpzPtIPrWCf5XmX5iL4txb
Y8aM4YYsbfMP1aYMdf4PQZ9hmEL5p3g9YMQw2xS5LiobtIjrXCLRqJrkwjiQ2jV9wm/EFllH
X5bb/l4t5vjXSPsEA4i+S38IZOXJgpclEZediwYTIzUY1bFyVSXe0wrj3S/SRU/MbKyCT0wn
ysXfCkTsEtZHRgp5vxiWVhQ2+YZc6TRF25dDRr84QDrhbTfPqPps6wA94zu+xRs8lmJj7add
0juYzJfVgkXwwInl7GbbtLEHvLsjvL1jXlPXQE6WKVT5nlB7LtUCHNns+O0iTAAAAAAAAA==
--------------ms080405020801060903060803--'''))