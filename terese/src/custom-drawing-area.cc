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

#include "custom-drawing-area.h"

CustomDrawingArea::CustomDrawingArea(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) : Gtk::DrawingArea(cobject) {

	m_treeviewBoxes=NULL;
	//m_refImage=NULL;
	m_currentZoom=1;
	m_boxSelectEmitted=false;
	
	add_events( Gdk::BUTTON_PRESS_MASK | Gdk::BUTTON_RELEASE_MASK );

#ifndef GLIBMM_DEFAULT_SIGNAL_HANDLERS_ENABLED
	//Connect the signal handler if it isn't already a virtual method override:
	signal_button_press_event().connect(sigc::mem_fun(*this, &CustomDrawingArea::on_button_press_event), false);
	signal_draw().connect(sigc::mem_fun(*this, &CustomDrawingArea::on_draw), false);
#endif //GLIBMM_DEFAULT_SIGNAL_HANDLERS_ENABLED
}

CustomDrawingArea::~CustomDrawingArea() {
}

CustomDrawingArea::type_signal_coordinates CustomDrawingArea::signal_boxselect() {
	return m_signal_boxselect;
}

CustomDrawingArea::type_signal_coordinates CustomDrawingArea::signal_boxrelocate() {
	return m_signal_boxrelocate;
}

Glib::RefPtr<Gdk::Pixbuf> CustomDrawingArea::get_pixbuf() {
	return m_refPixbuf; 
}

void CustomDrawingArea::set_boxes(BoxTreeView *refBoxes) {
	m_treeviewBoxes=refBoxes;
}

void CustomDrawingArea::set_zoom(int zoom) {
	m_currentZoom = zoom;
	if (m_refPixbuf) {
		if (m_currentZoom == 1) {
			m_refScaledPixbuf = m_refPixbuf;
		} else {
			const int width = m_refPixbuf->get_width()/m_currentZoom;
			const int height = m_refPixbuf->get_height()/m_currentZoom;
			m_refScaledPixbuf = m_refPixbuf->scale_simple(width, height, Gdk::INTERP_BILINEAR);
		}
		set_size_request(m_refScaledPixbuf->get_width(), m_refScaledPixbuf->get_height());
	}
	queue_draw();
}

void CustomDrawingArea::on_showPageImage(Glib::RefPtr<Gdk::Pixbuf> pixbuf) {
	if (pixbuf) {
		//m_refImage = img;
		m_refPixbuf = pixbuf;
		set_zoom(m_currentZoom);
	} else {
		//m_refImage = NULL;
		Glib::RefPtr<Gdk::Pixbuf> tmppixbuf;
		m_refPixbuf = tmppixbuf;
		set_size_request(0, 0);
		queue_draw();
	}
	/*
	if (img) {
		m_refImage = img;
		m_refPixbuf = m_refImage->toPixbuf(NULL,m_currentZoom);
		set_size_request(m_refPixbuf->get_width(), m_refPixbuf->get_height());
		
	} else {
		m_refImage = NULL;
		Glib::RefPtr<Gdk::Pixbuf> tmppixbuf;
		m_refPixbuf = tmppixbuf;
		set_size_request(0, 0);
	}
*/
}

bool CustomDrawingArea::on_button_press_event(GdkEventButton* event) {
	int xpos, ypos;
	get_pointer(xpos, ypos);
	xpos = xpos*m_currentZoom;
	ypos = ypos*m_currentZoom;
	
	// Single click without CTRL and SHIFT to select the box
   if (event->type == GDK_BUTTON_PRESS && !(event->state & GDK_CONTROL_MASK) && !(event->state & GDK_SHIFT_MASK)) {
		m_boxSelectEmitted = true;
		m_signal_boxselect.emit(xpos, ypos);
		m_boxSelectEmitted = false;
	}

	// Double click with CTRL to change the location of a single selected box
	else if (event->type == GDK_2BUTTON_PRESS && (event->state & GDK_CONTROL_MASK) && !(event->state & GDK_SHIFT_MASK)) {
		if (m_treeviewBoxes->get_selection()->count_selected_rows() == 1) {
			m_signal_boxrelocate.emit(xpos, ypos);
		}
	}
}

