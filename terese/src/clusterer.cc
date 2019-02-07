/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * clusterer.cc
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

#include "clusterer.h"

DataPoint::DataPoint() : box(Unigram(), 0, 0, 0, 0, NULL) {
	corr = 0.0;
	cluster = 0;
}

DataPoint::DataPoint(Box b, double c) : box(b), corr(c) {
	cluster = 0;
	setFeaturesBoxVerticalPos();
}

bool DataPoint::SortFallingCorr(const DataPoint* a, const DataPoint* b) {
	return a->corr > b->corr;
}

bool DataPoint::SortOnPage(DataPoint* a, DataPoint* b) {
	if (a->cluster == b->cluster) {
		return a->box.left() + a->box.right() < b->box.left() + b->box.right();
	}
	return a->box.top() + a->box.bot() < b->box.top() + b->box.bot();
}

void DataPoint::setFeaturesBoxVerticalPos() {
	features.clear();
	features.push_back((box.top()+box.bot())/2);
}

void DataPoint::setFeaturesBoxAppearance() {
	features.clear();
	features.push_back((box.right()-box.left())/10);
	features.push_back((box.bot()-box.top())/10);
	const int width = box.width(), height = box.height();
	double weightedxsum = 0, weightedysum = 0, pixelsum = 0;
	for (int y = 0; y < height; ++y) {
		for (int x = 0; x < width; ++x) {
			const double pix = box.pixel(x,y);
			pixelsum += pix;
			weightedxsum += pix*x;
			weightedysum += pix*y;
		}
	}
	int midx = weightedxsum / pixelsum;
	int midy = weightedysum / pixelsum;
	features.push_back(box.pixel(midx, midy));
	for (int dy = 1; dy < 20; dy++) {
		for (int dx = 1; dx < 20; dx++) {
			features.push_back(box.pixel(midx+dx, midy+dy));
			features.push_back(box.pixel(midx-dx, midy+dy));
			features.push_back(box.pixel(midx+dx, midy-dy));
			features.push_back(box.pixel(midx-dx, midy-dy));
		}
	}
	/*
	features.push_back(midx);
	features.push_back(midy);
	features.push_back(height);
	features.push_back(width);
	features.push_back(pixelsum);
	*/
}
/*
void DataPoint::setFeaturesBoxAppearance() {
	features.clear();
	features.push_back((box.right()-box.left())/10);
	features.push_back((box.bot()-box.top())/10);
	const int maxfeat = 10;
	const int width = box.width(), height = box.height();
	double pixsum = 0, rowsum[maxfeat+1], colsum[maxfeat+1];
	for (int i = 0; i <= maxfeat; ++i) {
		colsum[i] = 0;
		rowsum[i] = 0;
	}
	for (int y = 0; y < height; ++y) {
		for (int x = 0; x < width; ++x) {
			const double pix = box.pixel(x,y);
			const float xscaled = maxfeat*float(x)/width;
			const float yscaled = maxfeat*float(y)/height;
			colsum[int(xscaled)] += (int(xscaled)+1 - xscaled) * pix;
			colsum[int(xscaled)+1] += (xscaled - int(xscaled)) * pix;
			rowsum[int(yscaled)] += (int(yscaled)+1 - yscaled) * pix;
			rowsum[int(yscaled)+1] += (yscaled - int(yscaled)) * pix;
			pixsum += pix;
		}
	}
	//features.push_back(pixsum);
	for (int i = 0; i <= maxfeat; ++i) {
		features.push_back(colsum[i]/pixsum);
		features.push_back(rowsum[i]/pixsum);
	}
}

void DataPoint::setFeaturesBoxAppearance() {
	features.clear();
	const int width = box.width(), height = box.height();
	double pixsum = 0, expx = 0, expy = 0;
	for (int y = 0; y < height; ++y) {
		for (int x = 0; x < width; ++x) {
			const double pix = box.pixel(x,y);
			pixsum += pix;
			expx += x * pix;
			expy += y * pix;
		}
	}
	expx /= pixsum;
	expy /= pixsum;
	const int scale = 2, resolution = 20;
	std::vector<std::vector<double> > grid(resolution, std::vector<double>(resolution));
	for (int y = 0; y < height; ++y) {
		for (int x = 0; x < width; ++x) {
			const double pix = box.pixel(x,y);
			const int xscaled = int(resolution/2 + (x-expx)/scale);
			const int yscaled = int(resolution/2 + (y-expy)/scale);
			if (xscaled >= 0 && xscaled < resolution &&
			    yscaled >= 0 && yscaled < resolution ) {
				grid[xscaled][yscaled] += pix;
			}
		}
	}
	//Image img(resolution,resolution);
	for (int y = 0; y < resolution; ++y) {
		for (int x = 0; x < resolution; ++x) {
			//img(x,y) = grid[x][y] / (scale*scale);
			features.push_back(grid[x][y]);
		}
	}
	//img.savepng("/home/johan/test.png");
}
*/

bool DataPoint::GetNodesInRadius(std::vector<DataPoint*>& vecNodes, DataPoint* pt, double dblRadius, int nMinPts, std::vector<DataPoint*>& rgpNodesFound) {
	for (std::vector<DataPoint*>::const_iterator it = vecNodes.begin(); it != vecNodes.end(); it++) {
		double distance = 0.0;
		const int numfeats = std::min((*it)->features.size(), pt->features.size());
		for (int i = 0; i < numfeats; ++i) {
			distance += std::abs((*it)->features.at(i) - pt->features.at(i));
		}
		if (distance/numfeats < dblRadius) {
			rgpNodesFound.push_back(*it);
		}
	}
	return rgpNodesFound.size() >= nMinPts;
}

