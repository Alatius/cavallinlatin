/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * font.cc
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

#include "font.h"

#define MINNUMOFUNIGRAMS 2000
#define MINNUMOFBIGRAMS 50

#define TIFFWIDTH 1400
#define TIFFHEIGHT 10000

Font::Font() {
	fontImage = NULL;
	numUnigrams = 0;
	minspace = 10;
	midspace = 50;
	maxspace = 100;
	linespacing = 150;
}

Font::Font(Glib::ustring imgFilename, int min, int mid, int max, int line) {
	fontImage = new Image(imgFilename);
	numUnigrams = 0;
	minspace = min;
	midspace = mid;
	maxspace = max;
	linespacing = line;
}

void Font::addType(Glib::ustring character, int style, int var, int left, int right, int top, int bottom, float lb, float rb, float ld, float rd) {
	//top += 16;
	//bottom -= 44;
	unigramMap[Unigram(character, style, var)] = numUnigrams;
	numUnigrams++;
	FontBox newbox(Unigram(character, style, var), left, top, right-left, bottom-top, fontImage,
	               lb, rb, ld, rd);
	fontBoxes.push_back(newbox);
}

void Font::addAlias(Glib::ustring character, int style, int var,
                    Glib::ustring targetchr, int targetstyle, int targetvar) {
	aliasMap[Unigram(character, style, var)] = Unigram(targetchr, targetstyle, targetvar);
}

// Return set of all types that look identical, according to aliasMap
std::set<Unigram> Font::getAltTypes(Unigram unigram) {
	std::set<Unigram> aliases;
	// Aliases can be chained, so aliasMap may describe a tree.
	// First find the root...
	while (aliasMap.count(unigram) > 0) {
		unigram = aliasMap.at(unigram);
	}
	// ...and then recursively find all aliases that lead to this root.
	findAliases(aliases, unigram);
	return aliases;
}

// Recursive helper function
void Font::findAliases(std::set<Unigram> &aliases, Unigram node) {
	aliases.insert(node);
	for (std::map<Unigram, Unigram>::iterator it = aliasMap.begin();
	     it != aliasMap.end(); ++it) {
		if (it->second.equals(node)) {
			findAliases(aliases, it->first);
		}
	}
}

std::set<Unigram> Font::getAllUnigrams() {
	std::set<Unigram> allUnigrams;
	for (std::map<Unigram, Unigram>::iterator it = aliasMap.begin();
	     it != aliasMap.end(); ++it) {
		allUnigrams.insert(it->first);
	}
	for (std::map<Unigram, int>::iterator it = unigramMap.begin();
	     it != unigramMap.end(); ++it) {
		allUnigrams.insert(it->first);
	}
	return allUnigrams;
}

Font::type_signal_progress Font::signal_progress() {
	return m_signal_progress;
}

FontBox* Font::getBox(Glib::ustring character, int style, int var) {
	return getBox(Unigram(character, style, var));
}
FontBox* Font::getBox(Unigram unigram) {
	while (aliasMap.count(unigram) > 0) {
		unigram = aliasMap.at(unigram);
	}
	if (unigramMap.count(unigram) > 0) {
		int indx = unigramMap.at(unigram);
		return &fontBoxes[indx];
	} else {
		return NULL;
	}
}

int Font::getMaxVar() {
	int max = 0;
	for (std::map<Unigram, Unigram>::iterator it = aliasMap.begin();
	     it != aliasMap.end(); ++it) {
		if (it->first.var > max) {
			max = it->first.var;
		}
	}
	for (std::map<Unigram, int>::iterator it = unigramMap.begin();
	     it != unigramMap.end(); ++it) {
		if (it->first.var > max) {
			max = it->first.var;
		}
	}
	return max;
}

int Font::getMaxChrLen() {
	int max = 0;
	for (std::map<Unigram, Unigram>::iterator it = aliasMap.begin();
	     it != aliasMap.end(); ++it) {
		if (it->first.chr.size() > max) {
			max = it->first.chr.size();
		}
	}
	for (std::map<Unigram, int>::iterator it = unigramMap.begin();
	     it != unigramMap.end(); ++it) {
		if (it->first.chr.size() > max) {
			max = it->first.chr.size();
		}
	}
	return max;
}

// Helper class for the function below
std::vector<Box*> Boxline::getBoxes(Image *img) {
	BoxColumns boxColumns;
	std::vector<Box*> boxes;
	Gtk::TreeModel::Children::iterator rowit;
	Box *prevbox = NULL;
	for (rowit = startIt; rowit != endIt; ++rowit) {
		if ((*rowit)[boxColumns.character] != " ") {
			Box *box = new Box(rowit, img);
			if (prevbox) {
				prevbox->nextinline = box;
			}
			boxes.push_back(box);
			prevbox = box;
		} else {
			if (prevbox) {
				prevbox->followedbyspace = true;
			}
		}
	}
	return boxes;
}

