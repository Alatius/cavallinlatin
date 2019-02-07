/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 3; tab-width: 3 -*-  */
/*
 * Terese
 * Copyright (C) 2013 Johan Winge <johan.winge@gmail.com>
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

#include "project.h"

Project::Project() :
   m_fileName(""),
	m_isModified(false),
	m_isParsingRTML(false)
{

	m_refTagTable = Gtk::TextBuffer::TagTable::create();
	m_refStylesListStore = Gtk::ListStore::create(styleColumns);
	m_refStylesListStore->signal_row_deleted().connect(sigc::mem_fun(*this, &Project::on_row_deleted) );
	m_refPagesListStore = Gtk::ListStore::create(pagesColumns);
	m_refPagesListStore->signal_row_deleted().connect(sigc::mem_fun(*this, &Project::on_row_deleted) );

	m_refDummyPage = new Page();
	Glib::RefPtr<Gtk::TextBuffer> tempTextBuffer = Gtk::TextBuffer::create(m_refTagTable);
	Glib::RefPtr<Gtk::ListStore> tempTreeModel = Gtk::ListStore::create(boxColumns);
	m_refDummyPage->setTextBuffer(tempTextBuffer);
	m_refDummyPage->setBoxListStore(tempTreeModel);
	m_refActivePage = m_refDummyPage;
	m_refCurrentPage = NULL;
	
	m_font = new Font();
	m_font->signal_progress().connect(sigc::mem_fun(m_signal_progress, &type_signal_progress::emit));

}

Project::~Project() {
	for (Gtk::TreeModel::Children::iterator rowit = m_refPagesListStore->children().begin();
	     rowit != m_refPagesListStore->children().end(); rowit++) {
		delete (*rowit)[pagesColumns.page];
	}
	delete m_refDummyPage;
}

void Project::open(const std::string& filename) {

	if (filename == "")
		return;
	
	Glib::RefPtr<Gio::DataInputStream> inputstream;
	try {
		Glib::RefPtr<Gio::File> teresefile = Gio::File::create_for_path(filename);
		if (teresefile && teresefile->query_exists()) {
			m_fileName = filename;
			// Set the current dir to where the terese file is. In this way, we
			// can open the right images, even if they are given as relative paths.
			chdir(teresefile->get_parent()->get_path().c_str());
			inputstream = Gio::DataInputStream::create(teresefile->read());
		}
	} catch (Glib::Exception &except) {
		throw std::string(except.what() + " (" + m_fileName + ")");
	} catch (...) {
		throw std::string("Unknown exception!");
	}

	if (!inputstream)
		return;
	
	std::string line;
	Glib::ustring contents;
	while (inputstream->read_line(line)) {
		contents += line + "\n";
	}
	inputstream->close();
	
	Glib::Markup::ParseContext context(*this);
	// This will repeatedly trigger the on_start_element callback
	context.parse(contents);
	context.end_parse();

}

void Project::createFont() {
	//delete m_font;
	//m_font = new Font();
	//m_font->signal_progress().connect(sigc::mem_fun(m_signal_progress, &type_signal_progress::emit));
	std::vector< Page* > pages;
	for (Gtk::TreeModel::Children::iterator rowit = m_refPagesListStore->children().begin();
	     rowit != m_refPagesListStore->children().end(); rowit++) {
		pages.push_back((*rowit)[pagesColumns.page]);
	}
	m_font->calculateNew(pages);
	setModified(true);
}

bool Project::isNamed() {
	return m_fileName!="";
}

std::string Project::filename() {
	return m_fileName;
}

Glib::RefPtr<Gtk::ListStore> Project::stylesListStore() {
	return m_refStylesListStore;
}

Glib::RefPtr<Gtk::ListStore> Project::pagesListStore() {
	return m_refPagesListStore;
}

Project::type_signal_modified Project::signal_modified() {
	return m_signal_modified;
}

Project::type_signal_progress Project::signal_progress() {
	return m_signal_progress;
}

Glib::RefPtr<Gtk::ListStore> Project::currentBoxList() {
	return m_refActivePage->getBoxListStore();
}

Glib::RefPtr<Gtk::TextBuffer> Project::currentTextBuffer() {
	return m_refActivePage->getTextBuffer();
}

Glib::RefPtr<Gdk::Pixbuf> Project::currentPixbuf() {
	return m_refActivePage->getPixbuf();
}

Image* Project::currentImage() {
	return m_refActivePage->getImage();
}

Font* Project::theFont() {
	return m_font;
}

bool Project::isModified() {
	return m_isModified;
}
	
void Project::setModified(bool status=true) {
	m_isModified = status;
	m_signal_modified.emit();
}

void Project::on_row_deleted(const Gtk::TreeModel::Path& path) {
   setModified(true);
}

void Project::on_row_changed(const Gtk::TreeModel::Path& path, const Gtk::TreeModel::iterator& iter) {
   setModified(true);
}

Page* Project::getActivePage() {
	return m_refActivePage;
}

// Called when project is read from file, and from Terese::showPage
void Project::setActivePage(Page* page) {
	if (page == NULL) {
		page = m_refDummyPage;
	}
	if (page != m_refActivePage) {
		m_refActivePage->decachePixbuf();
	}
	m_refActivePage = page;
}

void Project::appendStyle(int id, Glib::ustring name, Glib::ustring prefix, Glib::ustring htmltag,
                          Glib::ustring font, Glib::ustring background, Glib::ustring foreground,
                          Glib::ustring shortcut) {

	Glib::RefPtr<Gtk::TextBuffer::Tag> refTag = Gtk::TextBuffer::Tag::create(name);
	if (font!="") refTag->property_font_desc() = Pango::FontDescription(font);
	if (background!="") refTag->property_background() = background;
	if (foreground!="") refTag->property_foreground() = foreground;
	m_refTagTable->add(refTag); // Should the first tag (id=0) be added here?
	
	Gtk::TreeModel::Row row = *(m_refStylesListStore->append());
	row[styleColumns.id] = id;
	row[styleColumns.name] = name;
	row[styleColumns.prefix] = prefix;
	row[styleColumns.htmltag] = htmltag;
	row[styleColumns.font] = font;
	row[styleColumns.background] = background;
	row[styleColumns.foreground] = foreground;
	row[styleColumns.texttag] = refTag;
	row[styleColumns.shortcut] = shortcut;

	setModified(true);
}

int Project::styleOfText(const Gtk::TextBuffer::iterator& textit) {
	int style = 0;
	Gtk::TreeModel::Children children = m_refStylesListStore->children();
	for (Gtk::TreeModel::Children::iterator styleit = children.begin(); styleit != children.end(); ++styleit) {
		int id = (*styleit)[styleColumns.id];
		Glib::RefPtr<Gtk::TextBuffer::Tag> refTag = (*styleit)[styleColumns.texttag];
		if (textit.has_tag(refTag)) {
			style = style | id;
		}
	}
	return style;
}

std::set<Unigram> Project::unigramCandidates(Gtk::TextBuffer::iterator textit) {
	const int maxvar = m_font->getMaxVar();
	const int maxlength = m_font->getMaxChrLen();
	int i = 0;
	int style = styleOfText(textit);
	Glib::ustring chr = "";
	std::set<Unigram> candidates;
	do {
		chr += Glib::ustring(1,*textit);
		for (int var = 0; var <= maxvar; ++var) {
			Unigram unigram(chr, style, var);
			Box* box = m_font->getBox(unigram);
			if (box != NULL) {
				candidates.insert(unigram);
			}
		}
		++textit;
		++i;
	} while (i <= maxlength && styleOfText(textit) == style);
	return candidates;
}

std::set<Unigram> Project::allBoxUnigrams() {
	std::set<Unigram> unigrams = m_font->getAllUnigrams();
	for (Gtk::TreeModel::Children::iterator rowit=m_refPagesListStore->children().begin();
	     rowit != m_refPagesListStore->children().end(); rowit++) {
		Page* page = (*rowit)[pagesColumns.page];
		Glib::RefPtr<Gtk::ListStore> boxList = page->getBoxListStore();
		for (Gtk::TreeModel::Children::iterator boxit=boxList->children().begin();
		     boxit != boxList->children().end(); boxit++) {
			Unigram unigram = Unigram(boxit);
			if (unigram.chr != "\\n" && unigram.chr != " ") {
				unigrams.insert(Unigram(boxit));
			}
		}
	}
	return unigrams;
}

Page* Project::appendPage(std::string filename) {

	Page *page = new Page(filename);

	Glib::RefPtr<Gtk::ListStore> tempTreeModel = Gtk::ListStore::create(boxColumns);
	//tempTreeModel->signal_row_deleted().connect(sigc::mem_fun(*this, &Project::on_row_deleted) );
	//tempTreeModel->signal_row_changed().connect(sigc::mem_fun(*this, &Project::on_row_changed) );
	//row[pagesColumns.boxlist] = tempTreeModel;

	//Glib::RefPtr<Gdk::Pixbuf> tempPixbuf = Gdk::Pixbuf::create_from_file(filename);
	//row[pagesColumns.image] = tempImage;

	Glib::RefPtr<Gtk::TextBuffer> tempTextBuffer = Gtk::TextBuffer::create(m_refTagTable);
	//row[pagesColumns.textbuffer] = tempTextBuffer;
	//tempTextBuffer->set_modified(false);
	tempTextBuffer->signal_modified_changed().connect( sigc::bind<bool> ( sigc::mem_fun(*this, &Project::setModified), true) );

	page->setBoxListStore(tempTreeModel);
	page->setTextBuffer(tempTextBuffer);

	Gtk::TreeModel::Row row = *(m_refPagesListStore->append());
	row[pagesColumns.fullname] = filename;
	Glib::RefPtr<Gio::File> file = Gio::File::create_for_path(filename);
	row[pagesColumns.name] = file->get_basename();
	row[pagesColumns.page] = page;

	setModified(true);
	return page;
}

void Project::appendBox(Page* page, Glib::ustring character, int style, int var, bool deg, int left, int right, int top, int bottom, int correlation) {
	Gtk::TreeModel::Row boxrow = *(page->getBoxListStore()->append());
	boxrow[boxColumns.character] = character;
	boxrow[boxColumns.style] = style;
	boxrow[boxColumns.variant] = var;
	boxrow[boxColumns.degenerate] = deg;
	boxrow[boxColumns.correlation] = correlation;
	boxrow[boxColumns.left] = left;
	boxrow[boxColumns.right] = right;
	boxrow[boxColumns.top] = top;
	boxrow[boxColumns.bottom] = bottom;

	//setModified(true); // Doing this puts a strain on the signal system it seems, freezing the whole of Gnome(?!).
}

void Project::importRTMLFile(Page* page, std::string tifffilename) {
	
	const std::string suffixes[]={".rtml", ".txt"};
	std::string basefilename=tifffilename.substr(0,tifffilename.find_last_of("."));

	Glib::RefPtr<Gio::DataInputStream> rtmlstream;
	for (int i=0; i<2 && !rtmlstream; i++) {
		std::string rtmlfilename=basefilename+suffixes[i];
		try {
			Glib::RefPtr<Gio::File> rtmlfile = Gio::File::create_for_path(rtmlfilename);
			if (rtmlfile && rtmlfile->query_exists()) {
				rtmlstream = Gio::DataInputStream::create(rtmlfile->read());
			}
		} catch (Glib::Exception &except) {
			throw std::string(except.what() + " (" + rtmlfilename + ")");
		} catch (...) {
			throw std::string("Unknown exception!");
		}
	}

	if (!rtmlstream)
		return;

	std::string line;
	Glib::ustring contents;
	while (rtmlstream->read_line(line)) {
		contents+=line+"\n";
	}
	rtmlstream->close();
	contents="<rtml>"+contents+"</rtml>";

	Glib::Markup::ParseContext context(*this);
	m_refCurrentPage = page; 
	context.parse(contents);
	context.end_parse();
	m_refCurrentPage = NULL;
}

void Project::importBoxFile(Page* page, std::string tifffilename) {
	
	std::string boxfilename=tifffilename.substr(0,tifffilename.find_last_of("."))+".box";
	std::string txtfilename=boxfilename+".txt";

   Glib::RefPtr<Gio::DataInputStream> boxstream;
   try {
      Glib::RefPtr<Gio::File> boxfile = Gio::File::create_for_path(boxfilename);
		if (boxfile && boxfile->query_exists()) {
   		boxstream = Gio::DataInputStream::create(boxfile->read());
		}
   } catch (Glib::Exception &except) {
      throw std::string(except.what() + " (" + boxfilename + ")");
   } catch (...) {
      throw std::string("Unknown exception!");
   }

   Glib::RefPtr<Gio::DataInputStream> txtstream;
   try {
      Glib::RefPtr<Gio::File> txtfile = Gio::File::create_for_path(txtfilename);
		if (txtfile && txtfile->query_exists()) {
   		txtstream = Gio::DataInputStream::create(txtfile->read());
		}
   } catch (Glib::Exception &except) {
      throw std::string(except.what() + " (" + txtfilename + ")");
   } catch (...) {
      throw std::string("Unknown exception!");
   }

	if (!boxstream)
		return;

	Glib::ustring::iterator stringit;
	std::string line;
	Glib::ustring wholetext;

	if (txtstream) {
		while (txtstream->read_line(line)) {
			wholetext+=line+"\n";
		}
		txtstream->close();

		stringit = wholetext.begin();
	}

	std::string rawchar;
	int lastlft=0, lastrgt=1, lasttop=0, lastbot=1;
	int lft=0, rgt=0, top=0, bot=0, dummy;

	int imageHeight = page->getHeight();

	while (boxstream->read_line(line)) {

		line.erase(line.find_last_not_of(" \n\r\t")+1);
		std::stringstream strstream(line);
		int spacecount = std::count(line.begin(), line.end(), ' ');
		if (spacecount==4) {
			strstream >> rawchar >> lft >> bot >> rgt >> top; // Note, if rawchar is a Glib::ustring, this doesn't work in Windows!
		} else if (spacecount==5) {
			strstream >> rawchar >> lft >> bot >> rgt >> top >> dummy;
		} else {
			std::cout << "Warning: Ignoring possibly malformed line \"" << line << "\"" << std::endl;
		}

		top=imageHeight-top;
		bot=imageHeight-bot;
		
		if (txtstream) {
			Glib::ustring urawchar(rawchar);
			Glib::ustring::iterator charit = urawchar.begin();
			while (stringit!=wholetext.end() && (*stringit==' ' || *stringit=='\n')) {
				if (*stringit=='\n') {
					appendBox(page, "\\n", 0, 0, false, lastrgt, lastrgt+10, lasttop, lastbot);
				} else { // ' '
					if (lastrgt>lft)
						lastrgt=lft-10;
					appendBox(page, " ", 0, 0, false, lastrgt, lft, top, bot);
				}
				stringit++;
			}
			while (charit!=urawchar.end() && *charit==*stringit) {
				charit++;
				stringit++;
			}
			if (urawchar!="~" && charit!=urawchar.end()) {
				std::cout << "Warning: Lost sync of text file" << txtfilename << std::endl;
				txtstream.reset();
			}
		} else {
			// We have to guess where the spaces and linebreaks are. Sigh.
			if (lft<lastlft-30) { // && top>lastbot && lastbot!=0) {
				appendBox(page, "\\n", 0, 0, false, lastrgt, lastrgt+10, lasttop, lastbot);
			} //else if (lastrgt>1 && lft>lastrgt+10) {
			//	appendBox(page, " ", 0, 0, false, lastrgt, lft, top, bot);
			//}
		}

		Glib::ustring boxchar;
		int styles;
		parseStylePrefix(rawchar, boxchar, styles);

		appendBox(page, boxchar, styles, 0, false, lft, rgt, top, bot);

		lastlft=lft;
		lastrgt=rgt;
		lasttop=top;
		lastbot=bot;
	}
	boxstream->close();

	resolveStyleAmbiguities(page);
	
}

void Project::exportBoxFiles() {
	for (Gtk::TreeModel::Children::iterator rowit=m_refPagesListStore->children().begin();
			rowit != m_refPagesListStore->children().end(); rowit++) {
		Page* page = (*rowit)[pagesColumns.page];
		Glib::ustring tifffilename = (*rowit)[pagesColumns.fullname];
		std::string boxfilename = tifffilename.substr(0,tifffilename.find_last_of("."))+".box";
		std::string txtfilename = boxfilename+".txt";
		try {
			// Open the .box file
			Glib::RefPtr<Gio::File> boxfile = Gio::File::create_for_path(boxfilename);
			if(!boxfile) {
				std::cerr << "Could not save file. Gio::File::create_for_path() returned an empty RefPtr." << std::endl;
				return;
			}
			Glib::RefPtr<Gio::FileOutputStream> boxfilestream;
			if (boxfile->query_exists())
				boxfilestream = boxfile->replace(std::string(),true); // true = Make backup
			else
				boxfilestream = boxfile->create_file();
			if (!boxfilestream) {
				std::cerr << "Could not save file. Gio::File::create_file() returned an empty RefPtr." << std::endl;
				return;
			}
			Glib::RefPtr<Gio::DataOutputStream> boxoutfile = Gio::DataOutputStream::create(boxfilestream);

			// Open the .box.txt file
			Glib::RefPtr<Gio::File> txtfile = Gio::File::create_for_path(txtfilename);
			if(!txtfile) {
				std::cerr << "Could not save file. Gio::File::create_for_path() returned an empty RefPtr." << std::endl;
				return;
			}
			Glib::RefPtr<Gio::FileOutputStream> txtfilestream;
			if (txtfile->query_exists())
				txtfilestream = txtfile->replace(std::string(),true); // true = Make backup
			else
				txtfilestream = txtfile->create_file();
			if (!txtfilestream) {
				std::cerr << "Could not save file. Gio::File::create_file() returned an empty RefPtr." << std::endl;
				return;
			}
			Glib::RefPtr<Gio::DataOutputStream> txtoutfile = Gio::DataOutputStream::create(txtfilestream);
			std::ostringstream boxstrstream;
			std::ostringstream txtstrstream;
			int imageHeight = page->getHeight();
			page->decachePixbuf();
			Glib::RefPtr<Gtk::ListStore> boxList = page->getBoxListStore(); //(*rowit)[pagesColumns.boxlist];
			for (Gtk::TreeModel::Children::iterator boxit=boxList->children().begin();
              boxit != boxList->children().end(); boxit++) {
				Glib::ustring prefixedChar = generateStylePrefix((*boxit)[boxColumns.style]) +
					                          (*boxit)[boxColumns.character];
				if ((*boxit)[boxColumns.character] == "\\n") {
					txtstrstream << std::endl;
				} else if ((*boxit)[boxColumns.character] == " ") {
					txtstrstream << " ";
				} else {
					if ((*boxit)[boxColumns.degenerate] == false) {
						txtstrstream << prefixedChar;
					}
				}
				if ((*boxit)[boxColumns.degenerate] == false &&
				   (*boxit)[boxColumns.character] != " " &&
				    (*boxit)[boxColumns.character] != "\\n") {
					boxstrstream << prefixedChar << " ";
				//if ((*boxit)[boxColumns.character] != " ") {
				//	if ((*boxit)[boxColumns.character] == "\\n") {
				//		boxstrstream << "\t ";
				//	} else {
				//		boxstrstream << prefixedChar << " ";
				//	}
					//boxstrstream << (*boxit)[boxColumns.left]+3 << " ";
					//boxstrstream << (imageHeight - (*boxit)[boxColumns.bottom])+3 << " ";
					//boxstrstream << (*boxit)[boxColumns.right]-3 << " ";
					//boxstrstream << (imageHeight - (*boxit)[boxColumns.top])-3 << " 0" << std::endl;
					boxstrstream << (*boxit)[boxColumns.left] << " ";
					boxstrstream << (imageHeight - (*boxit)[boxColumns.bottom]) << " ";
					boxstrstream << (*boxit)[boxColumns.right] << " ";
					boxstrstream << (imageHeight - (*boxit)[boxColumns.top]) << " 0" << std::endl;
				}
			}
			boxoutfile->put_string(boxstrstream.str());
			boxoutfile->close();
			boxoutfile.reset();
			txtoutfile->put_string(txtstrstream.str());
			txtoutfile->close();
			txtoutfile.reset();
		} catch(const Glib::Exception& ex) {
			std::cerr << "Could not save file. Exception caught: " << ex.what() << std::endl; 
		}
	}
}

void Project::exportOCRopusLines() {
	for (Gtk::TreeModel::Children::iterator pagerowit = m_refPagesListStore->children().begin();
			pagerowit != m_refPagesListStore->children().end(); pagerowit++) {
		Page* page = (*pagerowit)[pagesColumns.page];
		Glib::ustring tifffullname = (*pagerowit)[pagesColumns.fullname];
		Glib::ustring tifffilename = (*pagerowit)[pagesColumns.name];
		std::string dirname = tifffullname.substr(0, tifffullname.size() - tifffilename.size() + tifffilename.find_first_of("."));
		Glib::RefPtr<Gio::File> refPageDir = Gio::File::create_for_path(dirname);
		try {
			if (refPageDir->make_directory_with_parents()) {

				Image* pageimg = page->getImage();
				Glib::RefPtr<Gtk::ListStore> liststore = page->getBoxListStore();
				Glib::ustring linetext;
				int linetop = page->getHeight();
				int lineleft = page->getWidth();
				int linebot = 0;
				int lineright = 0;
				int linecount = 0;
				for (Gtk::TreeModel::Children::iterator boxrowit = liststore->children().begin();
				     boxrowit != liststore->children().end(); ++boxrowit)
				{
					if ((*boxrowit)[boxColumns.character] != "\\n") {
						linetext += (*boxrowit)[boxColumns.character];
						linetop = std::min(linetop, int((*boxrowit)[boxColumns.top]));
						lineleft = std::min(lineleft, int((*boxrowit)[boxColumns.left]));
						linebot = std::max(linebot, int((*boxrowit)[boxColumns.bottom]));
						lineright = std::max(lineright, int((*boxrowit)[boxColumns.right]));
					} else {
						if (linetext.size() > 0) {
							const int linewidth = lineright - lineleft;
							const int lineheight = linebot - linetop;
							Box linebox(Unigram(), lineleft, linetop, linewidth, lineheight, pageimg);
							Image lineimg(linewidth, lineheight);
							lineimg.addbox(&linebox, 0, 0);
							char linename[4];
							sprintf(linename, "%04d", linecount);
							Glib::RefPtr<Gio::File> pngfile = refPageDir->get_child(std::string(linename) + ".png");
							lineimg.savepng(pngfile->get_path());
							Glib::RefPtr<Gio::File> txtfile = refPageDir->get_child(std::string(linename) + ".gt.txt");
							Glib::RefPtr<Gio::FileOutputStream> txtfilestream = txtfile->create_file();
							Glib::RefPtr<Gio::DataOutputStream> txtoutstream = Gio::DataOutputStream::create(txtfilestream);
							txtoutstream->put_string(linetext);
							txtoutstream->close();
							txtoutstream.reset();
							linecount++;
						}
						linetext = "";
						linetop = page->getHeight();
						lineleft = page->getWidth();
						linebot = 0;
						lineright = 0;
					}
				}
				page->decachePixbuf();
			} else {
				std::cerr << "Could not create path " << dirname << std::endl; 
			}
		} catch(const Glib::Exception& ex) {
			std::cerr << "Could not export OCRopus lines. Exception caught: " << ex.what() << std::endl; 
		}
	}
}

void Project::parseStylePrefix(Glib::ustring rawchar, Glib::ustring &boxchar, int &styles) {
	boxchar="";
	styles=0;
	bool foundPrefix;
	for (Glib::ustring::iterator strit = rawchar.begin(); strit!=rawchar.end(); ++strit) {
		foundPrefix=false;
		Gtk::TreeModel::Children children = m_refStylesListStore->children();
		for (Gtk::TreeModel::Children::iterator styleit = children.begin(); styleit != children.end(); ++styleit) {
			if ( Glib::ustring(1,*strit) == (*styleit)[styleColumns.prefix] ) {
				styles += (*styleit)[styleColumns.id];
				foundPrefix=true;
			}
		}
		if (!foundPrefix) {
			boxchar += (*strit);
		}
	}
}

Glib::ustring Project::generateStylePrefix(int styles) {
	Glib::ustring prefix = "";
	Gtk::TreeModel::Children children = m_refStylesListStore->children();
	for (Gtk::TreeModel::Children::iterator styleit = children.begin(); styleit != children.end(); ++styleit) {
		if (styles & (*styleit)[styleColumns.id]) {
			prefix += (*styleit)[styleColumns.prefix];
		}
	}
	return prefix;
}

/* Because some types, which are visually identical, can belong to different styles,
   there is often ambiguities when importing Tesseract boxes. For example, capital letters
   may be marked as either no style, or as small-caps, depending on the surrounding glyphs.
   We want to resolve this, by minimizing the number of style changes, especially inside words.*/
