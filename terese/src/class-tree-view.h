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

#ifndef _CLASS_TREE_VIEW_H_
#define _CLASS_TREE_VIEW_H_
/*
#include <gtkmm.h>
#include <iostream>
#include "box-tree-view.h"

class ClassColumns : public Gtk::TreeModel::ColumnRecord {
	public:

		ClassColumns() {
			add(character);
			add(style);

		}

		Gtk::TreeModelColumn<Glib::ustring> character;
		Gtk::TreeModelColumn<int> style;
};

class ClassComboBox : public Gtk::ComboBox {
	
public:
	ClassComboBox(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
	virtual ~ClassComboBox();
	
	typedef sigc::signal< void, Glib::ustring, int > type_signal_showClassBoxes;
	type_signal_showClassBoxes signal_showClassBoxes();
	
	void show_classes(Glib::RefPtr<Gtk::ListStore> boxlist);

private:
	Glib::RefPtr<Gtk::Builder> builder;
	ClassColumns classColumns;
	BoxColumns boxColumns;
		
	Glib::RefPtr<Gtk::ListStore> m_listStore;

	type_signal_showClassBoxes m_signal_showClassBoxes;
	
	void on_selection_changed();

};
*/
#endif // _CLASS_TREE_VIEW_H_

