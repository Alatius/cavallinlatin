/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * clusterer.h
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

#ifndef _CLUSTERER_H_
#define _CLUSTERER_H_

#include "common.h"
#include "box.h"

class DataPoint {
public:
	// Data
	Box box;
	double corr;
	// Used in clustering algorithm
	int cluster;
	bool visited;
	std::vector<double> features;
	Gtk::TreeModel::Children::iterator rowit;
	DataPoint();
	DataPoint(Box b, double c);
	void setFeaturesBoxVerticalPos();
	void setFeaturesBoxAppearance();
	static bool SortFallingCorr(const DataPoint* a, const DataPoint* b);
	static bool SortOnPage(DataPoint* a, DataPoint* b);
	static int clusterLines(std::vector<DataPoint*>& segments);
	static int RunDBScan(std::vector<DataPoint*>& vecNodes, double dblEpsilon = 10.0, int nMinPts = 2);
private:
	static bool GetNodesInRadius(std::vector<DataPoint*>& vecNodes, DataPoint* pt, double dblRadius, int nMinPts, std::vector<DataPoint*>& rgpNodesFound);
	static void ExpandCluster(std::vector<DataPoint*>& vecNodes, std::vector<DataPoint*>& rgp, int nCluster, double dblEpsilon, int nMinPts);
};

#endif // _CLUSTERER_H_