void Project::resolveStyleAmbiguities(Page* page) {
	Glib::RefPtr<Gtk::ListStore> boxlist = page->getBoxListStore();
	Gtk::TreeModel::Children children = boxlist->children();
	Gtk::TreeModel::Children::iterator rowit = children.begin();
	// Actually, the list of boxes may be empty, if we have tried to open an empty boxfile
	if (rowit == children.end()) {
		return;
	}
	// First, set style on individual tokens:
	while (rowit != children.end()) {
		styleToken(rowit, children.end());
	}
	// Then, fill in style on whitespace
	int rightstyle=0;
	rowit--;
	do {
		while (rowit != children.begin() &&
		       ((*rowit)[boxColumns.character] != " " && (*rowit)[boxColumns.character] != "\\n")) {
			rightstyle=(*rowit)[boxColumns.style];
			rowit--;
		}
		while (rowit != children.begin() &&
		       ((*rowit)[boxColumns.character] == " " || (*rowit)[boxColumns.character] == "\\n")) {
			(*rowit)[boxColumns.style] = (*rowit)[boxColumns.style] & rightstyle;
			rowit--;
		}
	} while (rowit != children.begin());

}

/* Recursive function, selecting the best choice of alternative styles for each char. */
bool Project::styleToken(Gtk::TreeModel::Children::iterator &rowit,
                         const Gtk::TreeModel::Children::iterator rowend,
                         const int branchdiffs, const int laststyle)
{
	static Gtk::TreeModel::Children::iterator endit;
	static int bestquality;
	if (laststyle<0) { // Is first time (root)	endit=rowit;
		bestquality=1000000;
	}
	if (rowit==rowend || (*rowit)[boxColumns.character] == " " || (*rowit)[boxColumns.character] == "\\n") {
		if (bestquality > branchdiffs) {
			bestquality = branchdiffs;
			// Let's temporarily set the following whitespace to the same style as the last char.
			Gtk::TreeModel::Children::iterator spaceit=rowit;
			while (spaceit!=rowend && ((*spaceit)[boxColumns.character] == " " || (*spaceit)[boxColumns.character] == "\\n")) {
				(*spaceit)[boxColumns.style]=std::max(0,laststyle);
				spaceit++;
			}
			endit = spaceit;
			if (laststyle < 0) {
				rowit=endit;
			}
			return true;
		} else {
			return false;
		}
	} else {
		if (bestquality < branchdiffs) {
			return false;
		}
		bool isbestbranch = false;
		std::set<Unigram> alttypes = m_font->getAltTypes(Unigram(rowit));
		for (std::set<Unigram>::iterator altit = alttypes.begin(); altit != alttypes.end(); ++altit) {
			const Unigram alttype = *altit;
			int diffs = branchdiffs;
			if (laststyle >= 0) {
				diffs += __builtin_popcount(laststyle ^ alttype.style);
			}
			rowit++;
			bool containsbestleaf = styleToken(rowit, rowend, diffs, alttype.style);
			rowit--;
			if (containsbestleaf) {
				isbestbranch=true;
				(*rowit)[boxColumns.style] = alttype.style;
				(*rowit)[boxColumns.character] = alttype.chr;
				(*rowit)[boxColumns.variant] = alttype.var;
			}
		}
		//std::cout << std::endl;
		if (laststyle < 0) {
			rowit = endit;
		}
		return isbestbranch;
	}
}


