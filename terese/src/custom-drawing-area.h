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

#ifndef _CUSTOM_DRAWING_AREA_H_
#define _CUSTOM_DRAWING_AREA_H_

#include <gtkmm.h>
#include <iostream>
#include <stdlib.h>
#include "box-tree-view.h"

//#include "image.h"

class CustomDrawingArea : public Gtk::DrawingArea 
{
public:
	CustomDrawingArea(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);

	virtual ~CustomDrawingArea();

	void set_boxes(BoxTreeView *refBoxes);
	void set_zoom(int zoom);
	Glib::RefPtr<Gdk::Pixbuf> get_pixbuf();
	
	//void show_image(Image* img, int zoom=1, Image* mask=NULL);
	//void on_showPageImage(Image* img);
	void on_showPageImage(Glib::RefPtr<Gdk::Pixbuf> pixbuf);

	void on_centerBox(int left, int right, int top, int bot);

	typedef sigc::signal< void, int, int > type_signal_coordinates;
	type_signal_coordinates signal_boxselect();
	type_signal_coordinates signal_boxrelocate();

protected:

	BoxTreeView *m_treeviewBoxes;
	int m_currentZoom;
	bool m_boxSelectEmitted;
	
	//Image* m_refImage;
	Glib::RefPtr<Gdk::Pixbuf> m_refPixbuf;
	Glib::RefPtr<Gdk::Pixbuf> m_refScaledPixbuf;

	type_signal_coordinates m_signal_boxselect;
	type_signal_coordinates m_signal_boxrelocate;

	bool on_button_press_event(GdkEventButton* event);
	
	virtual bool on_draw(const Cairo::RefPtr<Cairo::Context>& cr);

	BoxColumns boxColumns;

};

#endif // _CUSTOM_DRAWING_AREA_H_

