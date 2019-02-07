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

#include "box-tree-view.h"

BoxTreeView::BoxTreeView (BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
        Gtk::TreeView(cobject),
        builder(refGlade)
{

	//Add the TreeView's view columns:
	append_column("Styl", boxColumns.style);
	append_column("Chr", boxColumns.character);
	append_column("Var", boxColumns.variant);
	append_column("Corr", boxColumns.correlation);
	append_column("Deg", boxColumns.degenerate);
	append_column("Lft", boxColumns.left);
	//append_column("Rgt", boxColumns.right);
	append_column("Top", boxColumns.top);
	//append_column("Bot", boxColumns.bottom);
/*
	builder->get_widget("menuBoxesPopup", menuBoxesPopup);
	builder->get_widget("menuBoxDelete", menuBoxDelete);
	builder->get_widget("menuBoxMerge", menuBoxMerge);
	menuBoxDelete->signal_activate().connect(sigc::mem_fun(*this, &BoxTreeView::on_menuBoxDelete));
	menuBoxMerge->signal_activate().connect(sigc::mem_fun(*this, &BoxTreeView::on_menuBoxMerge));
	*/
	get_selection()->signal_changed().connect(sigc::mem_fun(*this, &BoxTreeView::on_selection_changed));
	get_selection()->set_mode(Gtk::SELECTION_MULTIPLE);

#ifndef GLIBMM_DEFAULT_SIGNAL_HANDLERS_ENABLED
	signal_button_press_event()
		.connect(sigc::mem_fun(*this, &BoxTreeView::on_button_press_event), false);
#endif
	
	m_listStoreClipBoard = Gtk::ListStore::create(boxColumns);
}

BoxTreeView::~BoxTreeView() {
}

BoxTreeView::type_signal_centerBox BoxTreeView::signal_centerBox() {
	return m_signal_centerBox;
}

BoxTreeView::type_signal_boxChanged BoxTreeView::signal_boxChanged() {
	return m_signal_boxChanged;
}

void BoxTreeView::set_model(Glib::RefPtr<Gtk::ListStore> model, Glib::RefPtr<Gdk::Pixbuf> pixbuf) {

	// Remove icons from the boxes, to avoid clogging up memory:
	if (m_listStore) {
		Glib::RefPtr<Gdk::Pixbuf> tempPixbuf;
		Gtk::TreeModel::Children::iterator rowit;
		for (rowit = m_listStore->children().begin();
		     rowit != m_listStore->children().end(); ++rowit)
		{
			(*rowit)[boxColumns.icon] = tempPixbuf;
			// Ugly. What I really want is
			// (*rowit)[boxColumns.icon].reset();
			// but that doesn't work... (Help?)
		}
	}

	remove_all_columns();

	m_listStore=model;
	Gtk::TreeView::set_model(m_listStore);

	// Editable columns must be added after set_model(!)
	append_column_editable("Styl", boxColumns.style);
	append_column_editable("Chr", boxColumns.character);
	append_column_editable("Var", boxColumns.variant);
	append_column("Corr", boxColumns.correlation);
	append_column_editable("Deg", boxColumns.degenerate);
	append_column("Lft", boxColumns.left);
	//append_column("Rgt", boxColumns.right);
	append_column("Top", boxColumns.top);
	//append_column("Bot", boxColumns.bottom);

	m_refPixbuf = pixbuf;

	// Add new icons to the boxrows:
	if (m_listStore) {
		Gtk::TreeModel::Children::iterator rowit;
		for (rowit = m_listStore->children().begin();
		     rowit != m_listStore->children().end(); ++rowit)
		{
			updateBoxIcon(rowit);
		}
	}

}

void BoxTreeView::updateBoxIcon(Gtk::TreeModel::Children::iterator rowit) {
	Glib::ustring character = (*rowit)[boxColumns.character];
	int left = (*rowit)[boxColumns.left];
	int right = (*rowit)[boxColumns.right];
	int top = (*rowit)[boxColumns.top];
	int bottom = (*rowit)[boxColumns.bottom];

	if (character != "\\n" && character != " ") {
		if (left >=0 && top>=0 &&
		    right < m_refPixbuf->get_width() && bottom < m_refPixbuf->get_height() &&
		    left < right && top < bottom) {
			(*rowit)[boxColumns.icon] =
				Gdk::Pixbuf::create_subpixbuf(m_refPixbuf, left, top, right-left, bottom-top);
		} else {
			std::cout << "Warning, strange box: " << character << " " << left << " " << right << " " << top << " " << bottom << std::endl;
		}
	}
	
}

bool BoxTreeView::on_button_press_event(GdkEventButton* event) {

	bool return_value = false;

	//Call base class, to allow normal handling,
	//such as allowing the row to be selected by the right-click:
	return_value = TreeView::on_button_press_event(event);

	//Then do our custom stuff:
	if( (event->type == GDK_BUTTON_PRESS) && (event->button == 3) ) {
		//menuBoxesPopup->popup(event->button, event->time);
	}

	return return_value;
}

void BoxTreeView::on_menuBoxCut() {
	on_menuBoxCopy();
	on_menuBoxDelete();
}

void BoxTreeView::on_menuBoxCopy() {
	m_listStoreClipBoard->clear();
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
   std::vector<Gtk::TreeRowReference> rowrefs;
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
      rowrefs.push_back(Gtk::TreeRowReference(m_listStore, *pathit));
	}
   for (std::vector<Gtk::TreeRowReference>::const_iterator rowrefit = rowrefs.begin(); rowrefit!=rowrefs.end(); ++rowrefit) {
		Gtk::TreeIter iter = m_listStore->get_iter((*rowrefit).get_path());
		if (iter) {
			Glib::ustring character;
			int left, right, top, bottom, style, variant, correlation;
			bool deg;
			character = (*iter)[boxColumns.character];
			left = (*iter)[boxColumns.left];
			right = (*iter)[boxColumns.right];
			top = (*iter)[boxColumns.top];
			bottom = (*iter)[boxColumns.bottom];
			style = (*iter)[boxColumns.style];
			variant = (*iter)[boxColumns.variant];
			correlation = (*iter)[boxColumns.correlation];
			deg = (*iter)[boxColumns.degenerate];
			Gtk::TreeModel::Row boxrow = *(m_listStoreClipBoard->append());
			boxrow[boxColumns.character] = character;
			boxrow[boxColumns.style] = style;
			boxrow[boxColumns.variant] = variant;
			boxrow[boxColumns.degenerate] = deg;
			boxrow[boxColumns.correlation] = correlation;
			boxrow[boxColumns.left] = left;
			boxrow[boxColumns.right] = right;
			boxrow[boxColumns.top] = top;
			boxrow[boxColumns.bottom] = bottom;
		}
	}
}

