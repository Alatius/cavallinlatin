/**********************************************************************
//
//  Copyright (C) 2010-2011 Johan Winge.
//
//  This file is part of Terese.
//
//  Terese is free software: you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation, either version 3 of the License, or
//  (at your option) any later version.
//
//  Terese is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with Terese.  If not, see <http://www.gnu.org/licenses/>.
//
/**********************************************************************/

#ifndef IMAGE_H
#define IMAGE_H

class Box;

#include <gtkmm.h>
#include "matrix.h"

class Image : public Matrix<float> {
public:

   Image(int w, int h) : Matrix<float>(w, h) { }
   Image(std::string filename);
   Image(Glib::RefPtr<Gdk::Pixbuf> pixbuf);
	void fromPixbuf(Glib::RefPtr<Gdk::Pixbuf> img);
	
   void normalize() { normalize(0,0,width_,height_); }
   void normalize(int left, int top, int right, int bot);
   void contrast(float c);
   float pixel(int x, int y);
   void setpixel(int x, int y, float p);
   inline float cubic(float t,float a0, float a1, float a2, float a3) {
      return (t*(t*(t*(-a0+3*a1-3*a2+a3)+2*a0-5*a1+4*a2-a3)-a0+a2)+2*a1)/2;
   }
   float pixel(float x, float y);
   void addbox(Box *box, int xpos, int ypos);

   Glib::RefPtr<Gdk::Pixbuf> toPixbuf(Image* mask=NULL, int zoom=1);
   void savepng(std::string filename);
   void crop_bottom(int newheight);

};

#endif // IMAGE_H

