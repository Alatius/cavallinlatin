/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * Terese
 * Copyright (C) 2013 Johan Winge <johan.winge@gmail.com>
 * 
 * Terese is free software: you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * Terese is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef _PROJECT_H_
#define _PROJECT_H_

#include <gtkmm.h>
#include <gtkmm/accelmap.h>
#include <iostream>
#include <set>

#include "style-tree-view.h"
#include "page-tree-view.h"
#include "box-tree-view.h"
#include "page.h"
#include "font.h"
//#include "image.h"
#include "common.h"

class Project : public Glib::Markup::Parser
{
public:

	Project();
	virtual ~Project();
	
	// Public accessors
	Glib::RefPtr<Gtk::ListStore> stylesListStore();
	Glib::RefPtr<Gtk::ListStore> pagesListStore();

	Page* getActivePage();
	void setActivePage(Page* page);
	
	Glib::RefPtr<Gtk::ListStore> currentBoxList();
	Glib::RefPtr<Gtk::TextBuffer> currentTextBuffer();
	Glib::RefPtr<Gdk::Pixbuf> currentPixbuf();
	Image* currentImage();
	
	Font* theFont();

	bool isModified();
	void setModified(bool status);
	typedef sigc::signal< void > type_signal_modified;
	type_signal_modified signal_modified();
	
	typedef sigc::signal< void, float, Glib::ustring > type_signal_progress;
	type_signal_progress signal_progress();

	bool isNamed();
	std::string filename();

	Gtk::Menu* formatMenu();

	int styleOfText(const Gtk::TextBuffer::iterator& textit);
	std::set<Unigram> unigramCandidates(Gtk::TextBuffer::iterator textit);
	std::set<Unigram> allBoxUnigrams();
		
	// Methods to modify the project
	void appendStyle(int id, Glib::ustring name, Glib::ustring prefix, Glib::ustring htmltag,
                    Glib::ustring font, Glib::ustring background, Glib::ustring foreground,
	                 Glib::ustring shortcut);
	Page* appendPage(std::string filename);
	void importRTMLFile(Page* page, std::string tifffilename);
	void importBoxFile(Page* page, std::string tifffilename);
	void appendBox(Page* page, Glib::ustring character, int styles, int var, bool deg, int left, int right, int top, int bottom, int correlation = 0);

	void resolveStyleAmbiguities(Page* page);
	
	void createFont();
	
	// Input/Output to file
	void open(const std::string& filename);
	void save();
	void save(const std::string& filename);
	
	void exportBoxFiles();
	void exportOCRopusLines();
	
private:

	// Dummy templates for ListView columns
	StyleColumns styleColumns;
	PagesColumns pagesColumns;
	BoxColumns boxColumns;

	// Basic properties
	bool m_isModified;
	std::string m_fileName;
	std::string m_fileNameParentPath;
	
	Page* m_refActivePage; // The selected and shown page.
	Page* m_refCurrentPage; // The page being loaded, to which boxes should be added etc.
	Page* m_refDummyPage; // An empty page to show when no page is selected.

	// Project data
	Glib::RefPtr<Gtk::TextBuffer::TagTable> m_refTagTable; // Used when creating TextBuffers
	Glib::RefPtr<Gtk::ListStore> m_refStylesListStore;
	Glib::RefPtr<Gtk::ListStore> m_refPagesListStore;

	Font* m_font;
	
	// XML parsing methods
	virtual void on_start_element(Glib::Markup::ParseContext& context,
                                const Glib::ustring&        element_name,
                                const AttributeMap&         attributes);
	
	virtual void on_text(Glib::Markup::ParseContext& context, const Glib::ustring& text);
	
	virtual void on_end_element(Glib::Markup::ParseContext& context,
                                const Glib::ustring& element_name);
	
	// Variables used when parsing XML.
	bool m_isParsingRTML;
	Gtk::TextBuffer::iterator textit;

	// Parse the hackish Tesseract box-file style prefixes
	void parseStylePrefix(Glib::ustring rawchar, Glib::ustring &boxchar, int &styles);
	Glib::ustring generateStylePrefix(int styles);
	
	bool styleToken(Gtk::TreeModel::Children::iterator &rowit,
                   const Gtk::TreeModel::Children::iterator rowend,
                   const int branchdiffs=0, const int laststyle=-1);

	// Signal which is emitted from the method setModified
	// (Connects to Terese::updateWindowTitle())
	type_signal_modified m_signal_modified;

	// Signal emitted when during work in progress
	type_signal_progress m_signal_progress;

	// Callback triggered when any of the various ListViews are modified 
	void on_row_deleted(const Gtk::TreeModel::Path& path);
	void on_row_changed(const Gtk::TreeModel::Path& path, const Gtk::TreeModel::iterator& iter);
	
};

#endif // _PROJECT_H_

