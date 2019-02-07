/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * page.cc
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

#include "page.h"

Page::Page() : m_filename(""), m_refPixbuf(NULL), m_refImage(NULL), m_width(0), m_height(0) {

}

Page::~Page() {
	decachePixbuf();
}

Page::Page(std::string filename) : m_filename(filename), m_refPixbuf(NULL), m_refImage(NULL), m_width(0), m_height(0) {
	//loadPixbuf();
}

void Page::loadPixbuf() {
	m_refPixbuf = Gdk::Pixbuf::create_from_file(m_filename);
	m_width = m_refPixbuf->get_width();
	m_height = m_refPixbuf->get_height();
}

void Page::setBoxListStore(Glib::RefPtr<Gtk::ListStore> boxListStore) {
	m_refBoxListStore = boxListStore;
}

void Page::setTextBuffer(Glib::RefPtr<Gtk::TextBuffer> textBuffer) {
	m_refTextBuffer = textBuffer;
}

int Page::getWidth() {
	if (m_width==0 && m_filename!="") {
		loadPixbuf();
	}
	return m_width;
}

int Page::getHeight() {
	if (m_height==0 && m_filename!="") {
		loadPixbuf();
	}
	return m_height;
}

std::string Page::getFilename() {
	return m_filename;
}

Glib::RefPtr<Gdk::Pixbuf> Page::getPixbuf() {
	if (!m_refPixbuf && m_filename!="") {
		loadPixbuf();
	}
	return m_refPixbuf;
}

Image* Page::getImage() {
	if (!m_refImage) {
		if (!m_refPixbuf && m_filename!="") {
			loadPixbuf();
		}
		if (m_refPixbuf) {
			m_refImage = new Image(m_refPixbuf);
		}
	}
	return m_refImage;
}

Glib::RefPtr<Gtk::ListStore> Page::getBoxListStore() {
	return m_refBoxListStore;
}

Glib::RefPtr<Gtk::TextBuffer> Page::getTextBuffer() {
	return m_refTextBuffer;
}

void Page::decachePixbuf() {
	m_refPixbuf.reset();
	delete m_refImage;
	m_refImage = NULL;
}


