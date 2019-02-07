/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * page.h
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

#ifndef _PAGE_H_
#define _PAGE_H_

#include <gtkmm.h>
#include <iostream>
#include "image.h"
//#include "box-tree-view.h"

class Page
{
public:
	
	Page();
	virtual ~Page();
	Page(std::string filename);

	void setBoxListStore(Glib::RefPtr<Gtk::ListStore> boxListStore);
	void setTextBuffer(Glib::RefPtr<Gtk::TextBuffer> textBuffer);
	
	int getWidth();
	int getHeight();
	std::string getFilename();
	Glib::RefPtr<Gdk::Pixbuf> getPixbuf();
	Glib::RefPtr<Gtk::ListStore> getBoxListStore();
	Glib::RefPtr<Gtk::TextBuffer> getTextBuffer();
	Image* getImage();
	
	void decachePixbuf();
	
protected:

private:
	
	//BoxColumns boxColumns;

	void loadPixbuf();
	std::string m_filename;
	int m_width;
	int m_height;
	Glib::RefPtr<Gdk::Pixbuf> m_refPixbuf;
	Glib::RefPtr<Gtk::ListStore> m_refBoxListStore;
	Glib::RefPtr<Gtk::TextBuffer> m_refTextBuffer;
	Image* m_refImage;
	
};

#endif // _PAGE_H_