/* Because some types, which are visually identical, can belong to different styles,
   there is often ambiguities when importing Tesseract boxes. For example, capital letters
   may be marked as either no style, or as small-caps, depending on the surrounding glyphs.
   We want to resolve this, by minimizing the number of style changes, especially inside words.
void Project::resolveStyleAmbiguities(Page* page) {
	Glib::RefPtr<Gtk::ListStore> boxlist = page->getBoxListStore();
	Gtk::TreeModel::Children children = boxlist->children();
	Gtk::TreeModel::Children::iterator rowit = children.begin();
	// Actually, the list of boxes may be empty, if we have tried to open an empty boxfile
	if (rowit == children.end()) {
		return;
	}
	// First, set style on individual tokens:
	while (rowit != children.end()) {
		styleToken(rowit, children.end());
	}
	// Then, fill in style on whitespace
	int rightstyle=0;
	rowit--;
	do {
		while (rowit != children.begin() &&
		       ((*rowit)[boxColumns.character] != " " && (*rowit)[boxColumns.character] != "\\n")) {
			rightstyle=(*rowit)[boxColumns.style];
			rowit--;
		}
		while (rowit != children.begin() &&
		       ((*rowit)[boxColumns.character] == " " || (*rowit)[boxColumns.character] == "\\n")) {
			(*rowit)[boxColumns.style] = (*rowit)[boxColumns.style] & rightstyle;
			rowit--;
		}
	} while (rowit != children.begin());

}

/* Recursive function, selecting the best choice of alternative styles for each char.
bool Project::styleToken(Gtk::TreeModel::Children::iterator &rowit,
                         const Gtk::TreeModel::Children::iterator rowend,
                         const int branchdiffs, const Unigram lasttype)
{
	static Gtk::TreeModel::Children::iterator endit;
	static int bestquality;
	if (!lasttype.exists) { // Is first time (root)	endit=rowit;
		bestquality = 1000000;
	}
	if (branchdiffs >= bestquality) {
		return false;
	}
	if (rowit==rowend || (*rowit)[boxColumns.character] == " " || (*rowit)[boxColumns.character] == "\\n") {
		if (branchdiffs < bestquality) {
			bestquality = branchdiffs;
			// Let's temporarily set the following whitespace to the same style as the last char.
			Gtk::TreeModel::Children::iterator spaceit=rowit;
			while (spaceit!=rowend && ((*spaceit)[boxColumns.character] == " " || (*spaceit)[boxColumns.character] == "\\n")) {
				(*spaceit)[boxColumns.style] = lasttype.style;
				spaceit++;
			}
			endit = spaceit;
			if (!lasttype.exists) {
				rowit=endit;
			}
			return true;
		} else {
			return false;
		}
	} else {
		bool isbestbranch = false;
		const Unigram currenttype = Unigram(rowit);
		if (currenttype.equals(lasttype)) {
			int diffs = branchdiffs;
			rowit++;
			bool containsbestleaf = styleToken(rowit, rowend, diffs, currenttype);
			rowit--;
			return containsbestleaf;
		}
		std::set<Unigram> alttypes = m_font->getAltTypes(currenttype);
		// First only try with alttypes having exactly the same style:
		bool hasidenticalstyle = false;
		for (std::set<Unigram>::iterator altit = alttypes.begin(); altit != alttypes.end(); ++altit) {
			const Unigram alttype = *altit;
			if (lasttype.style == alttype.style) {
				hasidenticalstyle = true;
				int diffs = branchdiffs;
				rowit++;
				bool containsbestleaf = styleToken(rowit, rowend, diffs, alttype);
				rowit--;
				if (containsbestleaf) {
					isbestbranch=true;
					(*rowit)[boxColumns.style] = alttype.style;
					(*rowit)[boxColumns.character] = alttype.chr;
					(*rowit)[boxColumns.variant] = alttype.var;
				}
			}		
		}
		if (!hasidenticalstyle) {
			for (std::set<Unigram>::iterator altit = alttypes.begin(); altit != alttypes.end(); ++altit) {
				const Unigram alttype = *altit;
				int diffs = branchdiffs;
				if (lasttype.exists) {
					diffs += __builtin_popcount(lasttype.style ^ alttype.style);
				}
				rowit++;
				bool containsbestleaf = styleToken(rowit, rowend, diffs, alttype);
				rowit--;
				if (containsbestleaf) {
					isbestbranch=true;
					(*rowit)[boxColumns.style] = alttype.style;
					(*rowit)[boxColumns.character] = alttype.chr;
					(*rowit)[boxColumns.variant] = alttype.var;
				}
			}
		}
		if (!lasttype.exists) {
			rowit = endit;
		}
		return isbestbranch;
	}
}
*/