void DataPoint::ExpandCluster(std::vector<DataPoint*>& vecNodes, std::vector<DataPoint*>& rgp, int nCluster, double dblEpsilon, int nMinPts) {
	std::vector<DataPoint*> rgpNeighbourhood;
	for (int i = 0; i < rgp.size(); i++) {
		if (!rgp[i]->visited) {
			rgpNeighbourhood.push_back(rgp[i]);
			rgp[i]->visited = true;
		}
		rgp[i]->cluster = nCluster;
	}
	for (int i = 0; i < rgpNeighbourhood.size(); i++) {
		DataPoint* pNodeNear = rgpNeighbourhood[i];
		std::vector<DataPoint*> rgpNeighbourhood2;
		if (GetNodesInRadius(vecNodes, pNodeNear, dblEpsilon, nMinPts, rgpNeighbourhood2)) {
			for (int j = 0; j < (int)rgpNeighbourhood2.size(); j++) {
				DataPoint* pNode = rgpNeighbourhood2[j];
				if (!pNode->visited) {
					pNode->visited = true;
				}
				if (pNode->cluster == 0)	{
					pNode->cluster = nCluster;
					rgpNeighbourhood.push_back(pNode);
				}
			}
		}
	}
}

int DataPoint::RunDBScan(std::vector<DataPoint*>& vecNodes, double dblEpsilon, int nMinPts) {
	int nCluster = 1;
	for (std::vector<DataPoint*>::const_iterator it = vecNodes.begin(); it != vecNodes.end(); it++) {
		DataPoint* pNode = *it;
		if (!pNode->visited) {
			pNode->visited = true;
			std::vector<DataPoint*> rgpNeighbourhood;
			if (GetNodesInRadius(vecNodes, pNode, dblEpsilon, nMinPts, rgpNeighbourhood)) {
				ExpandCluster(vecNodes, rgpNeighbourhood, nCluster, dblEpsilon, nMinPts);
				nCluster++;
			}
		}
	}
	return nCluster;
}

int DataPoint::clusterLines(std::vector<DataPoint*>& segments) {
	int pageheight = 0;
	std::vector<int> boxheights;
	for (std::vector<DataPoint*>::iterator it = segments.begin();
	     it != segments.end(); ++it) {
		boxheights.push_back((*it)->box.bot() - (*it)->box.top());
		if (pageheight < (*it)->box.bot()) {
			pageheight = (*it)->box.bot();
		}
	}
	const int margin = 1.5 * median(boxheights);
	int boxesinrow[pageheight];
	for (int y = 0; y < pageheight; ++y) {
		boxesinrow[y] = 0;
	}
	for (std::vector<DataPoint*>::iterator it = segments.begin();
	     it != segments.end(); ++it) {
		for (int y = (*it)->box.top(); y <= (*it)->box.bot(); ++y) {
			++boxesinrow[y];
		}
	}
	int level = 0;
	bool arealeft;
	do {
		int valleyend, valleystart = -1;
		arealeft = false;
		for (int y = 0; y < pageheight; ++y) {
			if (boxesinrow[y] == level) {
				if (valleystart == -1) {
					valleystart = y;
				}
				valleyend = y;
			} else {
				if (valleystart >= 0) {
					for (int winy = valleystart - margin; winy <= valleyend + margin; ++winy) {
						if (winy >= 0 && winy < pageheight) {
							if (winy == (valleystart+valleyend)/2) {
								boxesinrow[winy] = 0;
							} else {
								boxesinrow[winy] = -1;
							}
						}
					}
					y = valleyend + margin;
					valleystart = -1;
				} else {
					if (boxesinrow[y] > level) {
						arealeft = true;
					}
				}
			}
		}
		++level;
	} while (arealeft);
	int prevline = 0;
	int cluster = 0;
	for (int y = 0; y <= pageheight; ++y) {
		if (y == pageheight || boxesinrow[y] == 0) {
			std::vector<int> linemids;
			for (std::vector<DataPoint*>::iterator it = segments.begin();
			     it != segments.end(); ++it) {
				const int mid = ((*it)->box.top()+(*it)->box.bot())/2;
				if (mid >= prevline && mid < y) {
					(*it)->cluster = cluster;
					linemids.push_back(mid);
				}
			}
			/* I get a segfault here... WHYYYYYY!? */
			if (linemids.size() > 0) {
				// If a segment that has not been assigned to this line nevertheless
				// protrudes over the line median center, split it.
				// This is an imperfect solution, as we don't look at the pixels...
				int linemedmid = median(linemids);
				for (std::vector<DataPoint*>::iterator it = segments.begin();
				     it != segments.end(); ++it) {
					const int width = (*it)->box.width();
					const int left = (*it)->box.left();
					const int top = (*it)->box.top();
					const int bot = (*it)->box.bot();
					if ((top+bot)/2 >= y && (*it)->box.top() < linemedmid) {
						(*it)->box = Box(Unigram(), left, top, width, y-top, NULL);
						(*it)->cluster = cluster;
						//segments.push_back(new DataPoint(Box(Unigram(), left, y, width, bot-y, NULL), 0));
						//segments.back()->cluster = cluster+1;
					} else if ((top+bot)/2 < prevline && (*it)->box.bot() > linemedmid) {
						(*it)->box = Box(Unigram(), left, top, width, prevline-top, NULL);
						//segments.push_back(new DataPoint(Box(Unigram(), left, prevline, width, bot-prevline, NULL), 0));
						//segments.back()->cluster = cluster;
					}
				}
			}
			
			++cluster;
			prevline = y;
		}
	}
	return cluster;
}