// This is an insanely long function; sorry about that.
// I could/should probably break it into smaller subfunctions,
// but presently, I don't have the need for that.
// At least I have noted the separation of stages with large comments.
void Font::calculateNew(std::vector<Page*> &pages) {

	delete fontImage;
	numUnigrams = 0;
	unigramMap.clear();
	fontBoxes.clear();

   /* ************* SELECT REPRESENTATIVE LINES FROM THE BOOK ************** */

	m_signal_progress.emit(0,"Selecting representative lines.");

	// Could use unordered_map, if the compiler supported it...
	std::map<Unigram, int>::iterator unMapIt;
	std::map<std::pair<Unigram,Unigram>, int> bigramMap;
	std::map<std::pair<Unigram,Unigram>, int>::iterator biMapIt;

	std::vector<Unigram> unigramSet;
	
	std::vector<Boxline> boxlines;
	std::vector<Boxline>::iterator lineIt;
	std::vector<Boxline> selectedBoxlines[pages.size()];
	
	for (int i=0; i<pages.size(); i++) {
		Glib::RefPtr<Gtk::ListStore> boxListStore = pages.at(i)->getBoxListStore();

		Unigram prevUnigram;
		Boxline boxline(i);
		
		Gtk::TreeModel::Children::iterator rowit;
		for (rowit = boxListStore->children().begin();
		     rowit != boxListStore->children().end(); ++rowit)
		{
			if (!boxline.startIt) {
				boxline.startIt = rowit;
			}
			Glib::ustring character = (*rowit)[boxColumns.character];
			int style = (*rowit)[boxColumns.style];
			int var = (*rowit)[boxColumns.variant];
			bool degenerate = (*rowit)[boxColumns.degenerate];
			if (character == "\\n") {
				boxline.endIt = rowit;
				boxlines.push_back(boxline);
				boxline = Boxline(i);
			} else {
				//boxline.plainText += character;
				if (character != " " && !degenerate) {
					Unigram unigram(character, style, var);
					while (aliasMap.count(unigram) > 0) {
						unigram = aliasMap.at(unigram);
					}
					++unigramMap[unigram];
					boxline.unigrams.push_back(unigram);
					if (prevUnigram.exists) {
						std::pair<Unigram,Unigram> bigram = std::pair<Unigram,Unigram>(prevUnigram,unigram);
						++bigramMap[bigram];
						boxline.bigrams.push_back(bigram);
					}
					prevUnigram = unigram;
				} else {
					prevUnigram.exists = false;
				}
			}
		}
		boxline.endIt = boxListStore->children().end();
		boxlines.push_back(boxline);
	}

	// Shuffle the list, to avoid selecting too many lines from a few pages in the beginning.
	std::random_shuffle(boxlines.begin(), boxlines.end());

	// We now have a set of lines, and frequency maps of uni- and bigrams.
	// I want to select lines so that each unigram is included at least
	// MINNUMOFUNIGRAMS times, and similarly for bigrams.
	// Of course, for those n-grams that don't exist in so many places,
	// we want them all, so select all lines that contain any of them.
	// But first, let's mark the more common n-grams as having freq. -1...
	for (unMapIt = unigramMap.begin(); unMapIt != unigramMap.end(); unMapIt++) {
		if (unMapIt->second > MINNUMOFUNIGRAMS) {
			unMapIt->second = -1;
		}
		// Also build a vector of all unique unigrams.
		unigramSet.push_back(unMapIt->first);
	}
	for (biMapIt = bigramMap.begin(); biMapIt != bigramMap.end(); biMapIt++) {
		if (biMapIt->second > MINNUMOFBIGRAMS) {
			biMapIt->second = -1;
		}
	}
	// Then iterate over the lines, and select good lines. Do this in two runs!
	// In the first run, only select those with the rare n-grams.
	// After that, all the frequencies should be either 0 or negative.
	// If negative, we want to decrease them even further,
	// to below -MINNUMOFUNIGRAMS and -MINNUMOFBIGRAMS.
	int selected = 0;
	for (int run = 0; run < 2; run++) {
		for (lineIt = boxlines.begin(); lineIt != boxlines.end(); lineIt++) {
			bool shouldSelect = false;
			std::vector<Unigram>::iterator unigramIt;
			for (unigramIt = lineIt->unigrams.begin(); unigramIt != lineIt->unigrams.end(); unigramIt++) {
				if (run == 0 && unigramMap[*unigramIt] > 0 ||
				    run == 1 && unigramMap[*unigramIt] < 0 && unigramMap[*unigramIt] >= -MINNUMOFUNIGRAMS) {
					shouldSelect = true;
				}
			}
			std::vector<std::pair<Unigram,Unigram> >::iterator bigramIt;
			for (bigramIt = lineIt->bigrams.begin(); bigramIt != lineIt->bigrams.end(); bigramIt++) {
				if (run == 0 && bigramMap[*bigramIt] > 0 ||
				    run == 1 && bigramMap[*bigramIt] < 0 && bigramMap[*bigramIt] >= -MINNUMOFBIGRAMS) {
					shouldSelect = true;
				}
			}
			if (shouldSelect) {
				selectedBoxlines[lineIt->pageid].push_back(*lineIt);
				selected++;
				// For each n-gram in the selected line, count down the frequency in the maps:
				for (unigramIt = lineIt->unigrams.begin(); unigramIt != lineIt->unigrams.end(); unigramIt++) {
					--unigramMap[*unigramIt];
				}
				for (bigramIt = lineIt->bigrams.begin(); bigramIt != lineIt->bigrams.end(); bigramIt++) {
					--bigramMap[*bigramIt];
				}
				// Clear the line's n-gramslists, so as to avoid selecting it again
				lineIt->unigrams.clear();
				lineIt->bigrams.clear();
			}
		}
	}

	std::cout << "Total number of lines: " << boxlines.size() << " Selected: " << selected << std::endl;

	// Sort the list of unique unigrams.
	std::sort(unigramSet.begin(), unigramSet.end());

	// Store the size of unigramSet:
	numUnigrams = unigramSet.size();
	
	// Reuse the frequency map as a map from unigram to its index in unigramSet
	for (int i = 0; i < numUnigrams; ++i) {
		unigramMap[unigramSet.at(i)] = i;
	}

	
	/* ************* CREATING AVERAGE IMAGES AND ALIGNING BOXES ************** */

	// So, we now have:
	//  std::vector<Unigram> unigramSet of size numUnigrams
	//  std::map<Unigram, int> unigramMap
	//  std::vector<Boxline> selectedBoxlines[] of len pages.size()

	std::vector<Box*> allBoxes;
	std::list<Box*> glyphLines;
	Image* unigramImgs[numUnigrams];
	Box* refBoxes[numUnigrams];
	int numBoxesAdded[numUnigrams];
	std::vector<float> lefts[numUnigrams];
	std::vector<float> rights[numUnigrams];

	for (int i=0; i<numUnigrams; ++i) {
		unigramImgs[i]=NULL;
		refBoxes[i]=NULL;
	}
	
	// Iterate through the pages and their selected boxlines
	for (int i = 0; i < pages.size(); ++i) {
		std::ostringstream strstream;
		strstream << "Processing boxes on page " << i << ".";

		// Maybe the page should load the pixbuf instead; something like this:
		//		pages.at(i-1)->decachePixbuf();
		//		Glib::RefPtr<Gdk::Pixbuf> pagePixbuf = pages.at(i)->getPixbuf();
		// But now I do like this instead:
		Image img = Image(pages.at(i)->getFilename());
		
		m_signal_progress.emit(i/(float)pages.size(),strstream.str());

		for (lineIt = selectedBoxlines[i].begin(); lineIt != selectedBoxlines[i].end(); ++lineIt) {
			// Update the progress here, to avoid unresponsive window
			//m_signal_progress.emit(i/(float)pages.size(),strstream.str());

			//std::cout << "Looking at a new line..." << std::endl;
			std::vector<Box*> boxes = lineIt->getBoxes(&img);
			
         glyphLines.push_back(*boxes.begin());
			
			for (std::vector<Box*>::iterator it = boxes.begin(); it != boxes.end(); ++it) {

				// Yay! We have a box!
				Box *box = *it;
				if (box->dubious) {
					continue;
				}
				
				Unigram unigram = box->unigram();
				while (aliasMap.count(unigram) > 0) {
					unigram = aliasMap.at(unigram);
				}
				int unigramId = unigramMap.at(unigram);
				box->indx = unigramId;
				
				if (!refBoxes[unigramId]) {
					// We haven't worked with this unigram yet.
					//	std::cout << "Creating a new image for unigram " << unigramId << std::endl;
					//	std::cout << "I.e. unigram " << unigram.style << unigram.chr << unigram.var << std::endl;
					Image *unigramImg = new Image(box->width()+100,box->height()+100);
					unigramImgs[unigramId] = unigramImg;
					for (int x=0; x<unigramImg->width(); ++x) {
						for (int y=0; y<unigramImg->height(); ++y) {
							unigramImg->setpixel(x, y, box->pixel(x - 50, y - 50));
						}
					}
					numBoxesAdded[unigramId] = 1;
					Box *refBox = new Box(unigram, 50, 50, box->width(), box->height(), unigramImg);
					refBox->setdisps(0,0);
					refBoxes[unigramId] = refBox;
					box->setdisps(0, 0);
					lefts[unigramId].push_back(0);
					rights[unigramId].push_back(box->width());
				} else {
					// We have worked with this unigram before, so align the box to the average image!
					float xdisp = 0, ydisp = 0;
					//std::cout << "Comparing two pairs of unigram " << unigram.style << unigram.chr << unigram.var << std::endl;
					float corr = refBoxes[unigramId]->finddisplacement(box, xdisp, ydisp);
					//float corr = refBoxes[unigramId]->finddisplacement(box, xdisp, ydisp, -2, 2, -2, 2);
					//std::cout << corr << "=?" << corrb << " " << round(xdisp) << "=?" << round(-xdispb) << " " << round(ydisp) << "=?" << round(-ydispb) << std::endl;
					xdisp = -xdisp;
					ydisp = -ydisp;
					box->setdisps(xdisp, ydisp);
					lefts[unigramId].push_back(xdisp);
					rights[unigramId].push_back(xdisp + box->width());
					Image *unigramImg = unigramImgs[unigramId];
					for (int x=0; x<unigramImg->width(); ++x) {
						for (int y=0; y<unigramImg->height(); ++y) {
							float oldpixel = unigramImg->pixel(x,y);
							oldpixel *= numBoxesAdded[unigramId];
							unigramImg->setpixel(x, y, (oldpixel + box->pixel(x-50-(int)round(xdisp), y-50-(int)round(ydisp)))/(numBoxesAdded[unigramId]+1));
						}
					}
					++numBoxesAdded[unigramId];
					if (numBoxesAdded[unigramId] < 10 || numBoxesAdded[unigramId] % 50 == 0) {
						refBoxes[unigramId]->invalidateTransformCache();
					}
				}
				allBoxes.push_back(box);
			}
		}
	}

	// Adjust the reference box's left and right to agree with the mean values
	for (int i=0; i<numUnigrams; ++i) {
		refBoxes[i]->addleft(median(lefts[i]));
		refBoxes[i]->setwidth(median(rights[i]) - median(lefts[i]));       
		//refBoxes[i]->addleft(median(lefts[i], 1));
		//refBoxes[i]->setwidth(median(rights[i], 0) - median(lefts[i], 1));       
		refBoxes[i]->setdisps(0, 0);
	}
	
	// Set all displacements relative to the newly adjusted reference boxes
	for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
      (*it)->setdisps((*it)->xdisp() - median(lefts[(*it)->indx]), (*it)->ydisp());
	}

	
	m_signal_progress.emit(1,"Post-processing.");
	
	/* ************** ADJUST YSHIFTS *************** */
	
	float *yshift;
   yshift=adjust_yshift(glyphLines);

	
   /* ************** CALCULATING BEARINGS *************** */
	
	// Okay, all boxes have been aligned and included in allBoxes!
	// The next step is to calculate the distances between boxes.
	// (This distance is the sum of the left box's right bearing and the right box's left bearing,
	// which are the values we ultimately want to calculate.)

	Matrix<float> avgDist(numUnigrams,numUnigrams);
   Matrix<float> distVar(numUnigrams,numUnigrams);
   Matrix<int> numBigrams(numUnigrams,numUnigrams);
	std::vector<float> lbear(numUnigrams);
	std::vector<float> rbear(numUnigrams);
	
	// Set preliminary values
	for (int i=0; i<numUnigrams; ++i) {
		lbear[i] = 0;
		rbear[i] = refBoxes[i]->width();
	}
	
	// Calculate averages
   for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
      if ((*it)->nextinline && !(*it)->followedbyspace &&
          !(*it)->dubious && !(*it)->nextinline->dubious) {
         int i = (*it)->indx;
			int j = (*it)->nextinline->indx;
			float distance = ((*it)->nextinline->left() - (*it)->nextinline->xdisp()) - ((*it)->left() - (*it)->xdisp());
         numBigrams(i,j) += 1;
         avgDist(i,j) += distance;
      }
   }
   for (int j=0; j<numUnigrams; j++) {
      for (int i=0; i<numUnigrams; i++) {
         if (numBigrams(i,j) > 0) {
            avgDist(i,j) /= numBigrams(i,j);
         }
      }
   }

	// Calculate variance
	for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
		if ((*it)->nextinline && !(*it)->followedbyspace &&
		    !(*it)->dubious && !(*it)->nextinline->dubious) {
			int i = (*it)->indx;
			int j = (*it)->nextinline->indx;
			float distance = ((*it)->nextinline->left() - (*it)->nextinline->xdisp()) - ((*it)->left() - (*it)->xdisp());
			distVar(i,j) += square(distance - avgDist(i,j));
		}
	}
	//  std::cout << "Variance: " << std::endl;
	for (int j=0; j<numUnigrams; j++) {
	//	     std::cout << unigramSet[j].chr << " ";
		for (int i=0; i<numUnigrams; i++) {
			if (numBigrams(i,j)>0) {
				if (numBigrams(i,j)==1) {
					distVar(i,j)=1; // Or what? I just take a largish number, because only one measurement is rather bad.
				} else {
					distVar(i,j) /= (numBigrams(i,j) - 1);
				}             
			}
			//        std::cout << distVar(i,j) <<  " ";
		}
		//      std::cout << std::endl;
	}

	// Assign the unknowns to sets
	int rbearset[numUnigrams];
	int lbearset[numUnigrams];
	for (int i=0; i<numUnigrams; i++) {
		rbearset[i]=0; // Set 0 is special: it means the value can't be known; this is the default, unless shown otherwise with checkset().
		lbearset[i]=0;
	}
	int numofsets=1;
	for (int i=0; i<numUnigrams; i++) {
		if (lbearset[i]==0) {
			checklset(numBigrams, lbearset, rbearset, i, numofsets);
			if (lbearset[i]==numofsets) {
				numofsets++;
			}
		}
	}

	// Make an artificial text with unseen bigrams
	std::vector<Unigram> unknownbearings;
	for (int i=0; i<numUnigrams; i++) {
		if (lbearset[i] != 1) {
			unknownbearings.push_back(Unigram("o",0,0));
		}
		if (rbearset[i] != 1 || lbearset[i] != 1) {
			unknownbearings.push_back(unigramSet[i]);
		}
		if (rbearset[i] != 1) {
			unknownbearings.push_back(Unigram("o",0,0));
		}
		if (rbearset[i] != 1 || lbearset[i] != 1) {
			unknownbearings.push_back(Unigram(" ",0,0));
		}
	}
	
	// Loop through the sets and solve the equations!
	for (int set=0; set<numofsets; set++) {

		int numoflunkn=0, numofrunkn=0;
		// Report some facts about the set
		std::cout << "Set " << set << ":";
		std::cout << std::endl << "  Right bearing: ";
		for (int i=0; i<numUnigrams; i++) {
			if (lbearset[i]!=set && rbearset[i]==set) {
				std::cout << unigramSet[i].chr << " ";
				numofrunkn++;
			}
		}
		std::cout << std::endl << "  Both bearings: ";
		for (int i=0; i<numUnigrams; i++) {
			if (lbearset[i]==set && rbearset[i]==set) {
				std::cout << unigramSet[i].chr << " ";
				numoflunkn++;
				numofrunkn++;
			}
		}
		std::cout << std::endl << "  Left  bearing: ";
		for (int i=0; i<numUnigrams; i++) {
			if (lbearset[i]==set && rbearset[i]!=set) {
				std::cout << unigramSet[i].chr << " ";
				numoflunkn++;
			}
		}
		std::cout << std::endl;

		if (set>0) { // As I said, set 0 is special.

			// Create the unknown vector (i.e. pointers to what the unknowns actually are)
			int unknownof[numoflunkn+numofrunkn]; // Array pointing to which character the unknown pertains to.
			int numofunkn=0;
			for (int i=0; i<numUnigrams; i++) {
				if (rbearset[i]==set) {
					unknownof[numofunkn++]=i;
					//std::cout << characters[i] << " ";
				}
			}
			for (int i=0; i<numUnigrams; i++) {
				if (lbearset[i]==set) {
					unknownof[numofunkn++]=i;
					//std::cout << characters[i] << " ";
				}
			}
			//std::cout << std::endl;
			// (Now numofunkn=numoflunkn+numofrunkn)

			// Count number of data for this set (pairs where both rbear and lbear pertain to this set)
			int numofpairs=0;
			for (int i=0; i<numUnigrams; i++) {
				if (rbearset[i]==set) {
					for (int j=0; j<numUnigrams; j++) {
						if (lbearset[j]==set && numBigrams(i,j)>0) {
							numofpairs++;
						}
					}
				}
			}

			// Create A, B, W and X
			Sparsematrix<int> A(numofunkn,numofpairs+1);
			float B[numofpairs+1];
			float W[numofpairs+1]; // This represents a diagonal matrix.
			float *X;
			numofpairs=0; // (Use it as a counter)
			for (int i=0; i<numofrunkn; i++) {
				for (int j=0; j<numoflunkn; j++) {
					int x=unknownof[i];
					int y=unknownof[numofrunkn+j];
					if (numBigrams(x,y)>0) {
						A.setrow(numofpairs,i,numofrunkn+j);
						B[numofpairs]=avgDist(x,y);
						if (distVar(x,y)==0)
							W[numofpairs]=1; // Or something
						else
							W[numofpairs]=std::min((float)1000,1/distVar(x,y));
						numofpairs++;
					}
				}
			}
			// numofpairs has got its old value back now. In the last row, add an "anchor":
			A.setrow(numofpairs,numofrunkn);
			B[numofpairs]=0;
			W[numofpairs]=1000;

			X=solveLES(A,B,W);

			// I think it is a good idea to shift the found bearings so that the median value for
			// the left bearing is 0. So find the median...
			std::vector<float> leftbearings;
			for (int j=numofrunkn; j<numofunkn; j++) {
				leftbearings.push_back(X[j]);
			}
			float leftbearingmedian = median(leftbearings);
			
			// And finally save the achieved values:
			for (int j=0; j<numofrunkn; j++) {
				rbear[unknownof[j]] = X[j] + leftbearingmedian;
			}
			for (int j=numofrunkn; j<numofunkn; j++) {
				lbear[unknownof[j]] = X[j] - leftbearingmedian;
			}

			delete X;
		}
	}
