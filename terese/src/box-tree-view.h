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

#ifndef _BOX_TREE_VIEW_H_
#define _BOX_TREE_VIEW_H_

#include <gtkmm.h>
#include <iostream>

class BoxColumns : public Gtk::TreeModel::ColumnRecord {
	public:

		BoxColumns() {
			add(character);
			add(style);
			add(variant);
			add(degenerate);
			add(correlation);
			add(left);
			add(right);
			add(top);
			add(bottom);
			add(icon);
			add(ishelped);
		}

		Gtk::TreeModelColumn<Glib::ustring> character;
		Gtk::TreeModelColumn<int> style;
		Gtk::TreeModelColumn<int> variant;
		Gtk::TreeModelColumn<bool> degenerate;
		Gtk::TreeModelColumn<int> correlation;
		Gtk::TreeModelColumn<int> left;
		Gtk::TreeModelColumn<int> right;
		Gtk::TreeModelColumn<int> top;
		Gtk::TreeModelColumn<int> bottom;
		Gtk::TreeModelColumn< Glib::RefPtr<Gdk::Pixbuf> > icon;
		Gtk::TreeModelColumn<bool> ishelped;
};

class BoxTreeView : public Gtk::TreeView {
	
public:
	BoxTreeView(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
	virtual ~BoxTreeView();

	void set_model(Glib::RefPtr<Gtk::ListStore> model, Glib::RefPtr<Gdk::Pixbuf> pixbuf);

	typedef sigc::signal< void, int, int, int, int > type_signal_centerBox;
	type_signal_centerBox signal_centerBox();
	
	typedef sigc::signal< void > type_signal_boxChanged;
	type_signal_boxChanged signal_boxChanged();

	//Glib::RefPtr<Gtk::AccelGroup> m_refAccelGroup;
	void on_menuBoxMerge(bool mergefollowing);
	void on_menuBoxCut();
	void on_menuBoxCopy();
	void on_menuBoxPaste();
	void on_menuBoxDelete();
	void on_menuBoxSplit();
	void on_menuBoxResize(int leftdiff, int rightdiff, int topdiff, int botdiff);

private:
	Glib::RefPtr<Gtk::Builder> builder;

	type_signal_centerBox m_signal_centerBox;
	type_signal_boxChanged m_signal_boxChanged;

		
	// Override Signal handler:
	// Alternatively, use signal_button_press_event().connect_notify()
	virtual bool on_button_press_event(GdkEventButton *ev);

	void on_selection_changed();

	BoxColumns boxColumns;

	//The Tree model:
	Glib::RefPtr<Gtk::ListStore> m_listStore;
	// The clip board:
	Glib::RefPtr<Gtk::ListStore> m_listStoreClipBoard;

	
	Glib::RefPtr<Gdk::Pixbuf> m_refPixbuf; // Used for generating icons.
	void updateBoxIcon(Gtk::TreeModel::Children::iterator rowit);
	
/*
	//Gtk::Menu m_Menu_Popup;
	
	Gtk::Menu *menuBoxesPopup;
	Gtk::MenuItem *menuBoxDelete;
	Gtk::MenuItem *menuBoxMerge;
		*/
};

#endif // _BOX_TREE_VIEW_H_

