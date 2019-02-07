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

#include "class-tree-view.h"
/*
ClassComboBox::ClassComboBox (BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
        Gtk::ComboBox(cobject),
        builder(refGlade)
{

	append_column("Styles", classColumns.style);
	append_column("Character", classColumns.character);

	get_selection()->signal_changed().connect(sigc::mem_fun(*this, &ClassComboBox::on_selection_changed));

#ifndef GLIBMM_DEFAULT_SIGNAL_HANDLERS_ENABLED
	signal_button_press_event()
		.connect(sigc::mem_fun(*this, &ClassComboBox::on_button_press_event), false);
#endif
}

ClassComboBox::~ClassComboBox() {
}

ClassComboBox::type_signal_showClassBoxes ClassComboBox::signal_showClassBoxes() {
	return m_signal_showClassBoxes;
}

void ClassComboBox::show_classes(Glib::RefPtr<Gtk::ListStore> boxlist) {
	m_listStore = Gtk::ListStore::create(classColumns);
	
	Gtk::TreeModel::Children::iterator boxrowit;
	for (boxrowit=boxlist->children().begin();
	     boxrowit != boxlist->children().end(); ++boxrowit)
	{
		Glib::ustring character = (*boxrowit)[boxColumns.character];
		if (character !=" " && character !="\\n") {
			int style = (*boxrowit)[boxColumns.style];
			Gtk::TreeModel::Children::iterator classrowit;
			bool isinlist = false;
			for (classrowit=m_listStore->children().begin();
			     classrowit != m_listStore->children().end(); ++classrowit)
			{
				if ((*classrowit)[classColumns.character] == character &&
				    (*classrowit)[classColumns.style] == style) {
					isinlist = true;
					break;
				}
			}
			if (!isinlist) {
				Gtk::TreeModel::Row row = *(m_listStore->append());
				row[classColumns.character] = character;
				row[classColumns.style] = style;
			}
		}
	}

	m_listStore->set_sort_column(classColumns.character, Gtk::SORT_ASCENDING);
	m_listStore->set_sort_column(classColumns.style, Gtk::SORT_ASCENDING);
	set_model(m_listStore);
}

void ClassComboBox::on_selection_changed() {
	Glib::RefPtr<Gtk::TreeView::Selection> refSelection = get_selection();
	if(refSelection) {
		Gtk::TreeModel::iterator iter = refSelection->get_selected();
		if (iter) {
			m_signal_showClassBoxes.emit((*iter)[classColumns.character],
			                               (*iter)[classColumns.style]);
		}
	}
}

*/