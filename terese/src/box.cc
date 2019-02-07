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

#include "box.h"

Box::Box() {
	img_ = NULL;
}

Box::Box(Unigram unigram, int lft, int top, int width, int height, Image *img):
      unigram_(unigram), lft_(lft), top_(top), width_(width), height_(height),
		img_(img), rowit_(NULL), xdisp_(0), ydisp_(0), isaligned_(false),
		indx(-1), nextinline(NULL), dubious(false), followedbyspace(false),
		lineslope(0) {
}

Box::Box(Gtk::TreeModel::Children::iterator rowit, Image *img):
      img_(img), rowit_(rowit), xdisp_(0), ydisp_(0), isaligned_(false),
		indx(-1), nextinline(NULL), followedbyspace(false), lineslope(0) {
	BoxColumns boxColumns;
	Glib::ustring character = (*rowit)[boxColumns.character];
	int style = (*rowit)[boxColumns.style];
	int var = (*rowit)[boxColumns.variant];
	unigram_ = Unigram(character, style, var);
	dubious = (*rowit)[boxColumns.degenerate];
	lft_ = (*rowit)[boxColumns.left];
	width_ = (*rowit)[boxColumns.right] - lft_;
	top_ = (*rowit)[boxColumns.top];
	height_ = (*rowit)[boxColumns.bottom] - top_;
}

void Box::setdisps(float xdisp, float ydisp) {
	xdisp_=xdisp;
	ydisp_=ydisp;
	isaligned_=true;
}

Box::FourierTransform::FourierTransform(int width, int height, const Box *box) : M(width), N(height) {
	double *realdata;
	realdata = fftw_alloc_real(M * N);
	fourierdata = fftw_alloc_complex(M * (N/2+1));
	fftw_plan plan;
	plan = fftw_plan_dft_r2c_2d(M, N, realdata, fourierdata, FFTW_DESTROY_INPUT);
	blackness = 0.0;
	for (int x = 0; x < M; ++x) {
		for (int y = 0; y < N; ++y) {
			if (x < box->width() && y < box->height()) {
				double scaledpix = box->pixel(x,y)*2-1;
				realdata[box->height()-1-y + N*(box->width()-1-x)] = scaledpix; // Note! Rotation!
				if (scaledpix > 0) {
					blackness += scaledpix;
				}
			} else {
				realdata[y + N*x] = 0 ;
			}
		}
	}
	fftw_execute(plan);
	fftw_destroy_plan(plan);
	fftw_free(realdata);
}

Box::FourierTransform::~FourierTransform() {
	fftw_free(fourierdata);
}

