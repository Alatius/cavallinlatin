/**********************************************************************
//
//  Copyright (C) 2010-2014 Johan Winge.
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

#ifndef BOX_H
#define BOX_H

#include <fftw3.h>
#include "unigram.h"
#include "image.h"
#include "box-tree-view.h"

inline float square(float a) { return a*a; }
inline float powers(float a) { return a*a*a*a*a*a; }

class Box
{
private:
	
	class FourierTransform {
	public:
		FourierTransform(int width, int height, const Box *box);
		~FourierTransform();
		fftw_complex *fourierdata;
		int M, N;
		double blackness;
	};
   Unigram unigram_;
   int lft_, top_, width_, height_;
   Image *img_;
   float xdisp_, ydisp_;
   bool isaligned_;
	Gtk::TreeModel::Children::iterator rowit_;
	std::vector<FourierTransform*> templatecache;
	
public:
   Box();
   Box(Unigram unigram, int lft, int top, int width, int height, Image *img);
	Box(Gtk::TreeModel::Children::iterator rowit, Image *img);
	~Box();
	
   float lineslope;
   bool followedbyspace;
   bool dubious;
   int indx; // Currently used when creating a font
   Box *nextinline;
   Unigram unigram() const { return unigram_; }
   int width() const { return width_; }
   int height() const { return height_; }
   int left() const { return lft_; }
   int right() const { return lft_+width_; }
   int top() const { return top_; }
   int bot() const { return top_+height_; }
   float xdisp() const { return xdisp_; }
   float ydisp() const { return ydisp_; }
   bool isaligned() const { return isaligned_; }
   Image* img() const { return img_; }
   float pixel(int x, int y) const { return img_->pixel(lft_+x,top_+y); }
   float pixel(float x, float y) const { return img_->pixel((float)lft_+x,(float)top_+y); }
   void setdisps(float xdisp, float ydisp);
   void print();
   std::string to_string();
	void addleft(int leftadd);
	void setwidth(int width);

	fftw_complex* getTransform(int &M, int &N, double &blackness);
	void invalidateTransformCache();
	float finddisplacement(Box *other, float &xdisp, float &ydisp, int minxdisp = 0, int maxxdisp = 0, int minydisp = 0, int maxydisp = 0, float leftgoodenoughfactor = 1.0);

};

#endif // BOX_H

