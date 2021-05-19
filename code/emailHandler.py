import queue
import smtpd
import threading
import asyncore
import sys
import email

class EmailServer(smtpd.SMTPServer, object):
    def __init__(self, *args, **kwargs):
        self.mq = queue.Queue()
        server_address = ('0.0.0.0', 2525)
        print('starting up on %s port %s' % server_address, file=sys.stderr)

        super().__init__(localaddr=server_address, remoteaddr=None)
        threading.Thread(target=asyncore.loop, daemon=True).start()
        print("Server started", file=sys.stderr)
    
    def process_message(self, peer, mailfrom, rcpttos, data, mail_options=None, rcpt_options=None):
        print("Incoming message from {0}, data:\n{1}".format(mailfrom, data), file=sys.stderr)
        self.mq.put(data)
    
    def getEmail(self):
        print("Getting message from queue")
        return str(self.mq.get())
    
def decodeEmailBody(body):
    #return quopri.decodestring(body)
    m = email.message_from_string(body)

    if m.is_multipart():
        for part in m.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            # skip any text/plain (txt) attachments
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = m.get_payload(decode=True)
    # This is an awful hack, but we don't actually care abotu the text being to intact..
    return str(body)

if __name__=="__main__":
    s = EmailServer()
    mail = s.getEmail()
    print(decodeEmailBody(mail))