#!/usr/bin/env python3

"""lair_client.py

CLI client for The Lair chat server.

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
from modules.ChatClient import ChatClient


def main():
    """Main function."""
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='The Lair Chat Server Client',
        epilog='Copyright Michael Berry 2019')

    # Client arguments
    client_args = parser.add_argument_group('client arguments')

    client_args.add_argument(
        'address',
        type=str,
        help='specifies the server address the client will connect to')

    client_args.add_argument(
        'port',
        type=int,
        help='specifies which port the client should use')

    # Parse the command line
    args = parser.parse_args()

    # Run the chat client
    ChatClient(args.address, args.port).run()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
