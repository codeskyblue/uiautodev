import re
from functools import partial
from typing import List, Optional, Tuple
from xml.etree import ElementTree

from uiautodev.exceptions import AndroidDriverException, RequestError
from uiautodev.model import AppInfo, Node, Rect, ShellResponse, WindowSize


def parse_xml(xml_data: str, wsize: WindowSize, display_id: Optional[int] = None) -> Node:
    root = ElementTree.fromstring(xml_data)
    node = parse_xml_element(root, wsize, display_id)
    if node is None:
        raise AndroidDriverException("Failed to parse xml")
    return node


def parse_xml_element(element, wsize: WindowSize, display_id: Optional[int], indexes: List[int] = [0]) -> Optional[Node]:
    """
    Recursively parse an XML element into a dictionary format.
    """
    name = element.tag
    if name == "node":
        name = element.attrib.get("class", "node")
    if display_id is not None:
        elem_display_id = int(element.attrib.get("display-id", display_id))
        if elem_display_id != display_id:
            return

    bounds = None
    rect = None
    # eg: bounds="[883,2222][1008,2265]"
    if "bounds" in element.attrib:
        bounds = element.attrib["bounds"]
        bounds = list(map(int, re.findall(r"\d+", bounds)))
        assert len(bounds) == 4
        rect = Rect(x=bounds[0], y=bounds[1], width=bounds[2] - bounds[0], height=bounds[3] - bounds[1])
        bounds = (
            bounds[0] / wsize.width,
            bounds[1] / wsize.height,
            bounds[2] / wsize.width,
            bounds[3] / wsize.height,
        )
        bounds = map(partial(round, ndigits=4), bounds)
        
    elem = Node(
        key="-".join(map(str, indexes)),
        name=name,
        bounds=bounds,
        rect=rect,
        properties={key: element.attrib[key] for key in element.attrib},
        children=[],
    )

    # Construct xpath for children
    for index, child in enumerate(element):
        child_node = parse_xml_element(child, wsize, display_id, indexes + [index])
        if child_node:
            elem.children.append(child_node)

    return elem
