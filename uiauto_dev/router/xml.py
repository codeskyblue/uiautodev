#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 05 2024 16:59:19 by codeskyblue
"""

from fastapi import APIRouter, Form, Response
from lxml import etree
from typing_extensions import Annotated

router = APIRouter()


@router.post("/check/xpath")
def check_xpath(xml: Annotated[str, Form()], xpath: Annotated[str, Form()]) -> Response:
    """Check if the XPath expression is valid"""
    try:
        children = []
        for child in etree.fromstring(xml).xpath(xpath):
            children.append(child)
        if len(children) > 0:
            return Response(content=children[0].tag, media_type="text/plain")
        else:
            return Response(
                content="XPath is valid but not node matches", media_type="text/plain"
            )
    except Exception as e:
        return Response(content=str(e), media_type="text/plain", status_code=400)