fftw_complex* Box::getTransform(int &M, int &N, double &blackness) {
	// It is often beneficial to round the dimensions up, as FFTW performs
	// better when the size factorizes to small primes.
/*
	int bestsizes[] = {16, 18, 20, 21, 22, 24, 25, 26, 27, 28, 30, 32, 33, 35,
		36, 39, 40, 42, 44, 45, 48, 49, 50, 52, 54, 55, 56, 60, 63, 64, 65, 66,
		70, 72, 75, 77, 78, 80, 81, 84, 88, 90, 91, 96, 98, 99, 100, 104, 105,
		108, 110, 112, 117, 120, 125, 126, 128, 130, 132, 135, 140, 144, 147,
		150, 154, 156, 160, 162, 165, 168, 175, 176, 180, 182, 189, 192, 195,
		196, 198, 200, 208, 210, 216, 220, 224, 225, 231, 234, 240, 243, 245,
		250, 252, 256, 260, 264, 270, 273, 275, 280, 288, 294, 297, 300, 308,
		312, 315, 320, 324, 325, 330, 336, 343, 350, 351, 352, 360, 364, 375,
		378, 384, 385, 390, 392, 396, 400, 405, 416, 420, 432, 440, 441, 448,
		450, 455, 462, 468, 480, 486, 490, 495, 500, 504, 512}; // Length 144
*/
	// At least on my system, we can get even better results with the following
	// thresholds. YMMV, of course.
	int bestsizes[] = {16, 20, 25, 32, 36, 40, 42, 44, 48, 50, 64, 66, 70, 72,
		78, 80, 84, 90, 96, 100, 104, 108, 112, 120, 128, 130, 132, 140, 144, 150,
		156, 160, 168, 180, 192, 200, 208, 210, 224, 240, 256, 260, 280, 300, 320,
		324, 330, 336, 360, 384, 400, 416, 420, 432, 448, 450, 512}; // Length 57
	for (int i=0; i<57; ++i) {
		if (bestsizes[i] >= M) {
			M = bestsizes[i];
			break;
		}
	}
	for (int i=0; i<57; ++i) {
		if (bestsizes[i] >= N) {
			N = bestsizes[i];
			break;
		}
	}
	// Maybe we have already calculated the template transform of this size for this box?
	for (std::vector<FourierTransform*>::iterator it = templatecache.begin();
	     it != templatecache.end(); ++it) {
		if (M == (*it)->M && N == (*it)->N) {
			blackness = (*it)->blackness;
			return (*it)->fourierdata;
		}
	}
	// Apparently not...
	FourierTransform* transform = new FourierTransform(M, N, this);
	templatecache.push_back(transform);
	blackness = transform->blackness;
	return transform->fourierdata;
}

void Box::invalidateTransformCache() {
	for (std::vector<FourierTransform*>::iterator it = templatecache.begin();
	     it != templatecache.end(); ++it) {
			delete (*it);
	}
	templatecache.clear();
}

