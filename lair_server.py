#!/usr/bin/env python3

"""lair_server.py

The Lair - A simple chat server application.

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


def main():
    """Main Function."""
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='The Lair Chat Server',
        epilog='Copyright Michael Berry 2019')

    # Server arguments
    server_args = parser.add_argument_group('server arguments')

    server_args.add_argument(
        'address',
        type=str,
        help='specifies the address the server will bind to')

    server_args.add_argument(
        'port',
        type=int,
        help='specifies which port the server will bind to')

    # Parse the command line
    args = parser.parse_args()

    # Run the chat server
    ChatServer(args.address, args.port).run()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