void Project::on_start_element(Glib::Markup::ParseContext&,
                                     const Glib::ustring& element_name,
                                     const AttributeMap&  attributes)
{
	AttributeMap::const_iterator p;
	if (!m_isParsingRTML) {
		if (element_name == "tereseproject") {
			for(p = attributes.begin(); p != attributes.end(); ++p) {
				if (p->first == "version") {
					if (ustringToInt(p->second) > 1) {
						std::cerr << "Sorry, you are trying to open a project saved by a later version of Terese. You should upgrade." << std::endl;
						exit(1);
					}
				}
			}
		} else if (element_name == "page") {
			bool active=false;
			Glib::ustring fileName;
			for(p = attributes.begin(); p != attributes.end(); ++p) {
				if (p->first == "path") {
					fileName = p->second;           
				} else if (p->first == "active") {
					active = (p->second=="true");
				}
			}
			m_signal_progress.emit(-1,"Opening "+fileName);
			m_refCurrentPage = appendPage(fileName.raw());
			if (active) {
				setActivePage(m_refCurrentPage);
			}
		} else if (element_name == "style") {
			int id=0;
			Glib::ustring name;
			Glib::ustring prefix;
			Glib::ustring tag;
			Glib::ustring font;
			Glib::ustring background;
			Glib::ustring foreground;
			Glib::ustring shortcut;
			for (p = attributes.begin(); p != attributes.end(); ++p) {
				if (p->first == "id") {
					id = ustringToInt(p->second);
				} else if (p->first == "name") {
					name = p->second;
				} else if (p->first == "prefix") {
					prefix = p->second;
				} else if (p->first == "tag") {
					tag = p->second;
				} else if (p->first == "font") {
					font = p->second;
				} else if (p->first == "background") {
					background = p->second;
				} else if (p->first == "foreground") {
					foreground = p->second;
				} else if (p->first == "shortcut") {
					shortcut = p->second;
				}
			}
			appendStyle(id, name, prefix, tag, font, background, foreground, shortcut);
		} else if (element_name == "font") {
			int minspace = 10, midspace = 50, maxspace = 100, linespacing = 150;
			//Glib::ustring fontFileName;
			for (p = attributes.begin(); p != attributes.end(); ++p) {
				if (p->first == "minspace") {
					minspace = ustringToInt(p->second);           
				} else if (p->first == "midspace") {
					midspace = ustringToInt(p->second);           
				} else if (p->first == "maxspace") {
					maxspace = ustringToInt(p->second);           
				} else if (p->first == "linespacing") {
					linespacing = ustringToInt(p->second);           
				}
			}
			delete m_font;
			m_font = new Font(m_fileName+".png", minspace, midspace, maxspace, linespacing);
			m_font->signal_progress().connect(sigc::mem_fun(m_signal_progress, &type_signal_progress::emit));
			
		} else if (element_name == "box" || element_name == "type") {
			Glib::ustring character, targetchr;
			int style=0, var=0, targetstyle=-1, targetvar=0;
			bool deg = false;
			int correlation = 0;
			int left=0, right=0, top=0, bottom=0;
			float lbear=0, rbear=0, ldev=0, rdev=0;
			for(p = attributes.begin(); p != attributes.end(); ++p) {
				if (p->first == "char" || p->first == "c") {
					character = p->second;
				} else if (p->first == "style" || p->first == "s") {
					style = ustringToInt(p->second);
				} else if (p->first == "variant" || p->first == "var" || p->first == "v") {
					var = ustringToInt(p->second);
				} else if (p->first == "degenerate" || p->first == "deg" || p->first == "d") {
					deg = (p->second == "true");
				} else if (p->first == "correlation" || p->first == "corr" || p->first == "cr") {
					correlation = ustringToInt(p->second);
				} else if (p->first == "left" || p->first == "l") {
					left = ustringToInt(p->second);
				} else if (p->first == "right" || p->first == "r") {
					right = ustringToInt(p->second);
				} else if (p->first == "top" || p->first == "t") {
					top = ustringToInt(p->second);
				} else if (p->first == "bot" || p->first == "b") {
					bottom = ustringToInt(p->second);
				} else if (p->first == "lbear" || p->first == "lb") {
					lbear = ustringToFloat(p->second);
				} else if (p->first == "rbear" || p->first == "rb") {
					rbear = ustringToFloat(p->second);
				} else if (p->first == "ldev" || p->first == "ld") {
					ldev = ustringToFloat(p->second);
				} else if (p->first == "rdev" || p->first == "rd") {
					rdev = ustringToFloat(p->second);
				} else if (p->first == "targetchar") {
					targetchr = p->second;
				} else if (p->first == "targetstyle") {
					targetstyle = ustringToInt(p->second);
				} else if (p->first == "targetvar" || p->first == "targetvariant") {
					targetvar = ustringToInt(p->second);
				}
			}
			if (element_name == "box") {
				appendBox(m_refCurrentPage, character, style, var, deg, left, right, top, bottom, correlation);
			} else {
				if (targetstyle < 0) {
					m_font->addType(character, style, var, left, right, top, bottom, lbear, rbear, ldev, rdev);
				} else {
					m_font->addAlias(character, style, var, targetchr, targetstyle, targetvar);
				}
			}
		} else if (element_name == "rtml") {
			m_isParsingRTML = true;
			textit = m_refCurrentPage->getTextBuffer()->begin();
		}
	} else { // m_isParsingRTML
		Gtk::TreeModel::Children children = m_refStylesListStore->children();
		for (Gtk::TreeModel::Children::iterator styleit = children.begin(); styleit != children.end(); ++styleit) {
			if ( element_name == (*styleit)[styleColumns.htmltag] ) {
				(*styleit)[styleColumns.textstartmark] = m_refCurrentPage->getTextBuffer()->create_mark(textit);
			}
		}
	}
}