void BoxTreeView::on_menuBoxPaste() {
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
   std::vector<Gtk::TreeRowReference> rowrefs;
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
      rowrefs.push_back(Gtk::TreeRowReference(m_listStore, *pathit));
	}
   for (std::vector<Gtk::TreeRowReference>::const_iterator rowrefit = rowrefs.begin(); rowrefit!=rowrefs.end(); ++rowrefit) {
		Gtk::TreeIter iter = m_listStore->get_iter((*rowrefit).get_path());
		if (iter) {
			for (Gtk::TreeModel::Children::iterator clipit=m_listStoreClipBoard->children().begin();
              clipit != m_listStoreClipBoard->children().end(); clipit++) {
				Glib::ustring character;
				int left, right, top, bottom, style, variant, correlation;
				bool deg;
				character = (*clipit)[boxColumns.character];
				left = (*clipit)[boxColumns.left];
				right = (*clipit)[boxColumns.right];
				top = (*clipit)[boxColumns.top];
				bottom = (*clipit)[boxColumns.bottom];
				style = (*clipit)[boxColumns.style];
				variant = (*clipit)[boxColumns.variant];
				correlation = (*clipit)[boxColumns.correlation];
				deg = (*clipit)[boxColumns.degenerate];
				iter = m_listStore->insert_after(iter);
				(*iter)[boxColumns.character] = character;
				(*iter)[boxColumns.style] = style;
				(*iter)[boxColumns.variant] = variant;
				(*iter)[boxColumns.degenerate] = deg;
				(*iter)[boxColumns.correlation] = correlation;
				(*iter)[boxColumns.left] = left;
				(*iter)[boxColumns.right] = right;
				(*iter)[boxColumns.top] = top;
				(*iter)[boxColumns.bottom] = bottom;
			}
			m_signal_boxChanged.emit();
			return;
		}
	}
}

void BoxTreeView::on_menuBoxDelete() {
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
   std::vector<Gtk::TreeRowReference> rowrefs;
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
      rowrefs.push_back(Gtk::TreeRowReference(m_listStore, *pathit));
	}
   for (std::vector<Gtk::TreeRowReference>::const_iterator rowrefit = rowrefs.begin(); rowrefit!=rowrefs.end(); ++rowrefit) {
		Gtk::TreeIter iter = m_listStore->get_iter((*rowrefit).get_path());
		if (iter) {
			m_listStore->erase(iter);
		}
	}
	m_signal_boxChanged.emit();
}

