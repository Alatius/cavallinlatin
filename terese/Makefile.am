## Process this file with automake to produce Makefile.in
## Created by Anjuta

SUBDIRS = src 

teresedocdir = ${prefix}/doc/terese
teresedoc_DATA = \
	README\
	COPYING\
	AUTHORS\
	ChangeLog\
	INSTALL\
	NEWS

AM_CXXFLAGS = -std=c++11

EXTRA_DIST = $(teresedoc_DATA)


# Remove doc directory on uninstall
uninstall-local:
	-rm -r $(teresedocdir)