void Project::on_text(Glib::Markup::ParseContext& context, const Glib::ustring& text) {
	if (m_isParsingRTML) {
		textit = m_refCurrentPage->getTextBuffer()->insert(textit, text);
	}
}

void Project::on_end_element(Glib::Markup::ParseContext& context,
                                const Glib::ustring& element_name)
{
	if (element_name == "tereseproject") {
		m_signal_progress.emit(0,"");
	}
	if (element_name == "rtml") {
		m_refCurrentPage->getTextBuffer()->set_modified(false);
		m_isParsingRTML = false;
	}
	if (element_name == "page") {
		if (m_refCurrentPage != m_refActivePage) {
			m_refCurrentPage->decachePixbuf();
		}
		m_refCurrentPage = NULL;
	}
	if (m_isParsingRTML) {
		Gtk::TreeModel::Children children = m_refStylesListStore->children();
		for (Gtk::TreeModel::Children::iterator styleit = children.begin(); styleit != children.end(); ++styleit) {
			if ( element_name == (*styleit)[styleColumns.htmltag] ) {
				Glib::RefPtr<Gtk::TextBuffer::Mark> tempStartMark = (*styleit)[styleColumns.textstartmark];
				m_refCurrentPage->getTextBuffer()->apply_tag((*styleit)[styleColumns.texttag],
				   tempStartMark->get_iter(), textit);
			}
		}
	}
}


