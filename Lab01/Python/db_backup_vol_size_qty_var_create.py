""" Oracle DB Backup - Calculate Volume size and Volume quantity"""

import argparse
from getpass import getpass
import logging
import subprocess
from typing import List, Union

class Argument:  # pylint: disable=too-few-public-methods
    """A structure to hold details of an argument"""

    def __init__(
            self,
            short_arg: str,
            long_arg: str,
            help_string: str,
            default=None,
            required=False,
            arg_type=None):
        self.short_arg = short_arg
        self.long_arg = long_arg
        self.help_string = help_string
        self.default = default
        self.required = required
        self.arg_type = arg_type if arg_type else str

def parse_args(
        program_description: str,
        arguments: List[Argument]) -> argparse.Namespace:
    """Parse the command line arguments from the user"""

    parser = argparse.ArgumentParser(description=program_description)
    for argument in arguments:
        parser.add_argument(
            argument.short_arg, argument.long_arg, required=argument.required,
            help=argument.help_string, default=argument.default, type=argument.arg_type,
        )
    parser.add_argument(
        "-d",
        "--db_size",
        default="100",
        help="Capacity in GB of Oracle DB")
    parser.add_argument(
        "-m",
        "--max_vol_size",
        default="50",
        help="Capacity in GB of MAX size of a single volume provisioned")
    parsed_args = parser.parse_args()

    return parsed_args

def db_backup_vol_size(args) -> None:
    """Ingest Database Size and Maximum volume size to provision"""
    db_size = int(args.db_size)
    max_vol_size = int(args.max_vol_size)
    """Create a varibles for the IMG and LOG volume sizes that includes multipliers related to function"""
    """IMG multiplier is 1.2 and LOG multiplier is 0.5"""
    db_size_img = db_size * 1.2
    db_size_log = db_size * 0.5

    """IMG Volume calculations"""
    vol_cnt_img_int = int(0)
    vol_size_img = int(0)

    vol_cnt_img_float = db_size_img / max_vol_size

    if vol_cnt_img_float <= 1:
        vol_cnt_img_int = int(1)
    else:
        while vol_cnt_img_float > 0:
            vol_cnt_img_int = vol_cnt_img_int + 1
            vol_cnt_img_float = vol_cnt_img_float - 1

    vol_size_img = db_size_img / vol_cnt_img_int

    vol_size_img_int = int(vol_size_img)
    vol_size_img_str = str(vol_size_img_int)
    vol_cnt_img_str = str(vol_cnt_img_int)
    print('volume_size_img: ' + vol_size_img_str)
    print('volume_count_img: ' + vol_cnt_img_str)

    """LOG Volume calculations"""
    vol_cnt_log_int = int(0)
    vol_size_log = int(0)

    vol_cnt_log_float = db_size_log / max_vol_size

    if vol_cnt_log_float <= 1:
        vol_cnt_log_int = int(1)
    else:
        while vol_cnt_log_float > 0:
            vol_cnt_log_int = vol_cnt_log_int + 1
            vol_cnt_log_float = vol_cnt_log_float - 1

    vol_size_log = db_size_log / vol_cnt_log_int

    vol_size_log_int = int(vol_size_log)
    vol_size_log_str = str(vol_size_log_int)
    vol_cnt_log_str = str(vol_cnt_log_int)
    print('volume_size_log: ' + vol_size_log_str)
    print('volume_count_log: ' + vol_cnt_log_str)

def calc_select(args) -> None:
    """DB Backup Volume Calculations"""
    actionbool = args.action
    if actionbool == 'volinfo':
        db_backup_vol_size(args)

def main() -> None:
    """Main function"""

    arguments = [
        Argument("-a", "--action", "Volume Calculation Request")]
    args = parse_args(
        "Oracle DB Backup",
        arguments,
    )

    db_backup_vol_size(args)

if __name__ == "__main__":
    main()
