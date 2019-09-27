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
import os
import sys
import subprocess
from typing import *

from modules.cli.ChatClient import ChatClient
from modules.cli.ChatServer import ChatServer

# Program name
prog = sys.argv[0]
prog.replace('./', '')


def catch_keyboard_interrupt(func: Callable) -> Any:
    """Catch keyboard interrupt and exit process."""

    def wrapper(*args, **kwargs) -> Any:
        """Wrapper around func to catch keyboard interrupt."""
        try:
            result = func(*args, **kwargs)
            return result
        except KeyboardInterrupt:
            sys.exit(0)

    return wrapper


@catch_keyboard_interrupt
def main() -> None:
    """Main Function."""
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        description='The Lair Chat App',
        epilog='Copyright (C) 2019 Michael Berry')

    # Lair options
    lair_options = parser.add_argument_group('Lair Arguments')

    # Required option, either server or client
    lair_options.add_argument(
        'session_type',
        type=str,
        help='specifies whether to run a "server" or "client" session')

    # Server options
    server_options = parser.add_argument_group('Server Arguments')

    server_options.add_argument(
        '--address',
        type=str,
        default='127.0.0.1',
        help='specifies the address the server will bind to')

    server_options.add_argument(
        '--port',
        type=int,
        default=8888,
        help='specifies which port the server will bind to')

    # Client options
    client_options = parser.add_argument_group('Client Arguments')

    client_options.add_argument(
        '--gui',
        default=False,
        action='store_true',
        help='run the Qt gui client'
    )

    client_options.add_argument(
        '--sa',
        default='127.0.0.1',
        type=str,
        help='specifies the address of the server'
    )

    client_options.add_argument(
        '--sp',
        default=8888,
        type=int,
        help='specifies which port on the server to connect to'
    )

    # Parse the command line
    args = parser.parse_args()

    if args.session_type == 'server':
        ChatServer(args.address, args.port).run()
    elif args.session_type == 'client':
        if not args.gui:
            ChatClient(args.sa, args.sp).run()
        else:
            # exec gui client
            subprocess.Popen(os.path.join(sys.path[0], 'lair_client-qt.py'))
            return
    else:
        print(f'{prog}: error: session_type must be either server or client')


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
