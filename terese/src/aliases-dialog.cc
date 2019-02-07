/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * aliases-dialog.cc
 * Copyright (C) 2014 Johan Winge <johan.winge@gmail.com>
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

#include "aliases-dialog.h"

AliasTreeView::AliasTreeView (BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
        Gtk::TreeView(cobject),
        builder(refGlade)
{
	refListStore = Gtk::ListStore::create(aliasColumns);
	set_model(refListStore);
	append_column("Styl", aliasColumns.style);
	append_column("Chr", aliasColumns.character);
	append_column("Var", aliasColumns.variant);
	append_column(" →  ", aliasColumns.arrow);
	append_column_editable("Styl", aliasColumns.targetstyle);
	append_column_editable("Chr", aliasColumns.targetcharacter);
	append_column_editable("Var", aliasColumns.targetvariant);
	get_selection()->set_mode(Gtk::SELECTION_MULTIPLE);
}

AliasesDialog::AliasesDialog(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
Gtk::Dialog(cobject),
builder(refGlade)
{
	builder->get_widget_derived("treeviewAliases", treeviewAliases);
	builder->get_widget("buttonRestyleAliases", buttonRestyleAliases);
	builder->get_widget("buttonResetAliases", buttonResetAliases);
	builder->get_widget("entryAliasStyle", entryAliasStyle);
	buttonRestyleAliases->signal_clicked().connect( sigc::mem_fun(*this, &AliasesDialog::on_buttonRestyleAliases_clicked) ); 
	buttonResetAliases->signal_clicked().connect( sigc::mem_fun(*this, &AliasesDialog::on_buttonResetAliases_clicked) ); 
}

void AliasesDialog::on_buttonRestyleAliases_clicked() {
	Glib::ustring newstylestring = entryAliasStyle->get_text();
	if (newstylestring.length() > 0) {
		int newstyle = ustringToInt(newstylestring);
		std::vector<Gtk::TreeModel::Path> paths = treeviewAliases->get_selection()->get_selected_rows();
		for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
			Gtk::TreeModel::iterator iter = treeviewAliases->get_model()->get_iter(*pathit);
			(*iter)[aliasColumns.targetstyle] = intToUstring(newstyle);
			if ( (*iter)[aliasColumns.targetcharacter] == "" ) {
				const Glib::ustring chr = (*iter)[aliasColumns.character];
				(*iter)[aliasColumns.targetcharacter] = chr;
			}
			if ( (*iter)[aliasColumns.targetvariant] == "" ) {
				(*iter)[aliasColumns.targetvariant] = intToUstring((*iter)[aliasColumns.variant]);
			}
		}
		entryAliasStyle->set_text("");
	}
}

void AliasesDialog::on_buttonResetAliases_clicked() {
	std::vector<Gtk::TreeModel::Path> paths = treeviewAliases->get_selection()->get_selected_rows();
	for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
		Gtk::TreeModel::iterator iter = treeviewAliases->get_model()->get_iter(*pathit);
		const int style = (*iter)[aliasColumns.style];
		const Glib::ustring chr = (*iter)[aliasColumns.character];
		const int var = (*iter)[aliasColumns.variant];
		(*iter)[aliasColumns.targetstyle] = "";
		(*iter)[aliasColumns.targetcharacter] = "";
		(*iter)[aliasColumns.targetvariant] = "";
	}
}

void AliasesDialog::populateList(std::set<Unigram> allUnigrams, std::map<Unigram, Unigram> aliasesMap) {
	// There might be aliases that are not currently represented in allUnigrams, so add them
	for (std::map<Unigram,Unigram>::iterator it = aliasesMap.begin();
	     it != aliasesMap.end(); ++it) {
		if (allUnigrams.count(it->first) == 0) {
			allUnigrams.insert(it->first);
		}
	}
	// Then populate the list
	treeviewAliases->refListStore->clear();
	for (std::set<Unigram>::iterator it = allUnigrams.begin(); it != allUnigrams.end(); ++it) {
		Unigram unigram = *it;
		Gtk::TreeModel::Row aliasrow = *(treeviewAliases->refListStore->append());
		aliasrow[aliasColumns.style] = unigram.style;
		aliasrow[aliasColumns.character] = unigram.chr;
		aliasrow[aliasColumns.variant] = unigram.var;
		aliasrow[aliasColumns.arrow] = "→   ";
		if (aliasesMap.count(unigram) > 0) {
			Unigram target = aliasesMap.at(unigram);
			aliasrow[aliasColumns.targetstyle] = intToUstring(target.style);
			aliasrow[aliasColumns.targetcharacter] = target.chr;
			aliasrow[aliasColumns.targetvariant] = intToUstring(target.var);
		} else {
			aliasrow[aliasColumns.targetstyle] = "";
			aliasrow[aliasColumns.targetcharacter] = "";
			aliasrow[aliasColumns.targetvariant] = "";
		}
	}
}

std::map<Unigram, Unigram> AliasesDialog::getAliasMap() {
	std::map<Unigram, Unigram> aliasMap;
	Gtk::TreeModel::Children::iterator aliasrowit;
	for (aliasrowit = treeviewAliases->refListStore->children().begin();
	     aliasrowit != treeviewAliases->refListStore->children().end();
	     ++aliasrowit)
	{
		const int style = (*aliasrowit)[aliasColumns.style];
		const Glib::ustring chr = (*aliasrowit)[aliasColumns.character];
		const int var = (*aliasrowit)[aliasColumns.variant];
		int targetstyle;
		Glib::ustring targetchr;
		int targetvar;
		if ((*aliasrowit)[aliasColumns.targetstyle] == "") {
			targetstyle = style;
		} else {
			targetstyle = ustringToInt((*aliasrowit)[aliasColumns.targetstyle]);
		}
		if ((*aliasrowit)[aliasColumns.targetcharacter] == "") {
			targetchr = chr;
		} else {
			targetchr = (*aliasrowit)[aliasColumns.targetcharacter];
		}
		if ((*aliasrowit)[aliasColumns.targetvariant] == "") {
			targetvar = var;
		} else {
			targetvar = ustringToInt((*aliasrowit)[aliasColumns.targetvariant]);
		}
		if (style != targetstyle || chr != targetchr || var != targetvar) {
			aliasMap.insert(std::pair<Unigram,Unigram>(
			   Unigram(chr, style, var), Unigram(targetchr, targetstyle, targetvar)));
		}
	}
	return aliasMap;
}
