#!/usr/bin/env python

import sys

template = """[Unit]
Description={HOST} site
Requires={HOST}.api.service\
 {HOST}.renderer.service\
 {HOST}.markup_renderer.service

After=multi-user.target
"""

if __name__ == '__main__':
    print template.format(**{
        'HOST': sys.argv[1],
    })
