#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 14:20:15 by codeskyblue
"""

import uvicorn


def main():
    uvicorn.run("appinspector.app:app", host="0.0.0.0", port=20242)


if __name__ == "__main__":
    main()