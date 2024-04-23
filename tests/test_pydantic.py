#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Apr 14 2024 22:32:43 by codeskyblue
"""

from pydantic import BaseModel


class MyBool(BaseModel):
    value: bool


def test_evalute_bool():
    b = MyBool.model_validate({"value": "true"})
    assert b.value == True

    # b.model_
    # dump_result = b.model_dump()
    # print(dump_result)