void BoxTreeView::on_menuBoxMerge(bool mergefollowing) {
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
   std::vector<Gtk::TreeRowReference> rowrefs, toselectrefs;
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
      rowrefs.push_back(Gtk::TreeRowReference(m_listStore, *pathit));
	}
   for (std::vector<Gtk::TreeRowReference>::const_iterator rowrefit = rowrefs.begin(); rowrefit!=rowrefs.end(); ++rowrefit) {
		Gtk::TreeIter iter = m_listStore->get_iter((*rowrefit).get_path());
		if (iter) {
			Glib::ustring character;
			int left, right, top, bottom, style, variant;
			character = (*iter)[boxColumns.character];
			left = (*iter)[boxColumns.left];
			right = (*iter)[boxColumns.right];
			top = (*iter)[boxColumns.top];
			bottom = (*iter)[boxColumns.bottom];
			style = (*iter)[boxColumns.style];
			variant = (*iter)[boxColumns.variant];
			if (mergefollowing) {
				iter++;
				if (iter == m_listStore->children().end()) {
					continue;
				}
			} else {
				if (iter == m_listStore->children().begin()) {
					continue;
				}
				iter--;
			}
			if ( character!=" " && character!="\\n" &&
			     (*iter)[boxColumns.character]!=" " && (*iter)[boxColumns.character]!="\\n") {
				if ((*iter)[boxColumns.character] == "??") {
					(*iter)[boxColumns.character] = character;
				} else {
					if (mergefollowing) {
						(*iter)[boxColumns.character] = character+(*iter)[boxColumns.character];
					} else {
						(*iter)[boxColumns.character] = (*iter)[boxColumns.character]+character;
					}
				}
				if ((*iter)[boxColumns.left] > left)
					(*iter)[boxColumns.left] = left;
				if ((*iter)[boxColumns.right] < right)
					(*iter)[boxColumns.right] = right;
				if ((*iter)[boxColumns.top] > top)
					(*iter)[boxColumns.top] = top;
				if ((*iter)[boxColumns.bottom] < bottom)
					(*iter)[boxColumns.bottom] = bottom;
				(*iter)[boxColumns.style] = style;
				(*iter)[boxColumns.variant] = variant;
				updateBoxIcon(iter);
   			toselectrefs.push_back(Gtk::TreeRowReference(m_listStore, m_listStore->get_path(iter)));
				if (mergefollowing) {
					iter--;
				} else {
					iter++;
				}
				m_listStore->erase(iter);
			}
		}
	}
	get_selection()->unselect_all();
   for (std::vector<Gtk::TreeRowReference>::const_iterator rowrefit = toselectrefs.begin(); rowrefit!=toselectrefs.end(); ++rowrefit) {
		get_selection()->select(rowrefit->get_path());
	}
	m_signal_boxChanged.emit();
}

void BoxTreeView::on_menuBoxSplit() {
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
   std::vector<Gtk::TreeRowReference> rowrefs;
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
      rowrefs.push_back(Gtk::TreeRowReference(m_listStore, *pathit));
	}
   for (std::vector<Gtk::TreeRowReference>::const_iterator rowrefit = rowrefs.begin(); rowrefit!=rowrefs.end(); ++rowrefit) {
		Gtk::TreeIter iter = m_listStore->get_iter((*rowrefit).get_path());
		if (iter) {
			Glib::ustring character = (*iter)[boxColumns.character];
			if (character!=" " && character!="\\n") {
				int left = (*iter)[boxColumns.left];
				int right = (*iter)[boxColumns.right];
				int top = (*iter)[boxColumns.top];
				int bottom = (*iter)[boxColumns.bottom];
				int style = (*iter)[boxColumns.style];

				// A more sophisticated splitting should look at the actual pixels...
				left = left+(right-left)/std::max(2,(int)character.length()); // That is, new left for the right box.
				
				(*iter)[boxColumns.character] = character.substr(0,1);
				(*iter)[boxColumns.right] = left;
				updateBoxIcon(iter);
					
				iter = m_listStore->insert_after(iter);

				character = character.substr(1,character.length()-1);
				if (character == "")
					character = "??";
				(*iter)[boxColumns.character] = character;
				(*iter)[boxColumns.left] = left;
				(*iter)[boxColumns.right] = right;
				(*iter)[boxColumns.top] = top;
				(*iter)[boxColumns.bottom] = bottom;
				(*iter)[boxColumns.style] = style;
				updateBoxIcon(iter);

			}
		}
	}
	m_signal_boxChanged.emit();
}

void BoxTreeView::on_menuBoxResize(int leftdiff, int rightdiff, int topdiff, int botdiff) {
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
		Gtk::TreeIter iter = m_listStore->get_iter(*pathit);
		if (iter) {
			(*iter)[boxColumns.left] = (*iter)[boxColumns.left]+leftdiff;
			(*iter)[boxColumns.right] = (*iter)[boxColumns.right]+rightdiff;
			(*iter)[boxColumns.top] = (*iter)[boxColumns.top]+topdiff;
			(*iter)[boxColumns.bottom] = (*iter)[boxColumns.bottom]+botdiff;
			updateBoxIcon(iter);
		}
	}
	m_signal_boxChanged.emit();
}

void BoxTreeView::on_selection_changed() {
	int left, right, top, bottom;
	std::vector<Gtk::TreePath> paths = get_selection()->get_selected_rows();
	if (!paths.empty()) {
		Gtk::TreeIter iter = m_listStore->get_iter(paths.back());
		if (iter) {
			left=(*iter)[boxColumns.left];
			right=(*iter)[boxColumns.right];
			top=(*iter)[boxColumns.top];
			bottom=(*iter)[boxColumns.bottom];
			m_signal_centerBox.emit(left, right, top, bottom);
		}
	}
}
