#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Thu May 09 2024 11:33:17 by codeskyblue
"""


import locale


def is_chinese_language() -> bool:
    language_code, _ = locale.getdefaultlocale()
    
    # Check if the language code starts with 'zh' (Chinese)
    if language_code and language_code.startswith('zh'):
        return True
    else:
        return False
    
    
def get_webpage_url() -> str:
    web_url = "https://uiauto.dev"
    if is_chinese_language():
        web_url = "https://uiauto.devsleep.com"
    return web_url