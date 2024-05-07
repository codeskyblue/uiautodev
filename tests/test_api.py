#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Mon Mar 04 2024 14:00:52 by codeskyblue
"""

from fastapi.testclient import TestClient

from uiautodev.app import app

client = TestClient(app)

def test_api_info():
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    for k in ['version', 'description', 'platform', 'code_language', 'cwd']:
        assert k in data


def test_mock_list():
    response = client.get("/api/mock/list")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for item in data:
        assert 'serial' in item
        assert 'model' in item
        assert 'name' in item


def test_mock_screenshot():
    response = client.get("/api/mock/mock-serial/screenshot/0")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/jpeg'


def test_mock_hierarchy():
    response = client.get("/api/mock/mock-serial/hierarchy")
    assert response.status_code == 200
    data = response.json()
    assert 'key' in data
    assert 'name' in data
    assert 'bounds' in data
    assert 'children' in data