/*
    std::cout << std::endl << "Kerning table: " << std::endl;
    for (int j=0; j<numUnigrams; j++) {
       for (int i=0; i<numUnigrams; i++) {
          float kern=avgDist(i,j)-(rbear[i]+lbear[j]);
          if (numBigrams(i,j)>0 && rbearset[i]==lbearset[j] && fabs(kern)>1.0)
             std::cout << unigramSet[i].chr << " " << unigramSet[j].chr << " " << (rbear[i]+lbear[j])-avgDist(i,j) << std::endl;
       }
    }
*/

	/************** MORE WORK ON DISTANCE DEVIANCE ***************/

	std::vector<float> ldev;
	std::vector<float> rdev;
	std::vector<float> ldevcount;
	std::vector<float> rdevcount;
	ldev.resize(numUnigrams, 0.0);
   rdev.resize(numUnigrams, 0.0);
	ldevcount.resize(numUnigrams, 0);
   rdevcount.resize(numUnigrams, 0);

	// Calculate deviances of the distances compared to rbear + lbear
	for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
		if ((*it)->nextinline && !(*it)->followedbyspace &&
		    !(*it)->dubious && !(*it)->nextinline->dubious) {
			int i = (*it)->indx;
			int j = (*it)->nextinline->indx;
			float distance = ((*it)->nextinline->left() - (*it)->nextinline->xdisp()) - ((*it)->left() - (*it)->xdisp());
			rdev[i] += square(distance - (rbear[i]+lbear[j]));
			ldev[j] += square(distance - (rbear[i]+lbear[j]));
			rdevcount[i]++;
			ldevcount[j]++;
		}
	}
   for (int i=0; i<numUnigrams; i++) {
		if (ldevcount[i] > 0) {
  			ldev[i] = sqrt(ldev[i]/ldevcount[i]);
		} else {
			ldev[i] = 0;
		}
		if (rdevcount[i] > 0) {
  			rdev[i] = sqrt(rdev[i]/rdevcount[i]);
		} else {
			rdev[i] = 0;
		}
   }

	// How large are the spaces really?
	std::vector<float> spaces;
	for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
      if ((*it)->nextinline && (*it)->followedbyspace &&
          !(*it)->dubious && !(*it)->nextinline->dubious) {
         int i = (*it)->indx;
			int j = (*it)->nextinline->indx;
			if (rbearset[i] != 0 && rbearset[i] == lbearset[j]) {
				float distance = ((*it)->nextinline->left() - (*it)->nextinline->xdisp()) - ((*it)->left() - (*it)->xdisp()) - (rbear[i] + lbear[j]);
				spaces.push_back(distance);
				// It is interesting to analyze these values; a histogram for example would show
				// spikes in discrete intervalls, representing the empty types of fixed width
				// which were used to space the text.
				//std::cout << "Space size: " << (int)distance << std::endl;
			}
      }
   }
	minspace = median(spaces, 0.01);
	midspace = median(spaces);
	maxspace = median(spaces, 0.95);

	
   /************** FINAL STAGES OF POST PROCESSING ***************/

   fontImage = new Image(TIFFWIDTH,TIFFHEIGHT);
   int boxx=50, boxy=50;

	// Find maximum height for all glyphs.
   int miny=0, maxy=0;
	for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
		if (!(*it)->dubious) {
			int i = (*it)->indx;
			if ((*it)->ydisp() - yshift[i]<miny) {
				miny=(int)floor((*it)->ydisp() - yshift[i]);
			}
			if ((*it)->height() + (*it)->ydisp() - yshift[i]>maxy) {
				maxy=(int)ceil((*it)->height() + (*it)->ydisp() - yshift[i]);
			}
		}
	}

	linespacing = maxy - miny;

   for (int i=0; i<numUnigrams; i++) {

      int minx=0, maxx=0;
		for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
			if (!(*it)->dubious && (*it)->indx == i) {
            if ((*it)->xdisp() < minx) {
               minx = (int)floor((*it)->xdisp());
				}
            if ((*it)->width()+(*it)->xdisp() > maxx) {
               maxx = (int)ceil((*it)->width() + (*it)->xdisp());
				}
         }
      }

      if (boxx+maxx-minx>TIFFWIDTH-50) {
         boxy+=maxy-miny+10;
         if (boxy+maxy-miny+50>TIFFHEIGHT) {
            std::cerr << "Oops! Increase TIFFHEIGHT." << std::endl;
            std::exit(1);
         }
         boxx=50;
      }

      for (int y=0; y<maxy-miny; y++) {
         for (int x=0; x<maxx-minx; x++) {
         	(*fontImage)(boxx+x, boxy+y) = refBoxes[i]->pixel( x + minx, y + (int)round(yshift[i]) + miny );
         }
      }

      FontBox newbox(refBoxes[i]->unigram(), boxx-minx, boxy, refBoxes[i]->width(), maxy-miny, fontImage,
                     lbear[i], rbear[i], ldev[i], rdev[i]);
      //newbox.indx=i;
      //newbox.setdisps(0,0);
      fontBoxes.push_back(newbox);

      boxx+=maxx-minx+10;

   }

   fontImage->crop_bottom(boxy+maxy-miny+50);
	
