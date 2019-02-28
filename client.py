#!/usr/bin/env python3


"""Single threaded chat client for chat server application."""


import socket
import select
import sys


def usage():
    print('usage: {} ipaddress port'.format(sys.argv[0]))
    sys.exit(1)


class ChatClient():
    """Create a chat client."""

    def __init__(self):
        """Create a chat client connection."""

        self.exit_flag = False
        self.ADDR = sys.argv[1]
        try:
            self.PORT = int(sys.argv[2])
        except ValueError:
            print('Error: port must be a number.')
            usage()
        self.BUFSIZ = 4096
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as err:
            print('Error: {}'.format(err))
            sys.exit(1)
        try:
            self.server.connect((self.ADDR, self.PORT))
        except socket.error as err:
            print('Error: {}'.format(err))
            sys.exit(1)

    def run(self):
        """Run a client session."""

        while not self.exit_flag:
            self.select_loop()

    def select_loop(self):
        sockets = [sys.stdin, self.server]

        rlist, wlist, xlist = select.select(sockets, [], [], 60)

        for sock in rlist:
            if sock == self.server:
                try:
                    msg = sock.recv(self.BUFSIZ).decode('utf8')
                    if msg == 'The lair is closed.':
                        print(msg)
                        self.server.close()
                        self.exit_flag = True
                        break
                    else:
                        print(msg)
                except socket.error as err:
                    print('Error: {}'.format(err))
            else:
                msg = input('')
                try:
                    self.server.send(bytes(msg, 'utf8'))
                except socket.error as err:
                    print('Error: {}'.format(err))
                    sys.exit(1)
                if msg == '{quit}':
                    self.exit_flag = True
                    break

# Main function
def main():
    if len(sys.argv) != 3:
        usage()

    ChatClient().run()


# main? Program entry point
if __name__ == '__main__':
    sys.exit(main())
