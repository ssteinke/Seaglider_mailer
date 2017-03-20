#! /usr/bin/env python
"""Extension for Seaglider basestation
Author: Sebastian Steinke, 19.03.2017
"""
import Base
import sys


def main(base_opts=None, sg_calib_file_name=None, dive_nc_file_names=None,
         nc_files_created=None, processed_other_files=None,
         known_mailer_tags=None, known_ftp_tags=None):
    """Basestation extension script invoked at glider logout time

    Returns:
        0 for success (although there may have been individual errors in
            file processing).
        Non-zero for critical problems.

    Raises:
        Any exceptions raised are considered critical errors and not expected
    """
    ret_val = 0
    Base.send_email(base_opts, 213, 'sebastian.steinke@kaust.edu.sa',
                    'Extension test', 'body')
    return ret_val


if __name__ == "__main__":

    retval = 1
    retval = main()
    sys.exit(retval)