/*
	// In case we want to see how the averaged images look: 
	for (int i=0; i<numUnigrams; ++i) {
		unigramImgs[i]->setpixel(refBoxes[i]->left(),refBoxes[i]->top()-0,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left(),refBoxes[i]->top()-1,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left(),refBoxes[i]->top()-2,1);
		unigramImgs[i]->setpixel(refBoxes[i]->right(),refBoxes[i]->top()-0,1);
		unigramImgs[i]->setpixel(refBoxes[i]->right(),refBoxes[i]->top()-1,1);
		unigramImgs[i]->setpixel(refBoxes[i]->right(),refBoxes[i]->top()-2,1);

		unigramImgs[i]->setpixel(refBoxes[i]->left() - lbear[i],refBoxes[i]->bot()+0,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left() - lbear[i],refBoxes[i]->bot()+1,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left() - lbear[i],refBoxes[i]->bot()+2,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left() + rbear[i],refBoxes[i]->bot()+0,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left() + rbear[i],refBoxes[i]->bot()+1,1);
		unigramImgs[i]->setpixel(refBoxes[i]->left() + rbear[i],refBoxes[i]->bot()+2,1);

		std::stringstream ss;
		ss << "/home/johan/test" << i << ".png";
		unigramImgs[i]->savepng(ss.str());
		
	}
*/

	//typeset(unknownbearings);
		
	// Clean up
	for (int i=0; i<numUnigrams; i++) {
		delete refBoxes[i];
		delete unigramImgs[i];
	}
	for (std::vector<Box*>::iterator it = allBoxes.begin(); it != allBoxes.end(); it++ ) {
      delete (*it);
	}

	m_signal_progress.emit(0,"");
}


