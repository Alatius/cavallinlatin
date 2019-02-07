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

#ifndef _STYLE_TREE_VIEW_H_
#define _STYLE_TREE_VIEW_H_

#include <gtkmm.h>

class StyleColumns : public Gtk::TreeModel::ColumnRecord {
	public:
		StyleColumns() {
			add(id);
			add(name);
			add(prefix);
			add(htmltag);
			add(font);
			add(background);
			add(foreground);
			add(shortcut);
			add(texttag);
			add(textstartmark);
		}
		Gtk::TreeModelColumn<int> id;
		Gtk::TreeModelColumn<Glib::ustring> name;
		Gtk::TreeModelColumn<Glib::ustring> prefix;
		Gtk::TreeModelColumn<Glib::ustring> htmltag;
		Gtk::TreeModelColumn<Glib::ustring> font;
		Gtk::TreeModelColumn<Glib::ustring> background;
		Gtk::TreeModelColumn<Glib::ustring> foreground;
		Gtk::TreeModelColumn<Glib::ustring> shortcut;
		Gtk::TreeModelColumn< Glib::RefPtr<Gtk::TextBuffer::Tag> > texttag;
		Gtk::TreeModelColumn< Glib::RefPtr<Gtk::TextBuffer::Mark> > textstartmark;
};

class StyleTreeView : public Gtk::TreeView
{
public:
	StyleTreeView(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
	virtual ~StyleTreeView();

private:
	Glib::RefPtr<Gtk::Builder> builder;
	StyleColumns styleColumns;
	Glib::RefPtr<Gtk::ListStore> m_listStore;
		
};

#endif // _STYLE_TREE_VIEW_H_

