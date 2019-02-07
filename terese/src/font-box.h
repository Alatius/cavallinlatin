/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * font-box.h
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

#ifndef _FONT_BOX_H_
#define _FONT_BOX_H_

#include "box.h"

class FontBox: public Box {
public:
	FontBox(Unigram unigram, int lft, int top, int width, int height, Image *img,
	        float lbear, float rbear, float ldev, float rdev) :
		Box(unigram, lft, top, width, height, img),
		lbear_(lbear), rbear_(rbear), ldev_(ldev), rdev_(rdev)
	{
	}

	float getLbear();
	float getRbear();
	float getLdev();
	float getRdev();

	void setLbear(float lbear);
	void setRbear(float rbear);
	void setLdev(float ldev);
	void setRdev(float rdev);
		
protected:
	float lbear_, rbear_, ldev_, rdev_;
	
private:

};

#endif // _FONT_BOX_H_

