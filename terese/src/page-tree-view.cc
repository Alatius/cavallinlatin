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

#include "page-tree-view.h"
#include "box-tree-view.h"

PageTreeView::PageTreeView (BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
        Gtk::TreeView(cobject),
        builder(refGlade)
{

	append_column("Filename", pagesColumns.name);

	builder->get_widget("menuPagesPopup", menuPagesPopup);
	builder->get_widget("menuPageDelete", menuPageDelete);

	menuPageDelete->signal_activate().connect(sigc::mem_fun(*this, &PageTreeView::on_menuPageDelete_activate));
	get_selection()->signal_changed().connect(sigc::mem_fun(*this, &PageTreeView::on_selection_changed));
	get_selection()->set_mode(Gtk::SELECTION_BROWSE);
		
#ifndef GLIBMM_DEFAULT_SIGNAL_HANDLERS_ENABLED
	signal_button_press_event()
		.connect(sigc::mem_fun(*this, &PageTreeView::on_button_press_event), false);
#endif
}

PageTreeView::~PageTreeView() {
}

PageTreeView::type_signal_setActivePage PageTreeView::signal_setActivePage() {
	return m_signal_setActivePage;
}

void PageTreeView::set_model(Glib::RefPtr<Gtk::ListStore> model) {
	m_listStore=model;
	Gtk::TreeView::set_model(m_listStore);
}

Glib::RefPtr<Gtk::ListStore> PageTreeView::get_model() {
	return m_listStore;
}

bool PageTreeView::on_button_press_event(GdkEventButton* event) {

	bool return_value = false;

	return_value = TreeView::on_button_press_event(event);

	if( (event->type == GDK_BUTTON_PRESS) && (event->button == 3) ) {
		menuPagesPopup->popup(event->button, event->time);
	}
	
	return return_value;
}

void PageTreeView::on_menuPageDelete_activate() {
	Glib::RefPtr<Gtk::TreeView::Selection> refSelection = get_selection();
	if(refSelection) {
		Gtk::TreeModel::iterator iter = refSelection->get_selected();
		if (iter) {
			m_signal_setActivePage.emit(NULL);
			delete (*iter)[pagesColumns.page];
			m_listStore->erase(iter);
		}
	}
}

void PageTreeView::on_selection_changed() {
	Glib::RefPtr<Gtk::TreeView::Selection> refSelection = get_selection();
	if (refSelection) {
		Gtk::TreeModel::iterator iter = refSelection->get_selected();
		if (iter) {
			m_signal_setActivePage.emit((*iter)[pagesColumns.page]);
		}
	}
}

