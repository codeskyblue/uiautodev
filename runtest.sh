#!/bin/bash
#

set -e

poetry run uiauto.dev android --help
poetry run uiauto.dev appium --help
poetry run uiauto.dev ios --help
poetry run uiauto.dev version
poetry run uiauto.dev server --help
