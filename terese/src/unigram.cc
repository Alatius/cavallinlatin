/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * unigram.cc
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

#include "unigram.h"

Unigram::Unigram() : exists(false), chr(""), style(0), var(0) {
}

Unigram::Unigram(Glib::ustring c, int s, int v) : exists(true), chr(c), style(s), var(v) {
}

Unigram::Unigram(Gtk::TreeModel::Children::iterator boxit) {
	BoxColumns boxColumns;
	exists = true;
	style = (*boxit)[boxColumns.style];
	chr = (*boxit)[boxColumns.character];
	var = (*boxit)[boxColumns.variant];
}

bool Unigram::equals(const Unigram other) const {
	return (style == other.style && strcmp(chr.c_str(), other.chr.c_str()) == 0 && var == other.var);
}
	
Glib::ustring Unigram::print() const {
	std::stringstream out;
   out << style << chr << var;
   return out.str();
}
