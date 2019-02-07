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

#ifndef _PAGE_TREE_VIEW_H_
#define _PAGE_TREE_VIEW_H_

#include <gtkmm.h>
#include <iostream>
#include "image.h"
#include "page.h"

class PagesColumns : public Gtk::TreeModel::ColumnRecord {
	public:

		PagesColumns() {
			add(fullname);
			add(name);
			add(page);
		}

		Gtk::TreeModelColumn<Glib::ustring> fullname;
		Gtk::TreeModelColumn<Glib::ustring> name;
		Gtk::TreeModelColumn<Page*> page;
};

class PageTreeView : public Gtk::TreeView {
	
public:
	PageTreeView(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
	virtual ~PageTreeView();

   void set_model(Glib::RefPtr<Gtk::ListStore> model);
	Glib::RefPtr<Gtk::ListStore> get_model();
	
	typedef sigc::signal< void, Page* > type_signal_setActivePage;
	type_signal_setActivePage signal_setActivePage();

private:

	Glib::RefPtr<Gtk::Builder> builder;
	
	PagesColumns pagesColumns;
	Glib::RefPtr<Gtk::ListStore> m_listStore;
		
	Gtk::Menu *menuPagesPopup;
	Gtk::MenuItem *menuPageDelete;
	
	// Override signal handler (for popup)
	virtual bool on_button_press_event(GdkEventButton *ev);

	void on_menuPageDelete_activate();
   void on_selection_changed();

	// Signal
	type_signal_setActivePage m_signal_setActivePage;

};

#endif // _PAGE_TREE_VIEW_H_