// Two recursive functions to mark all bearings in a set.
void Font::checklset(Matrix<int>& numBigrams, int lbearset[], int rbearset[], int index, int setnum) {
   for (int x=0; x<numBigrams.width(); x++) {
      if (numBigrams(x,index)>0) {
         lbearset[index]=setnum;
         if (rbearset[x]==0)
            checkrset(numBigrams,lbearset,rbearset,x,setnum);
      }
   }
}
void Font::checkrset(Matrix<int>& numBigrams, int lbearset[], int rbearset[], int index, int setnum) {
   for (int y=0; y<numBigrams.height(); y++) {
      if (numBigrams(index,y)>0) {
         rbearset[index]=setnum;
         if (lbearset[y]==0)
            checklset(numBigrams,lbearset,rbearset,y,setnum);
      }
   }
}

// And a similar function for ysets:     
void Font::checkyset(Matrix<int>& numBigrams, int set[], int index, int setnum) {
   for (int x=0; x<index; x++) {
      if (numBigrams(x,index)>0) {
         if (set[x]==0) {
            set[x]=setnum;
            checkyset(numBigrams, set, x, setnum);
         } else if (set[x]!=setnum) {
            std::cout << "Hm, this shouldn't happen, actually." << std::endl;
         }
      }
   }
   for (int y=index+1; y<numBigrams.height(); y++) {
      if (numBigrams(index,y)>0) {
         if (set[y]==0) {
            set[y]=setnum;
            checkyset(numBigrams, set, y, setnum);
         } else if (set[y]!=setnum) {
            std::cout << "Hm, this shouldn't happen, actually." << std::endl;
         }
      }
   }
}

