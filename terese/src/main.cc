/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * main.cc
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

#include <gtkmm.h>

#include "config.h"
#include "terese.h"

/* #define UI_FILE PACKAGE_DATA_DIR"/ui/terese.ui" */
#define UI_FILE "src/terese.ui"
   
int main (int argc, char *argv[]) {

	Gtk::Main kit(argc,argv);
	
	Glib::RefPtr<Gtk::Builder> builder;
	try {
		builder = Gtk::Builder::create_from_file(UI_FILE);
	} catch (const Glib::FileError & ex) {
		std::cerr << ex.what() << std::endl;
		return 1;
	}
	
	Terese *terese = NULL;
	builder->get_widget_derived("winTerese", terese);
	if (terese) {
		kit.run(*terese);
	}
	
	return 0;

}

