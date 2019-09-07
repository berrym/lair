#!/usr/bin/env python3

"""lair.py

The Lair - A simple chat application.

Copyright (C) <2019>  <Michael Berry>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import argparse
from modules.ChatServer import ChatServer
from modules.ChatClient import ChatClient


def main():
    """Main Function."""
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        description='The Lair Chat App',
        epilog='Copyright (C) <2019> Michael Berry')

    lair_options = parser.add_argument_group('Lair Arguments')

    lair_options.add_argument(
        'session',
        type=str,
        help='specifies wether to run a server or client session')

    lair_options.add_argument(
        'address',
        type=str,
        help='specifies the address the server will bind to')

    lair_options.add_argument(
        'port',
        type=int,
        help='specifies which port the server will bind to')

    # Parse the command line
    args = parser.parse_args()

    if args.session == 'server':
        ChatServer(args.address, args.port).run()
    elif args.session == 'client':
        ChatClient(args.address, args.port).run()
    else:
        print('{}: error: session must be either server or client'.format(
            sys.argv[0]))


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
