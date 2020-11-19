import socket
import sys
import quopri
import email
from email.message import Message

class EmailServer:
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
    #return quopri.decodestring(body)
    m = email.message_from_string(body)

    if m.is_multipart():
        for part in m.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            # skip any text/plain (txt) attachments
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
                break
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = m.get_payload(decode=True)
    return body

if __name__=="__main__":
    es = EmailServer()
    m = es.getEmail()
    print(decodeEmailBody(m))
    