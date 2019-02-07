/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * unigram.h
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

#ifndef _UNIGRAM_H_
#define _UNIGRAM_H_

#include <gtkmm.h>
//#include <string.h> 
#include "box-tree-view.h"

class Unigram {
public:
	Unigram();
	Unigram(Glib::ustring c, int s, int v);
	Unigram(Gtk::TreeModel::Children::iterator boxit);

	bool equals(const Unigram other) const;
	
	Glib::ustring print() const;
	
	bool exists;
	Glib::ustring chr;
   int style;
	int var;
	friend bool operator < (const Unigram &u1, const Unigram &u2) {
		if (u1.style < u2.style) return true;
		if (u1.style > u2.style) return false;
		// Use strcmp to avoid locale collation (where e.g. "longs s" = "s")
		if (strcmp(u1.chr.c_str(), u2.chr.c_str()) < 0) return true;
		if (strcmp(u1.chr.c_str(), u2.chr.c_str()) > 0) return false;
		if (u1.var < u2.var) return true;
		return false;
	}
};

#endif // _UNIGRAM_H_