// Let's scroll to ensure this box is visible.
void CustomDrawingArea::on_centerBox(int left, int right, int top, int bot) {
	left=left/m_currentZoom;
	right=right/m_currentZoom;
	top=top/m_currentZoom;
	bot=bot/m_currentZoom;
	
	Gtk::Viewport* viewport = (Gtk::Viewport*) get_parent();
	Gtk::ScrolledWindow* scrolledwin = (Gtk::ScrolledWindow*) viewport->get_parent();
	Glib::RefPtr<Gtk::Adjustment> hadj = scrolledwin->get_hadjustment();
	Glib::RefPtr<Gtk::Adjustment> vadj = scrolledwin->get_vadjustment();
	int x = hadj->get_value();
	int y = vadj->get_value();
	int w = viewport->get_width();
	int h = viewport->get_height();

	if (m_boxSelectEmitted) {
		// If the request was triggered by a mouse click in the picture,
		// we want to scroll minimally.
		const int margin = 10;
		if (x > left) {
			hadj->set_value(left-margin);
		} else if (x+w < right) {
			hadj->set_value(right-w+margin);
		}
		if (y > top) {
			vadj->set_value(top-margin);
		} else if (y+h < bot) {
			vadj->set_value(bot-h+margin);
		}
	} else {
		// Scroll center
		const int leeway = 100;
		if (abs(left+right-w-2*x) > leeway) {
			hadj->set_value((left+right-w)/2);
		}
		if (abs(top+bot-h-2*y) > leeway) {
			vadj->set_value((top+bot-h)/2);
		}
	}
	
	queue_draw();
}

bool CustomDrawingArea::on_draw(const Cairo::RefPtr<Cairo::Context>& cr)
{

	if (!m_refPixbuf)
		return false;

	//cr->set_identity_matrix();

	Gdk::Cairo::set_source_pixbuf(cr, m_refScaledPixbuf, 0, 0);
	cr->paint();

	cr->scale(1.0/m_currentZoom, 1.0/m_currentZoom);
	float halfWidth=0.5*m_currentZoom;
	cr->set_line_width(2.0*halfWidth);

	std::vector<Gtk::TreePath> paths = m_treeviewBoxes->get_selection()->get_selected_rows();
	Gtk::TreeIter prevnextiter = m_treeviewBoxes->get_model()->children().end();
	int prevcenterx=0, prevcentery=0;
	for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
		Gtk::TreeIter iter = m_treeviewBoxes->get_model()->get_iter(*pathit);
		const Glib::ustring chr = (*iter)[boxColumns.character];
		/*
		if (chr == " ") {
			prevnextiter = ++iter;
			continue;
		}
		if (chr == "\\n") {
			continue;
		}
		*/
		const int left = (*iter)[boxColumns.left];
		const int right = (*iter)[boxColumns.right];
		const int top = (*iter)[boxColumns.top];
		const int bottom = (*iter)[boxColumns.bottom];
		const int centerx = (left+right)/2;
		const int centery = (top+bottom)/2;

		if (iter == prevnextiter) {
			cr->set_source_rgb(0.0, 0.0, 1.0);
			cr->move_to(prevcenterx, prevcentery);
			cr->line_to(centerx, centery);
			cr->stroke();
		}

		cr->set_source_rgb(0.9, 0.0, 0.0);
		cr->move_to(left-halfWidth, top-halfWidth);
		cr->line_to(right+halfWidth, top-halfWidth);
		cr->line_to(right+halfWidth, bottom+halfWidth);
		cr->line_to(left-halfWidth, bottom+halfWidth);
		cr->line_to(left-halfWidth, top-halfWidth);
		cr->stroke();
		
		prevcenterx = centerx;
		prevcentery = centery;
		prevnextiter = ++iter;
	}

	return true;
}

/*
void CustomDrawingArea::show_image(Image* img, int zoom, Image* mask) {
	image = img->toPixbuf(mask,zoom);
	set_size_request(image->get_width(), image->get_height());
}
*/