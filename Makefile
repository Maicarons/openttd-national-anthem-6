PKG     = openttd-national-anthem
VERSION = 1.0
VOL     = 6
DIR     = $(PKG)-$(VOL)-$(VERSION)
TGZ     = $(DIR).tar.gz

all:
	python scripts/build_package.py

clean:
	rm -rf dist

.PHONY: all clean
