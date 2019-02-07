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

#include "image.h"
#include "box.h"

// Note: Image deals with ink! 0 = paper = white; 1 = ink = black.

Image::Image(std::string filename) {
	fromPixbuf(Gdk::Pixbuf::create_from_file(filename));
}

Image::Image(Glib::RefPtr<Gdk::Pixbuf> pixbuf) {
	fromPixbuf(pixbuf);
}

void Image::fromPixbuf(Glib::RefPtr<Gdk::Pixbuf> img) {
   int rowstride, n_channels;
   guchar *pixels, *p;

   construct(img->get_width(), img->get_height(), false);

   n_channels = img->get_n_channels();
   g_assert (img->get_bits_per_sample() == 8);
   g_assert (n_channels >= 3);
   rowstride = img->get_rowstride();
   pixels = img->get_pixels();

   for (int y=0; y<height_; y++) {
      for (int x=0; x<width_; x++) {
         p = pixels + y * rowstride + x * n_channels;
         (*this)(x,y)=1.0-(float)(p[0]+p[1]+p[2])/(255*3);
      } 
   }
}
                       
void Image::normalize(int left, int top, int right, int bot) {
	float lightest=1;
	float darkest=0;
	for (int y=top; y<bot; y++) {
		for (int x=left; x<right; x++) {
			if (darkest < (*this)(x,y))
				darkest=(*this)(x,y);
			if (lightest > (*this)(x,y))
				lightest=(*this)(x,y);
		} 
	}
	for (int y=top; y<bot; y++) {
		for (int x=left; x<right; x++) {
			(*this)(x,y) = ((*this)(x,y)-lightest) / (darkest-lightest);
		} 
	}
}

void Image::contrast(float c) {
      for (int y=0; y<height_; y++) {
         for (int x=0; x<width_; x++) {
            (*this)(x,y) = std::min(std::max(((*this)(x,y)-0.5)*c+0.5,0.0),1.0);
         } 
      }
}
 
float Image::pixel(int x, int y) {
      if (x>=width_ || y>=height_ || x<0 || y<0) // We may access pixels outside the image.
         return 0;                               // But there is nothing there.
      else
         return (*this)(x,y);
}

void Image::setpixel(int x, int y, float p) {
      if (!(x>=width_ || y>=height_ || x<0 || y<0))
         (*this)(x,y)=p;
}

float Image::pixel(float x, float y) {
      float p=0;
      float b0,b1,b2,b3;
      if (true) { // Bicubic
         b0=cubic(x-floor(x), pixel((int)floor(x)-1,(int)floor(y)-1), pixel((int)floor(x)+0,(int)floor(y)-1), pixel((int)floor(x)+1,(int)floor(y)-1), pixel((int)floor(x)+2,(int)floor(y)-1));
         b1=cubic(x-floor(x), pixel((int)floor(x)-1,(int)floor(y)+0), pixel((int)floor(x)+0,(int)floor(y)+0), pixel((int)floor(x)+1,(int)floor(y)+0), pixel((int)floor(x)+2,(int)floor(y)+0));
         b2=cubic(x-floor(x), pixel((int)floor(x)-1,(int)floor(y)+1), pixel((int)floor(x)+0,(int)floor(y)+1), pixel((int)floor(x)+1,(int)floor(y)+1), pixel((int)floor(x)+2,(int)floor(y)+1));
         b3=cubic(x-floor(x), pixel((int)floor(x)-1,(int)floor(y)+2), pixel((int)floor(x)+0,(int)floor(y)+2), pixel((int)floor(x)+1,(int)floor(y)+2), pixel((int)floor(x)+2,(int)floor(y)+2));
         p=cubic(y-floor(y),b0,b1,b2,b3);
         p=std::min(std::max(p,(float)0),(float)1);
      } else { // Bilinear interpolation
         float b0,b1,b2,b3;
         b0=pixel((int)floor(x),(int)floor(y));
         b1=pixel((int)ceil(x),(int)floor(y))-b0;
         b2=pixel((int)floor(x),(int)ceil(y))-b0;
         b3=pixel((int)ceil(x),(int)ceil(y))-b0-b1-b2;
         p=b0 + b1*(x-floor(x)) + b2*(y-floor(y)) + b3*(x-floor(x))*(y-floor(y));
      }
      return p;
}


Glib::RefPtr<Gdk::Pixbuf> Image::toPixbuf(Image* maskimg, int zoom) {
   int width=width_/zoom, height=height_/zoom;
   int rowstride, n_channels;
   float pixel, mask;
   guchar *pixels, *p;

   Glib::RefPtr<Gdk::Pixbuf> img = Gdk::Pixbuf::create(Gdk::COLORSPACE_RGB, false, 8, width, height);

   n_channels = img->get_n_channels();
   g_assert (img->get_bits_per_sample() == 8);
   g_assert (n_channels == 3);
   rowstride = img->get_rowstride();
   pixels = img->get_pixels();

   for (int y=0; y<height; y++) {
      for (int x=0; x<width; x++) {
         p = pixels + y * rowstride + x * n_channels;
         float diff, maxdiff=-1;
         pixel=0;
         for (int addy=0; addy<zoom; addy++) {
            for (int addx=0; addx<zoom; addx++) {
               if (maskimg) {
                  pixel=std::min(1.0,std::max(0.0,(double)(*this)(zoom*x+addx,zoom*y+addy)));
						float unlimitedmask = std::max(0.0,(double)(*maskimg)(zoom*x+addx,zoom*y+addy));
						if (unlimitedmask > 1.5) {
							maxdiff = 1;
               		p[0]=(unsigned char)(255);
               		p[1]=(unsigned char)(0);
               		p[2]=(unsigned char)(0);
						} else {
               		mask=std::min(1.0,(double)unlimitedmask);
               		diff=square(pixel-mask);
               		if (diff>maxdiff) {
               		   maxdiff=diff;
               		   p[0]=(unsigned char)(255*std::min(1.0,std::max(0.0, 1.0-1.0*mask*mask-1.0*pixel*pixel+2.0*mask*pixel )));
               		   p[1]=(unsigned char)(255*std::min(1.0,std::max(0.0, 1.0-1.0*mask*mask-0.7*pixel*pixel+1.7*mask*pixel )));
               		   p[2]=(unsigned char)(255*std::min(1.0,std::max(0.0, 1.0-0.6*mask*mask-1.0*pixel*pixel+1.6*mask*pixel )));
               		}
						}
               } else {
                  pixel+=std::min(1.0,std::max(0.0,(double)(*this)(zoom*x+addx,zoom*y+addy)));
               }
            }
         }
         if (!maskimg) {
            pixel/=zoom*zoom;
            p[0]=p[1]=p[2]=(unsigned char)((1.0-pixel)*255);
         }
      } 
   } 

   return img;
}

void Image::savepng(std::string filename) {
   Glib::RefPtr<Gdk::Pixbuf> img = toPixbuf();
   img->save(filename, "png");
}


void Image::addbox(Box *box, int xpos, int ypos) {
   if (xpos+box->width()>width_ || ypos+box->height()>height_ || xpos<0 || ypos<0) {
      std::cerr << "Warning: Attempt at adding a box outside the image." << std::endl;
   } else {

      for (int y=0; y<box->height(); y++) {
         for (int x=0; x<box->width(); x++) {
             (*this)(xpos+x,ypos+y) += box->pixel(x,y);
         }
      }

   }
}

void Image::crop_bottom(int newheight) {
   if (newheight<height_) {
      height_=newheight;
   }
}

