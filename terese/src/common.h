/*
 * common.h
 *
 * Copyright (C) 2014 - Johan Winge
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef _COMMON_H_
#define _COMMON_H_

#include <gtkmm.h>

inline int ustringToInt(const Glib::ustring& str) {
	std::stringstream s;
	int result;
	s << str.raw();
	s >> result;
	return result;
}

inline Glib::ustring intToUstring(const int integer) {
	std::stringstream s;
	Glib::ustring result;
	s << integer;
	s >> result;
	return result;
}

inline float ustringToFloat(const Glib::ustring& str) {
	std::stringstream s;
	float result;
	s << str.raw();
	s >> result;
	return result;
}

inline Glib::ustring escapeSpace(const Glib::ustring& str) {
	if (str == "\n") {
		return "\\n";
	} else {
		return str;
	}
}

inline Glib::ustring unescapeSpace(const Glib::ustring& str) {
	if (str == "\\n") {
		return "\n";
	} else {
		return str;
	}
}

inline int median(std::vector<int> &v, float pos = 0.5) {
   int size=v.size();
   if (size==0)
      return 0;
   int n = (size-1) * pos;
   nth_element(v.begin(), v.begin()+n, v.end());
   return v[n];
}

#endif // _COMMON_H_
