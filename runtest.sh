#!/bin/bash
#

set -e

poetry run appinspector android --help
poetry run appinspector appium --help
poetry run appinspector ios --help
poetry run appinspector version
poetry run appinspector server --help
