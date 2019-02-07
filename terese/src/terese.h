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

#ifndef _TERESE_H_
#define _TERESE_H_

#include <gtkmm.h>
#include <iostream>
#include <fftw3.h>

#include "project.h"
#include "style-tree-view.h"
#include "page-tree-view.h"
#include "box-tree-view.h"
#include "custom-drawing-area.h"
//#include "class-tree-view.h"
#include "aliases-dialog.h"
#include "clusterer.h"

class Terese : public Gtk::Window {
	
protected:
	Glib::RefPtr<Gtk::Builder> builder;
	PageTreeView *treeviewPages;
	BoxTreeView *treeviewBoxes;
	CustomDrawingArea *drawingArea;
	Gtk::ComboBox *comboboxClasses;
	Gtk::ComboBoxText *comboboxSorting;
	Gtk::TextView *textView;
	Gtk::ProgressBar *progressbar;
	Gtk::IconView *iconviewBoxes;
	Gtk::Entry *entryNewStyle;
	Gtk::Entry *entryNewChar;
	Gtk::Entry *entryNewVariant;
	Gtk::Button *buttonReclassify;

	AliasesDialog *dialogAliases;
	
	Glib::RefPtr<Gtk::TreeModelFilter> modelFilter;
	Glib::RefPtr<Gtk::TreeModelSort> modelFilterSorted;
	
	Gtk::MenuItem *menuNew;
	Gtk::MenuItem *menuOpen;
	Gtk::MenuItem *menuSave;
	Gtk::MenuItem *menuSaveAs;
	Gtk::MenuItem *menuAddPages;
	Gtk::MenuItem *menuExportBox;
	Gtk::MenuItem *menuExportOCRopusLines;
	Gtk::MenuItem *menuExportOverlays;
	Gtk::MenuItem *menuQuit;
	Gtk::MenuItem *menuFormat;
	Gtk::MenuItem *menuZoom100;
	Gtk::MenuItem *menuZoom50;
	Gtk::MenuItem *menuZoom33;
	Gtk::MenuItem *menuZoom25;
	Gtk::MenuItem *menuShowOriginal;
	Gtk::MenuItem *menuShowMaskOverlay;
	Gtk::MenuItem *menuShowMaskOnly;

	Gtk::MenuItem *menuitemCutBox;
	Gtk::MenuItem *menuitemCopyBox;
	Gtk::MenuItem *menuitemPasteBox;
	Gtk::MenuItem *menuitemDeleteBox;
	Gtk::MenuItem *menuitemMergeFollowingBox;
	Gtk::MenuItem *menuitemMergePrecedingBox;
	Gtk::MenuItem *menuitemSplitBox;
	Gtk::MenuItem *menuitemBoxEnlargeLeft;
	Gtk::MenuItem *menuitemBoxEnlargeRight;
	Gtk::MenuItem *menuitemBoxEnlargeTop;
	Gtk::MenuItem *menuitemBoxEnlargeBottom;
	Gtk::MenuItem *menuitemBoxDecreaseLeft;
	Gtk::MenuItem *menuitemBoxDecreaseRight;
	Gtk::MenuItem *menuitemBoxDecreaseTop;
	Gtk::MenuItem *menuitemBoxDecreaseBottom;

	Gtk::MenuItem *menuitemTextFromBoxes;
	
	Gtk::MenuItem *menuitemEditAliases;
	Gtk::MenuItem *menuitemCreateFont;
	Gtk::MenuItem *menuitemReadjustBoxes;
	Gtk::MenuItem *menuitemReconsiderBoxes;
	Gtk::MenuItem *menuitemOCR;
	Gtk::MenuItem *menuitemMapText;
	Gtk::MenuItem *menuitemSegmentate;
	Gtk::MenuItem *menuitemClusterBoxes;
	Gtk::MenuItem *menuitemBatch;
	Gtk::MenuItem *menuitemBatch2;
	
	Project *project;
	
public:
	Terese(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);

protected:

	//void setModified(bool status=true);
	
	void buildFormatMenu(Glib::RefPtr<Gtk::ListStore> styles);
	
	// Called from the format menu
	void toggle_tag(int style, Glib::RefPtr<Gtk::TextBuffer::Tag> refTag);

   //signal handlers
	void on_menuNew_activate();
	void on_menuOpen_activate();
	void on_menuSave_activate();
	void on_menuSaveAs_activate();
	void on_menuAddPages_activate();
	void on_menuExportBox_activate();
	void on_menuExportOCRopusLines_activate();
	void on_menuExportOverlays_activate();
	void on_menuQuit_activate();
	bool on_delete_event(GdkEventAny* event);
	void on_buttonReclassify_clicked();
	void on_iconselection_changed();
	void on_menuTextFromBoxes_activate();
	void on_menuEditAliases_activate();
	void on_menuCreateFont_activate();
	void on_menuReadjustBoxes_activate();
	void on_menuReconsiderBoxes_activate();
	void on_menuOCR_activate();
	void on_menuMapText_activate();
	void on_menuShowOriginal_activate();
	void on_menuShowMask_activate(bool overlay);
	void on_menuSegment_activate();
	void on_menuClusterBoxes_activate();
	void on_menuBatch_activate();
	void on_menuBatch2_activate();
	
	// other methods
	void createNewProject(const std::string& filename);
	bool mayDiscard();
	void updateWindowTitle();
	void updateProgress(float progress, Glib::ustring message);
	void showPage(Page* page);
	void selectBox(int xpos, int ypos);
	void relocateBox(int xpos, int ypos);
	void readjustBoxes(bool onlyselected);
	void reconsiderBoxes();
	void listClasses(Glib::RefPtr<Gtk::ListStore> boxlist);
	void showClassBoxes();
	void appendNewBox(int left, int right, int top, int bot, Glib::ustring chr = "??", int style = 0, int var = 0, bool deg = false);
	bool filterBoxes(const Gtk::TreeModel::const_iterator& iter, Glib::ustring character, int style, int var);
	void on_boxicon_activated(const Gtk::TreeModel::Path& path);
	Image getMask(Image* img);
	void straightenLines();
	
	// Dummy templates for ListView columns
	StyleColumns styleColumns;
	PagesColumns pagesColumns;
	BoxColumns boxColumns;

};

#endif // _TERESE_H_