float* Font::solveLES(Sparsematrix<int>& A, float B[], float W[]) {

//          std::cout << "A=";
//          A.print();
//          std::cout << "B=[";
          for (int j=0; j<A.height(); j++) {
//             std::cout << B[j] << "; ";
          }
//          std::cout << "];" << std::endl;
//          std::cout << "W=[";
          for (int j=0; j<A.height(); j++) {
//             std::cout << W[j] << "; ";
//W[j]=1;
          }
//          std::cout << "];" << std::endl;

          Matrix<float> ATWA(A.width(),A.width());
          for (int j=0; j<A.width(); j++) {
             for (int i=0; i<A.width(); i++) {
                float sum=0;
                for (int k=0; k<A.height(); k++) {
                   sum+=A(j,k)*W[k]*A(i,k);
                }
                ATWA(i,j)=sum;
             }
          }
//          std::cout << "ATWA=";
//          ATWA.print();

//          std::cout << "ATWB=[";
          float ATWB[A.width()];
          for (int j=0; j<A.width(); j++) {
             float sum=0;
             for (int k=0; k<A.height(); k++) {
                sum+=A(j,k)*W[k]*B[k];
             }
             ATWB[j]=sum;
//             std::cout << sum << "; ";
          }
//          std::cout << "];" << std::endl;


          // Cholesky factorization (in place!)
          for (int k=0; k<ATWA.width(); k++) {
             ATWA(k,k)=sqrt(ATWA(k,k));
             for (int i=k+1; i<ATWA.height(); i++) {
                ATWA(k,i)=ATWA(k,i)/ATWA(k,k);
             }
             for (int j=k+1; j<ATWA.width(); j++) {
                for (int i=0; i<k+1 && j==k+1; i++) {
                   ATWA(k+1,i)=0;
                }
                for (int i=k+1; i<ATWA.height(); i++) {
                   ATWA(j,i)=ATWA(j,i)-ATWA(k,i)*ATWA(k,j);
                }
             }

          }
//          std::cout << "L=";
//          ATWA.print();

          // Solve Ly=ATWb
//          std::cout << "Y=[";
          float Y[ATWA.width()];
          for (int j=0; j<ATWA.height(); j++) {
             float sum=0;
             for (int i=0; i<j; i++) {
                sum+=ATWA(i,j)*Y[i];
             }
             Y[j]=(ATWB[j]-sum)/ATWA(j,j);
//             std::cout << Y[j] << "; ";
          }
//          std::cout << "];" << std::endl;

          // Solve LTx=y
          float *X = new float[ATWA.height()];
          for (int j=ATWA.width()-1; j>=0; j--) {
             float sum=0;
             for (int i=ATWA.height()-1; i>j; i--) {
                sum+=ATWA(j,i)*X[i];
             }
             X[j]=(Y[j]-sum)/ATWA(j,j);
          }

//          std::cout << "X=[";
          for (int j=0; j<ATWA.height(); j++) {
//             std::cout << X[j] << "; ";
          }
//          std::cout << "];" << std::endl;

   return X;

}

float Font::median(std::vector<float> &v, float pos) {
   int size=v.size();
   if (size==0)
      return 0;
   int n = size * pos;
   nth_element(v.begin(), v.begin()+n, v.end());
   return v[n];
}

