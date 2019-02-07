## Process this file with automake to produce Makefile.in

## Created by Anjuta


uidir = $(pkgdatadir)/ui
ui_DATA = terese.ui


AM_CPPFLAGS = \
	-DPACKAGE_LOCALE_DIR=\""$(localedir)"\" \
	-DPACKAGE_SRC_DIR=\""$(srcdir). \
	$(gtkmm-3.0_CFLAGS)"\" \
	-DPACKAGE_DATA_DIR=\""$(pkgdatadir)"\" \
	$(TERESE_CFLAGS)

AM_CFLAGS =\
	 -Wall\
	 -g

bin_PROGRAMS = terese

terese_SOURCES = \
	main.cc \
	terese.cc \
	terese.h \
	box-tree-view.cc \
	box-tree-view.h \
	page-tree-view.cc \
	page-tree-view.h \
	project.cc \
	project.h \
	image.cc \
	image.h \
	box.cc \
	box.h \
	matrix.h \
	custom-drawing-area.cc \
	custom-drawing-area.h \
	style-tree-view.cc \
	style-tree-view.h \
	class-tree-view.cc \
	class-tree-view.h \
	page.cc \
	page.h \
	font.cc \
	font.h \
	unigram.cc \
	unigram.h \
	aliases-dialog.cc \
	aliases-dialog.h \
	common.h \
	font-box.cc \
	font-box.h \
	clusterer.cc \
	clusterer.h

terese_LDFLAGS = 

terese_LDADD = $(TERESE_LIBS) \
	$(gtkmm-3.0_LIBS)


EXTRA_DIST = $(ui_DATA)

# Remove ui directory on uninstall
uninstall-local:
	-rm -r $(uidir)
	-rm -r $(pkgdatadir)