void Project::save(const std::string& filename) {
   m_fileName = filename;
	save();
}

void Project::save() {
   try {
      Glib::RefPtr<Gio::File> file = Gio::File::create_for_path(m_fileName);
      if(!file) {
         std::cerr << "Could not save file. Gio::File::create_for_path() returned an empty RefPtr." << std::endl;
			return;
		}

      Glib::RefPtr<Gio::FileOutputStream> filestream;
      if (file->query_exists())
         filestream = file->replace(std::string(),true); // true = Make backup
      else
         filestream = file->create_file();

		if (!filestream) {
			std::cerr << "Could not save file. Gio::File::create_file() returned an empty RefPtr." << std::endl;
			return;
		}

		Glib::RefPtr<Gio::DataOutputStream> outfile = Gio::DataOutputStream::create(filestream);
		std::ostringstream strstream;
		strstream << "<tereseproject version=\"1\">" << std::endl;

		// Styles
		//strstream << "  <styles>" << std::endl;
		for (Gtk::TreeModel::Children::iterator rowit=m_refStylesListStore->children().begin();
		     rowit != m_refStylesListStore->children().end(); rowit++) {
			strstream << "  <style id=\"" << (*rowit)[styleColumns.id] << "\" ";
			strstream << "name=\"" << Glib::Markup::escape_text((*rowit)[styleColumns.name]) << "\" ";
			strstream << "prefix=\"" << Glib::Markup::escape_text((*rowit)[styleColumns.prefix]) << "\" ";
			strstream << "tag=\"" << (*rowit)[styleColumns.htmltag] << "\" ";
			strstream << "font=\"" << Glib::Markup::escape_text((*rowit)[styleColumns.font]) << "\" ";
			strstream << "background=\"" << Glib::Markup::escape_text((*rowit)[styleColumns.background]) << "\" ";
			strstream << "foreground=\"" << Glib::Markup::escape_text((*rowit)[styleColumns.foreground]) << "\" ";
			strstream << "shortcut=\"" << Glib::Markup::escape_text((*rowit)[styleColumns.shortcut]) << "\"/>" << std::endl;
		}
		//strstream << "  </styles>" << std::endl;
		//strstream << "  <pages>" << std::endl;

		for (Gtk::TreeModel::Children::iterator rowit = m_refPagesListStore->children().begin();
		     rowit != m_refPagesListStore->children().end(); rowit++) {
			Page* page = (*rowit)[pagesColumns.page];
			
			strstream << "  <page path=\"" << Glib::Markup::escape_text((*rowit)[pagesColumns.fullname]) << "\"";
			if ((*rowit)[pagesColumns.page] == m_refActivePage) {
				strstream << " active=\"true\"";
			}
			strstream << ">" << std::endl;

			// (R/H)TML. In order to avoid nested tags, this gets a bit messy.
			// I'm probably reinventing the wheel...
			strstream << "<rtml>";
			std::stack<Glib::ustring> htmltagstack;
			Glib::RefPtr<Gtk::TextBuffer> textBuffer = page->getTextBuffer();
			textBuffer->set_modified(false);
         for (Gtk::TextBuffer::iterator textit=textBuffer->begin(); textit != textBuffer->end(); textit++) {
				// First, check which tags should be closed, and which should be opened,
				// iterating over the available styles.
				std::set<Glib::ustring> tagstobeclosed;
				std::stack<Glib::ustring> tagstobeopened;
				Gtk::TreeModel::Children styles = m_refStylesListStore->children();
				for (Gtk::TreeModel::Children::iterator styleit = styles.begin(); styleit != styles.end(); ++styleit) {
					Glib::RefPtr<Gtk::TextBuffer::Tag> texttag = (*styleit)[styleColumns.texttag];
					Glib::ustring htmltag = (*styleit)[styleColumns.htmltag];
					if (htmltag!="") {
						if (textit.ends_tag(texttag)) {
							tagstobeclosed.insert(htmltag);
						} else if (textit.begins_tag(texttag)) {
							tagstobeopened.push(htmltag);
						}
					}
				}
				// We now have a set containing tags that should be closed, so we close them.
				// But if they should not be permanently closed, add them to the to-be-opened stack.
				std::set<Glib::ustring>::iterator setit;
				while (!tagstobeclosed.empty()) {
					Glib::ustring lastopentag;
					lastopentag = htmltagstack.top();
					setit=tagstobeclosed.find(lastopentag);
					if (setit==tagstobeclosed.end()) { // Not in set
						tagstobeopened.push(lastopentag);
					} else {
						tagstobeclosed.erase(setit);
					}
					strstream << "</" << lastopentag << ">";
					htmltagstack.pop();
				}
				// Finally we open tags.
				while (!tagstobeopened.empty()) {
					Glib::ustring tag;
					tag = tagstobeopened.top();
					strstream << "<" << tag << ">";
					htmltagstack.push(tag);
					tagstobeopened.pop();
				}
				// And don't forget the actual character!
				strstream << Glib::Markup::escape_text(Glib::ustring(1,*textit));
			}
			// Done! But there might be tags at the end to close.
			while (!htmltagstack.empty()) {
				strstream << "</" << htmltagstack.top() << ">";		
				htmltagstack.pop();
			}
			strstream << "</rtml>" << std::endl;
			// Boxes
			Glib::RefPtr<Gtk::ListStore> boxList = page->getBoxListStore(); //(*rowit)[pagesColumns.boxlist];
			for (Gtk::TreeModel::Children::iterator boxit=boxList->children().begin();
              boxit != boxList->children().end(); boxit++) {
				strstream << "<box c=\"" << Glib::Markup::escape_text((*boxit)[boxColumns.character]) << "\" ";
				strstream << "s=\"" << (*boxit)[boxColumns.style] << "\" ";
				if ((*boxit)[boxColumns.variant] > 0) {
					strstream << "v=\"" << (*boxit)[boxColumns.variant] << "\" ";
				}
				if ((*boxit)[boxColumns.degenerate]) {
					strstream << "d=\"true\" ";
				}
				if ((*boxit)[boxColumns.correlation] != 0) {
					strstream << "cr=\"" << (*boxit)[boxColumns.correlation] << "\" ";
				}
				strstream << "l=\"" << (*boxit)[boxColumns.left] << "\" ";
				strstream << "r=\"" << (*boxit)[boxColumns.right] << "\" ";
				strstream << "t=\"" << (*boxit)[boxColumns.top] << "\" ";
				strstream << "b=\"" << (*boxit)[boxColumns.bottom] << "\"/>" << std::endl;
			}
			strstream << "  </page>" << std::endl;
		}
		//strstream << "  </pages>" << std::endl;
		strstream << m_font->save(m_fileName);
		strstream << "</tereseproject>" << std::endl;
		outfile->put_string(strstream.str());
		outfile->close();
		outfile.reset();
		setModified(false);
	} catch(const Glib::Exception& ex) {
      std::cerr << "Could not save file. Exception caught: " << ex.what() << std::endl; 
   }
}
