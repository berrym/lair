#!/usr/bin/env python3


"""lair.py

The Lair - A simple chat application.

Copyright (C) 2019 Michael Berry

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

import argparse
import sys

from modules.cli.ChatClient import ChatClient
from modules.cli.ChatServer import ChatServer

# Program name
prog = sys.argv[0]
prog.replace('./', '')


def catch_keyboard_interrupt(func):
    """Catch keyboard interrupt and exit process."""

    def wrapper(*args, **kwargs):
        """Wrapper around func to catch keyboard interrupt."""
        try:
            result = func(*args, **kwargs)
            return result
        except KeyboardInterrupt:
            sys.exit(0)

    return wrapper


@catch_keyboard_interrupt
def main():
    """Main Function."""
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        description='The Lair Chat App',
        epilog='Copyright (C) 2019 Michael Berry')

    lair_options = parser.add_argument_group('Lair Arguments')

    lair_options.add_argument(
        'session_type',
        type=str,
        help='specifies whether to run a server or client session')

    lair_options.add_argument(
        'address',
        type=str,
        help='specifies the address the server will bind to')

    lair_options.add_argument(
        'port_number',
        type=int,
        help='specifies which port the server will bind to')

    # Parse the command line
    args = parser.parse_args()

    if args.session_type == 'server':
        ChatServer(args.address, args.port_number).run()
    elif args.session_type == 'client':
        ChatClient(args.address, args.port_number).run()
    else:
        print(f'{prog}: error: session_type must be either server or client')


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
