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

#ifndef MATRIX_H
#define MATRIX_H

#include <iostream>
#include <stdexcept>

template <class T>
class Matrix {
private:
   T *elements_;
protected:
   int width_, height_;
public:

   Matrix() {
     elements_=NULL;
     width_=0;
     height_=0;
   }
   Matrix(int w, int h) {
      construct(w,h);
   }
   ~Matrix() {
      delete[] elements_;
   }
protected:
   void construct(int w, int h, bool empty = true) {
      elements_ = new T[w*h];
      width_=w;
      height_=h;
      if (empty) {
			reset();
		}
   }
public:
   void reset() {
      for (int y=0; y<height_; y++) {
         for (int x=0; x<width_; x++) {
            (*this)(x,y)=0;
         }
      }
   }
   T& operator() (int x, int y) {
      if (x<0 || x>=width_ || y<0 || y>=height_)
         throw std::out_of_range("Matrix::operator()");
      return elements_[y*width_+x];
   }
   int height() {
      return height_;
   }
   int width() {
      return width_;
   }
   void print() { // Print in Matlab format
      std::cout << "[";
      for (int y=0; y<height_; y++) {
         for (int x=0; x<width_; x++) {
            std::cout << (*this)(x,y);
            if (x<width_-1)
               std::cout << ", ";
            else
               std::cout << ";";
         }
         if (y<height_-1)
            std::cout << std::endl << " ";
         else
            std::cout << "]" << std::endl;
      }
   }
};

// This is a very special kind of sparse matrix, with a maximum of two non-zero elements in each row.
template <class T>
class Sparsematrix {
private:
   int *firstpos_;
   int *secondpos_;
   T *firstval_;
   T *secondval_;
   int width_;
   int height_;
public:
   Sparsematrix(int x, int y) {
      firstpos_ = new int[y];
      secondpos_ = new int[y];
      firstval_ = new T[y];
      secondval_ = new T[y];
      width_ = x;
      height_ = y;
      for (int i=0; i<height_; i++) {
         firstpos_[i]=-1;
         secondpos_[i]=-1;
      }
   }
   ~Sparsematrix() {
      delete[] firstpos_;
      delete[] secondpos_;
      delete[] firstval_;
      delete[] secondval_;
   }
   int height() {
      return height_;
   }
   int width() {
      return width_;
   }
   T operator() (int x, int y) {
      if (x<0 || x>=width_ || y<0 || y>=height_)
         throw std::out_of_range("Sparsematrix::operator()");
      if (firstpos_[y]==x)
         return firstval_[y];
      if (secondpos_[y]==x)
         return secondval_[y];
      return 0;
   }
   void setrow(int y, int apos, int bpos=-1, T avalue=1, T bvalue=1) {
      if (y<0 || y>=height_ || apos >=width_ || bpos >=width_)
         throw std::out_of_range("Sparsematrix::setrow()");
      firstpos_[y]=apos;
      secondpos_[y]=bpos;
      firstval_[y]=avalue;
      secondval_[y]=bvalue;
   }
   void print() {
      std::cout << "[";
      for (int y=0; y<height_; y++) {
         for (int x=0; x<width_; x++) {
            std::cout << (*this)(x,y);
            if (x<width_-1)
               std::cout << ", ";
            else
               std::cout << ";";
         }
         if (y<height_-1)
            std::cout << std::endl << " ";
         else
            std::cout << "]" << std::endl;
      }
   }

};

#endif // MATRIX_H