// Find at what displacement this box (the template) fits over another box.
// The alignment/registration is done through convolution using FFT.
float Box::finddisplacement(Box *other, float &xdisp, float &ydisp, int minxdisp, int maxxdisp, int minydisp, int maxydisp, float leftgoodenoughfactor) {

	double maxpossiblecorr, maxcorr;
	double corr;
	int bestx, besty;
	
	int M = width_ + other->width();
	int N = height_ + other->height();

	fftw_complex *A, *B, *C;
	
	A = getTransform(M, N, maxpossiblecorr); // Note: Changes M and N!
	B = fftw_alloc_complex(M * (N/2+1));
	C = fftw_alloc_complex(M * (N/2+1));

	double *otherdata, *convdata;
	otherdata = fftw_alloc_real(M * N);
	convdata = fftw_alloc_real(M * N);

	fftw_plan plan, pinv;

	plan = fftw_plan_dft_r2c_2d(M, N, otherdata, B, FFTW_DESTROY_INPUT);
	pinv = fftw_plan_dft_c2r_2d(M, N, C, convdata, FFTW_DESTROY_INPUT);

	for (int x = 0; x < M; ++x) {
		for (int y = 0; y < N; ++y) {
			if (x < other->width() && y < other->height()) {
				otherdata[y+N*x] = other->pixel(x,y);
			} else {
				otherdata[y+N*x] = 0;
			}
		}
	}

	// Perform the fourier-transform of the other box
	fftw_execute(plan);

	// Do the actual convolution
	double scale = 1.0 / (M * N);
	for (int i = 0; i < M; ++i) {
		for (int j = 0; j < N/2+1; ++j) {
			int ij = i*(N/2+1) + j;
			C[ij][0] = (A[ij][0] * B[ij][0] - A[ij][1] * B[ij][1]) * scale;
			C[ij][1] = (A[ij][0] * B[ij][1] + A[ij][1] * B[ij][0]) * scale;
		}
	}

	// And do the reverse transform, which saves the result to convdata
	fftw_execute(pinv);

	// Find maximum correlation
	//Image convolution(M,N);
	int minx, maxx, miny, maxy;
	if (minxdisp == 0 && maxxdisp == 0 && minydisp == 0 && maxydisp == 0) {
		//minx = 0; maxx = M;
		//miny = 0; maxy = N;
		minx = 0.25*M; maxx = 0.75*M;
		miny = 0.2*N; maxy = 0.8*N;
		//minx = 0.4*M; maxx = 0.6*M;
		//miny = 0.4*N; maxy = 0.6*N;
	} else {
		minx = std::max(0, minxdisp + width_ - 1);
		maxx = std::min(M, maxxdisp + width_ - 1);
		miny = std::max(0, minydisp + height_ - 1);
		maxy = std::min(N, maxydisp + height_ - 1);
	}
	bestx=minx; besty=miny;
	maxcorr = convdata[besty+N*bestx];
	for (int x = minx; x < maxx; ++x) {
		for (int y = miny; y < maxy; ++y) {
			corr = convdata[y+N*x];
			if (maxcorr < corr) {
				maxcorr = corr;
				bestx = x;
				besty = y;
			}
			//convolution(x,y) = convdata[y+N*x];
		}
	}

	// But in many cases, we don't actually want the global maximum, but instead
	// the leftmost local maximum that is good enough!
	if (leftgoodenoughfactor < 1.0) {
		maxcorr = leftgoodenoughfactor * maxcorr;
		for (int x = minx; x < maxx; ++x) {
			for (int y = miny; y < maxy; ++y) {
				corr = convdata[y+N*x];
				if (maxcorr < corr) {
					maxcorr = corr;
					bestx = x;
					besty = y;
				}
			}
			if (bestx < x) {
				break;
			}
		}
	}
	
	if (maxcorr > 0) {
		// Check the values around the max, in order to try to
		// interpolate the location to subpixel accuracy.
		double const left  = convdata[besty + N*(bestx==0 ? M-1 : bestx-1)];
		double const right = convdata[besty + N*(bestx==M-1 ? 0 : bestx+1)];
		double const top   = convdata[(besty==0 ? N-1 : besty-1) + N*bestx];
		double const bot   = convdata[(besty==N-1 ? 0 : besty+1) + N*bestx];
		xdisp = bestx - width_ + 1 + 0.5*(right-left)/(maxcorr-std::min(right, left));
		ydisp = besty - height_ + 1 + 0.5*(bot-top)/(maxcorr-std::min(bot, top));
	} else {
		xdisp = 0;
		ydisp = 0;
	}
	
	maxcorr = maxcorr / maxpossiblecorr;
	
	/*
	std::cout << "Xdisp: " << xdisp << " Ydisp: " << ydisp << std::endl;
		
	convolution.normalize();
	convolution.savepng("convolution.png");

	Image box1img(width_,height_);
	for (int x=0; x<width_; x++) {
		for (int y=0; y<height_; y++) {
			box1img(x,y)=pixel(x,y);
		}
	}
	box1img.savepng("box1img.png");

	Image box2img(other->width(), other->height());
	for (int x = 0; x < other->width(); x++) {
		for (int y = 0; y < other->height(); y++) {
			box2img(x,y) = other->pixel(x,y);
		}
	}
	box2img.savepng("box2img.png");
	*/
	
	// Clean up
	fftw_destroy_plan(plan);
	fftw_destroy_plan(pinv);
	fftw_free(otherdata);
	fftw_free(convdata);
	fftw_free(B);
	fftw_free(C);

	return maxcorr;
}

void Box::print() {
   for (int y=0; y<height_; y++) {
      for (int x=0; x<width_; x++)
         std::cout << pixel(x,y);
      std::cout << std::endl;
   }
}

std::string Box::to_string() {
   std::stringstream out;
   out << unigram().print() << " l=\"" << left() << "\" r=\"" << right() << "\" t=\"" << top() << "\" b=\"" << bot() << "\"" << std::endl;
   return out.str();
}

void Box::addleft(int leftadd) {
	lft_ += leftadd;
	width_ -= leftadd;
	xdisp_ -= leftadd;
}

void Box::setwidth(int width) {
	width_ = width;
}

Box::~Box() {
	invalidateTransformCache();
}
