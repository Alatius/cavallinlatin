/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * aliases-dialog.h
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

#ifndef _ALIASES_DIALOG_H_
#define _ALIASES_DIALOG_H_

#include <set>
#include <gtkmm.h>
#include "unigram.h"
#include "common.h"

class AliasColumns : public Gtk::TreeModel::ColumnRecord {
	public:
		AliasColumns() {
			add(character);
			add(style);
			add(variant);
			add(arrow);
			add(targetcharacter);
			add(targetstyle);
			add(targetvariant);
		}
		Gtk::TreeModelColumn<Glib::ustring> character;
		Gtk::TreeModelColumn<int> style;
		Gtk::TreeModelColumn<int> variant;
		Gtk::TreeModelColumn<Glib::ustring> arrow;
		Gtk::TreeModelColumn<Glib::ustring> targetcharacter;
		Gtk::TreeModelColumn<Glib::ustring> targetstyle;
		Gtk::TreeModelColumn<Glib::ustring> targetvariant;
};

class AliasTreeView : public Gtk::TreeView {
	public:
		AliasTreeView(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
		Glib::RefPtr<Gtk::ListStore> refListStore;

	private:
		Glib::RefPtr<Gtk::Builder> builder;
		AliasColumns aliasColumns;
};

class AliasesDialog : public Gtk::Dialog {
	public:
		AliasesDialog(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);

		void populateList(std::set<Unigram> allUnigrams, std::map<Unigram, Unigram> aliasesMap);
		std::map<Unigram, Unigram> getAliasMap();

	protected:
		Glib::RefPtr<Gtk::Builder> builder;

		AliasTreeView *treeviewAliases;

		Gtk::Button *buttonRestyleAliases;
		Gtk::Button *buttonResetAliases;
		Gtk::Entry *entryAliasStyle;

		void on_buttonRestyleAliases_clicked();
		void on_buttonResetAliases_clicked();
		
	private:
		AliasColumns aliasColumns;		
};

#endif // _ALIASES_DIALOG_H_

