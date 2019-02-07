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

#include "style-tree-view.h"

StyleTreeView::StyleTreeView (BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
        Gtk::TreeView(cobject),
        builder(refGlade)
{
	append_column("ID", styleColumns.name);
	append_column("Name", styleColumns.name);
	append_column("Prefix", styleColumns.prefix);
	append_column("Tag", styleColumns.htmltag);
	append_column("Shortcut", styleColumns.shortcut);
}

StyleTreeView::~StyleTreeView() {
}