float* Font::adjust_yshift(std::list<Box*>& glyphlines) {

   float *yshift;
   int set[numUnigrams];
   int sets=0;

   // Alright, we now calculate yshifts, based, inter all, on the calculated slopes of the lines.
   // At the end, we calculate new slopes. Iterate this a couple of times:
   for (int iterations=0; iterations<3; iterations++) {

      Matrix<float> avg(numUnigrams,numUnigrams);
      Matrix<float> variance(numUnigrams,numUnigrams);
      Matrix<int> antal(numUnigrams,numUnigrams); // Number of pairs 
      Matrix<float> wantal(numUnigrams,numUnigrams); // Weighted 

      // Calculate averages of height differences between every pair of characters.
      float distance;
      std::list<Box*>::iterator it;
      for ( it=glyphlines.begin(); it != glyphlines.end(); it++ ) {
         for (Box *b=*it; b; b=b->nextinline) {
            for (Box *c=*it; c; c=c->nextinline) {
               if (b->indx < c->indx && !b->dubious && !c->dubious) {
                  float confidence=std::min(1.0, 100.0/fabs(((c->right()+c->left())/2-c->xdisp())-((b->right()+b->left())/2-b->xdisp()))); // 100 is a distance in pixels.
                  distance=(b->top() - b->ydisp() - b->lineslope*(b->right()+b->left())/2) - (c->top() - c->ydisp() - c->lineslope*(c->right()+c->left())/2);
                  avg(b->indx,c->indx) += distance*confidence;
                  wantal(b->indx,c->indx) += confidence;
                  antal(b->indx,c->indx) += 1;
               }
            }
//            std::cout << b->boxchar();
         }
//         std::cout << std::endl;
      }

//      std::cout << "Ydiffs:" << std::endl;
      for (int j=0; j<numUnigrams; j++) {
         for (int i=0; i<numUnigrams; i++) {
            if (wantal(i,j)>0.0) {
               avg(i,j)/=wantal(i,j);
//               std::cout << i << " " << j << " " << avg(i,j) << std::endl;
//               std::cout << characters[i]+characters[j] << " " << avg(i,j) << std::endl;
//               std::cout << " " << avg(i,j);
//               std::cout << "X";
            } else {
//               std::cout << "-";
            }
         }
//         std::cout << std::endl;
      }
//      std::cout << std::endl;

      // Calculate variance
      for ( it=glyphlines.begin(); it != glyphlines.end(); it++ ) {
         for (Box *b=*it; b; b=b->nextinline) {
            for (Box *c=*it; c; c=c->nextinline) {
               if (b->indx < c->indx && !b->dubious && !c->dubious) {
                  distance=(b->top() - b->ydisp() - b->lineslope*(b->right()+b->left())/2) - (c->top() - c->ydisp() - c->lineslope*(c->right()+c->left())/2);
                  variance(b->indx,c->indx)=variance(b->indx,c->indx)+(distance-avg(b->indx,c->indx))*(distance-avg(b->indx,c->indx));
//                  if ((distance-avg(b->indx,c->indx))*(distance-avg(b->indx,c->indx))>50) std::cout << " " << b->boxchar() << " " << c->boxchar() << " " << (distance-avg(b->indx,c->indx)) << std::endl;
               }
            }
//            std::cout << b->boxchar();
         }
//         std::cout << std::endl;
      }
      for (int j=0; j<numUnigrams; j++) {
         for (int i=0; i<j; i++) {
            if (wantal(i,j)>0) {
               if (wantal(i,j)<=1) {
                  variance(i,j)=1; // Or?
               } else {
                  variance(i,j)/=(wantal(i,j)-1);
               }             
            }
         }
      }

      if (iterations==0) {
         // It may be the case that two (or more) sets of characters never stand in the same line.
         // For example, if numerals are not used in the main body of the text, but only for pagination,
         // we can't know how they should align vertically when placed besides a letter.
         // Find these sets.
         for (int i=0; i<numUnigrams; i++) {
            set[i]=0; // Zero = not assigned yet.
         }
         for (int i=0; i<numUnigrams; i++) {
            if (set[i]==0) {
               sets++;
               set[i]=sets;
               checkyset(antal, set, i, sets);
            }
         }

         // Print the sets.
			/*
         std::cout << "Y-displacement sets:" << std::endl;
         for (int i=1; i<=sets; i++) {
            std::cout << "Set " << i << ": ";
            for (int j=0; j<numUnigrams; j++) {
               if (set[j]==i) {
                  //std::cout << unigramSet[j].chr << " ";
               }
            }
            std::cout << std::endl;
         }
         std::cout << std::endl;
			*/
      }

      // Count number of data
      int numofpairs=0;
      for (int j=0; j<numUnigrams; j++) {
         for (int i=0; i<j; i++) {
            if (wantal(i,j)>0)
               numofpairs++;
         }
      }

      // Create A, B, W and X
      Sparsematrix<int> A(numUnigrams,numofpairs+sets);
      float B[numofpairs+sets];
      float W[numofpairs+sets];
      numofpairs=0; // (Use it as a counter)
      for (int j=0; j<numUnigrams; j++) {
         for (int i=0; i<j; i++) {
            if (wantal(i,j)>0) {
               A.setrow(numofpairs,j,i,1,-1);
               B[numofpairs]=avg(i,j);
               if (variance(i,j)==0)
                  W[numofpairs]=1000; // Or something
               else
                  W[numofpairs]=std::min((float)1000,1/variance(i,j));
               numofpairs++;
            }
         }
      }

      // numofpairs has got its old value back now. In the last rows, add anchors:
      for (int i=1; i<=sets; i++) {
         int j=0;
         while (set[j]!=i) {
            j++;
         }
         A.setrow(numofpairs,j);
         B[numofpairs]=0;
         W[numofpairs]=1000;
         numofpairs++;
      }

      yshift=solveLES(A,B,W);
/*
      std::cout << "This is Yshift:" << std::endl;
      for (int i=0; i<numUnigrams; i++)
         std::cout << yshift[i] << std::endl;
         //std::cout << characters[i] << " " << yshift[i] << std::endl;
*/

      // Calculate slopes of the lines.
      for ( it=glyphlines.begin(); it != glyphlines.end(); it++ ) {
         int n=0;
         float sumx=0, sumxx=0, sumy=0, sumxy=0;
         for (Box *b=*it; b; b=b->nextinline) {
            float x=(b->left()+b->right())/2-b->xdisp();
            float y=b->top()-b->ydisp()+yshift[b->indx];
            sumx+=x;
            sumxx+=x*x;
            sumy+=y;
            sumxy+=x*y;
            n++;
         }
         float slope=(n*sumxy-sumy*sumx)/(n*sumxx-sumx*sumx);
         float yintercept=sumy/n-slope*sumx/n;
         for (Box *b=*it; b; b=b->nextinline) {
            b->lineslope=slope;
         }
         if (iterations>2) {
            for (Box *b=*it; b; b=b->nextinline) {
               float x=(b->left()+b->right())/2-b->xdisp();
               float y=b->top()-b->ydisp()+yshift[b->indx];
               float ress=slope*x+yintercept-y;
               if (square(ress)>100 && !b->dubious) {
                  b->dubious=true;
                  std::cout << "Dubious character (y-disp " << ress << "): " << b->to_string();
               }
            }
         }
      }
   } 

   return yshift;
}

