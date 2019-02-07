/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * type-box.cc
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

#include "type-box.h"

float TypeBox::getLbear() {
	return lbear_;
}
float TypeBox::getRbear() {
	return rbear_;
}
float TypeBox::getLdev() {
	return ldev_;
}
float TypeBox::getRdev() {
	return rdev_;
}

void TypeBox::setLbear(float lbear) {
	lbear_ = lbear;
}
void TypeBox::setRbear(float rbear) {
	rbear_ = rbear;
}
void TypeBox::setLdev(float ldev) {
	ldev_ = ldev;
}
void TypeBox::setRdev(float rdev) {
	rdev_ = rdev;
}
		