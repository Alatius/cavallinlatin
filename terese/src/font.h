/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * font.h
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

#ifndef _FONT_H_
#define _FONT_H_

#include <set>
#include "page.h"
#include "box.h"
#include "font-box.h"
#include "image.h"
#include "box-tree-view.h"

class Boxline {
public:
	Boxline(int i) : pageid(i) {}
	//Glib::ustring plainText;
	std::vector<Unigram> unigrams;
	std::vector<std::pair<Unigram,Unigram> > bigrams;
	int pageid;
	Gtk::TreeModel::Children::iterator startIt;
	Gtk::TreeModel::Children::iterator endIt;
	std::vector<Box*> getBoxes(Image *img);
private:
};

class Font
{
public:

	Font();
	Font(Glib::ustring imgFilename, int minspace, int midspace, int maxspace, int linespaceing);
	void addType(Glib::ustring character, int style, int var, int left, int right, int top, int bottom, float lbear, float rbear, float ldev, float rdev);
	void addAlias(Glib::ustring character, int style, int var, Glib::ustring targetchr, int targetstyle, int targetvar);
	std::string save(std::string baseFileName);
	
	void calculateNew(std::vector<Page*> &pages);

	std::map<Unigram, Unigram> getAliasMap() { return aliasMap; }
	void setAliasMap(std::map<Unigram, Unigram> map) { aliasMap = map; }
	std::set<Unigram> getAllUnigrams();
	
	std::set<Unigram> getAltTypes(Unigram unigram);
	void findAliases(std::set<Unigram> &aliases, Unigram node);
	std::set<Unigram> getVarTypes(Unigram unigram);

	// Used by the OCR function:
	std::vector<FontBox> getFontBoxes() { return fontBoxes; }
	
	FontBox* getBox(Glib::ustring character, int style, int var);
	FontBox* getBox(Unigram unigram);

	int getMaxVar();
	int getMaxChrLen();
	int getMinSpace() { return minspace; }
	int getMaxSpace() { return maxspace; }
	int getLineSpacing() { return linespacing; }
	int getBoxHeight();
	
	void typeset(Glib::ustring str);
	void typeset(std::vector<Unigram> unigrams);
	void typeset(Glib::RefPtr<Gtk::ListStore> boxList);
	
	typedef sigc::signal< void, float, Glib::ustring > type_signal_progress;
	type_signal_progress signal_progress();
	
private:
	Image* fontImage;
	int numUnigrams;
	std::map<Unigram, Unigram> aliasMap; // Map unigram aliases to unigrams represented in the font.
	std::map<Unigram, int> unigramMap; // Map unigrams to glyph id in the font.
	std::vector<FontBox> fontBoxes;

	int minspace, midspace, maxspace, linespacing;
	
	BoxColumns boxColumns;
	float* solveLES(Sparsematrix<int>& A, float B[], float W[]);
	void checkrset(Matrix<int>& numBigrams, int lbearset[], int rbearset[], int index, int setnum);
	void checklset(Matrix<int>& numBigrams, int lbearset[], int rbearset[], int index, int setnum);
	void checkyset(Matrix<int>& numBigrams, int set[], int index, int setnum);
	float median(std::vector<float> &v, float pos = 0.5);
	float* adjust_yshift(std::list<Box*>& glyphlines);

	type_signal_progress m_signal_progress;

};

#endif // _FONT_H_