int Font::getBoxHeight() {
	if (fontBoxes.size() > 0) {
		return fontBoxes[0].height();
	}
	return linespacing;
}

std::string Font::save(std::string baseFileName) {
	std::ostringstream strstream;
	if (fontImage) {
		strstream << "<font "; // path=\"" << baseFileName + ".png" << "\">" << std::endl;
		strstream << "minspace=\"" << minspace << "\" ";
		strstream << "midspace=\"" << midspace << "\" ";
		strstream << "maxspace=\"" << maxspace << "\" ";
		strstream << "linespacing=\"" << linespacing << "\">" << std::endl;
		fontImage->savepng(baseFileName + ".png");

		for (int i = 0; i < numUnigrams; ++i) {
			strstream << "<type c=\"" << Glib::Markup::escape_text(fontBoxes[i].unigram().chr) << "\" ";
			strstream << "s=\"" << fontBoxes[i].unigram().style << "\" ";
			strstream << "v=\"" << fontBoxes[i].unigram().var << "\" ";
			strstream << "l=\"" << fontBoxes[i].left() << "\" ";
			strstream << "r=\"" << fontBoxes[i].right() << "\" ";
			strstream << "t=\"" << fontBoxes[i].top() << "\" ";
			strstream << "b=\"" << fontBoxes[i].bot() << "\" ";
			strstream << "lb=\"" << fontBoxes[i].getLbear() << "\" ";
			strstream << "rb=\"" << fontBoxes[i].getRbear() << "\" ";
			strstream << "ld=\"" << fontBoxes[i].getLdev() << "\" ";
			strstream << "rd=\"" << fontBoxes[i].getRdev() << "\"/>" << std::endl;
		}
		for (std::map<Unigram,Unigram>::iterator it = aliasMap.begin();
		     it != aliasMap.end(); ++it) {
			strstream << "<type c=\"" << Glib::Markup::escape_text(it->first.chr) << "\" ";
			strstream << "s=\"" << it->first.style << "\" ";
			strstream << "v=\"" << it->first.var << "\" ";
			strstream << "targetchar=\"" << Glib::Markup::escape_text(it->second.chr) << "\" ";
			strstream << "targetstyle=\"" << it->second.style << "\" ";
			strstream << "targetvar=\"" << it->second.var << "\"/>" << std::endl;
		}
		strstream << "</font>" << std::endl;
	}
	return strstream.str();
}

void Font::typeset(Glib::ustring str) {
	Image img(1200,300);
	float xpos=50, ypos=20;
	
	for (Glib::ustring::iterator it = str.begin(); it != str.end(); ++it) {
		Glib::ustring chr = Glib::ustring(1,*it);
		if (chr == " ") {
			xpos += midspace;
		} else {
			int indx = unigramMap.at(Unigram(chr, 0, 0));
			xpos += fontBoxes[indx].getLbear();
			for (int x=0; x<fontBoxes[indx].width(); ++x) {
				for (int y=0; y<fontBoxes[indx].height(); ++y) {
					img(xpos+x,ypos+y) += fontBoxes[indx].pixel(x,y);
				}
			}
			xpos += fontBoxes[indx].getRbear();
		}
	}
	img.savepng("/home/johan/typeset.png");
}

void Font::typeset(std::vector<Unigram> unigrams) {
	Image img(1600,12000);
	Image img2(1600,12000);
	float xpos=50, ypos=20;
	
	for (std::vector<Unigram>::iterator it = unigrams.begin(); it != unigrams.end(); ++it) {
		Glib::ustring chr = it->chr;
		if (chr == " " && xpos < 1300) {
			xpos += midspace;
		} else if (chr == "\n" || chr == " " && xpos >= 1300) {
			xpos = 50;
			ypos += linespacing;
		} else {
			int indx = unigramMap.at(*it);
			xpos += fontBoxes[indx].getLbear();
			for (int x=0; x<fontBoxes[indx].width(); ++x) {
				for (int y=0; y<fontBoxes[indx].height(); ++y) {
					if (it->equals(Unigram("o",0,0))) {
						img(xpos+x,ypos+y) += fontBoxes[indx].pixel(x,y);
					} else {
						img2(xpos+x,ypos+y) += fontBoxes[indx].pixel(x,y);
					}
				}
			}
			xpos += fontBoxes[indx].getRbear();
		}
	}
	img.crop_bottom(ypos+linespacing+50);
	img2.crop_bottom(ypos+linespacing+50);
	img.savepng("/home/johan/typeset1.png");
	img2.savepng("/home/johan/typeset2.png");
}

void Font::typeset(Glib::RefPtr<Gtk::ListStore> boxList) {
	Image img(3000,9000);
	float xpos=50, ypos=20;

	bool shouldsyncx = true, shouldsyncy = true;
	
	for (Gtk::TreeModel::Children::iterator boxit=boxList->children().begin();
	     boxit != boxList->children().end(); boxit++) {
		Glib::ustring chr = (*boxit)[boxColumns.character];
		if (chr == "\\n") {
			shouldsyncy = true;
			shouldsyncx = true;
		} else if (chr == " ") {
			shouldsyncx = true;
		} else {
			if (shouldsyncx) {
				xpos = (*boxit)[boxColumns.left];
			}
			if (shouldsyncy) {
				ypos = (*boxit)[boxColumns.top];
			}
			shouldsyncx = false;
			shouldsyncy = false;
			int style = (*boxit)[boxColumns.style];
			int var = (*boxit)[boxColumns.variant];
			int indx = unigramMap.at(Unigram(chr, style, var));
			xpos += fontBoxes[indx].getLbear();
			for (int x=0; x<fontBoxes[indx].width(); ++x) {
				for (int y=0; y<fontBoxes[indx].height(); ++y) {
					img(xpos+x,ypos+y) += fontBoxes[indx].pixel(x,y);
				}
			}
			xpos += fontBoxes[indx].getRbear();
		}
	}
		
	img.savepng("/home/johan/typeset.png");
}

