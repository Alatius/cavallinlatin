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

#include "terese.h"

Terese::Terese(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade) :
Gtk::Window(cobject),
builder(refGlade)
{

	builder->get_widget("menuNew", menuNew);
	builder->get_widget("menuOpen", menuOpen);
	builder->get_widget("menuSave", menuSave);
	builder->get_widget("menuSaveAs", menuSaveAs);
	builder->get_widget("menuAddPages", menuAddPages);
	builder->get_widget("menuExportBox", menuExportBox);
	builder->get_widget("menuExportOCRopusLines", menuExportOCRopusLines);
	builder->get_widget("menuExportOverlays", menuExportOverlays);
	builder->get_widget("menuQuit", menuQuit);
	builder->get_widget("menuFormat", menuFormat);
	builder->get_widget("menuZoom100", menuZoom100);
	builder->get_widget("menuZoom50", menuZoom50);
	builder->get_widget("menuZoom33", menuZoom33);
	builder->get_widget("menuZoom25", menuZoom25);
	builder->get_widget("menuShowOriginal", menuShowOriginal);
	builder->get_widget("menuShowMaskOverlay", menuShowMaskOverlay);
	builder->get_widget("menuShowMaskOnly", menuShowMaskOnly);

	builder->get_widget("menuitemCutBox", menuitemCutBox);
	builder->get_widget("menuitemCopyBox", menuitemCopyBox);
	builder->get_widget("menuitemPasteBox", menuitemPasteBox);
	builder->get_widget("menuitemDeleteBox", menuitemDeleteBox);
	builder->get_widget("menuitemMergeFollowingBox", menuitemMergeFollowingBox);
	builder->get_widget("menuitemMergePrecedingBox", menuitemMergePrecedingBox);
	builder->get_widget("menuitemSplitBox", menuitemSplitBox);
	builder->get_widget("menuitemBoxEnlargeLeft", menuitemBoxEnlargeLeft);
	builder->get_widget("menuitemBoxEnlargeRight", menuitemBoxEnlargeRight);
	builder->get_widget("menuitemBoxEnlargeTop", menuitemBoxEnlargeTop);
	builder->get_widget("menuitemBoxEnlargeBottom", menuitemBoxEnlargeBottom);
	builder->get_widget("menuitemBoxDecreaseLeft", menuitemBoxDecreaseLeft);
	builder->get_widget("menuitemBoxDecreaseRight", menuitemBoxDecreaseRight);
	builder->get_widget("menuitemBoxDecreaseTop", menuitemBoxDecreaseTop);
	builder->get_widget("menuitemBoxDecreaseBottom", menuitemBoxDecreaseBottom);

	builder->get_widget("menuitemTextFromBoxes", menuitemTextFromBoxes);
	
	builder->get_widget("menuitemEditAliases", menuitemEditAliases);
	builder->get_widget("menuitemCreateFont", menuitemCreateFont);
	builder->get_widget("menuitemReadjustBoxes", menuitemReadjustBoxes);
	builder->get_widget("menuitemReconsiderBoxes", menuitemReconsiderBoxes);
	builder->get_widget("menuitemOCR", menuitemOCR);
	builder->get_widget("menuitemMapText", menuitemMapText);
	builder->get_widget("menuitemSegmentate", menuitemSegmentate);
	builder->get_widget("menuitemClusterBoxes", menuitemClusterBoxes);
	builder->get_widget("menuitemBatch", menuitemBatch);
	builder->get_widget("menuitemBatch2", menuitemBatch2);

	builder->get_widget_derived("dialogAliases", dialogAliases);

	builder->get_widget_derived("treeviewBoxes", treeviewBoxes);
	builder->get_widget_derived("treeviewPages", treeviewPages);
	builder->get_widget_derived("drawingArea", drawingArea);
	builder->get_widget("comboboxClasses", comboboxClasses);
	builder->get_widget("comboboxSorting", comboboxSorting);
	builder->get_widget("textView", textView);
	builder->get_widget("iconviewBoxes", iconviewBoxes);
	builder->get_widget("progressbar", progressbar);
	builder->get_widget("entryNewStyle", entryNewStyle);
	builder->get_widget("entryNewChar", entryNewChar);
	builder->get_widget("entryNewVariant", entryNewVariant);
	builder->get_widget("buttonReclassify", buttonReclassify);

	drawingArea->set_boxes(treeviewBoxes);
	
	comboboxClasses->pack_start(boxColumns.style);
	comboboxClasses->pack_start(boxColumns.character);
	comboboxClasses->pack_start(boxColumns.variant);
	comboboxSorting->set_active(0);
	
	menuNew->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuNew_activate));
	menuOpen->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuOpen_activate));
	menuSave->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuSave_activate));
	menuSaveAs->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuSaveAs_activate));
	menuAddPages->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuAddPages_activate));
	menuExportBox->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuExportBox_activate));
	menuExportOCRopusLines->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuExportOCRopusLines_activate));
	menuExportOverlays->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuExportOverlays_activate));
	menuQuit->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuQuit_activate));

	menuZoom100->signal_activate().connect( sigc::bind<int> ( sigc::mem_fun(drawingArea, &CustomDrawingArea::set_zoom), 1) );
	menuZoom50->signal_activate().connect( sigc::bind<int> ( sigc::mem_fun(drawingArea, &CustomDrawingArea::set_zoom), 2) );
	menuZoom33->signal_activate().connect( sigc::bind<int> ( sigc::mem_fun(drawingArea, &CustomDrawingArea::set_zoom), 3) );
	menuZoom25->signal_activate().connect( sigc::bind<int> ( sigc::mem_fun(drawingArea, &CustomDrawingArea::set_zoom), 4) );
	menuShowOriginal->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuShowOriginal_activate));
	menuShowMaskOverlay->signal_activate().connect(sigc::bind<bool> (sigc::mem_fun(*this, &Terese::on_menuShowMask_activate), true));
	menuShowMaskOnly->signal_activate().connect(sigc::bind<bool> (sigc::mem_fun(*this, &Terese::on_menuShowMask_activate), false));

	menuitemCutBox->signal_activate().connect(sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxCut));
	menuitemCopyBox->signal_activate().connect(sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxCopy));
	menuitemPasteBox->signal_activate().connect(sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxPaste));
	menuitemDeleteBox->signal_activate().connect(sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxDelete));
	menuitemMergeFollowingBox->signal_activate().connect(sigc::bind<bool> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxMerge), true));
	menuitemMergePrecedingBox->signal_activate().connect(sigc::bind<bool> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxMerge), false));
	menuitemSplitBox->signal_activate().connect(sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxSplit));
	menuitemBoxEnlargeLeft->signal_activate().connect(   sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize), -1,  0,  0,  0));
	menuitemBoxEnlargeRight->signal_activate().connect(  sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  0,  1,  0,  0));
	menuitemBoxEnlargeTop->signal_activate().connect(    sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  0,  0, -1,  0));
	menuitemBoxEnlargeBottom->signal_activate().connect( sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  0,  0,  0,  1));
	menuitemBoxDecreaseLeft->signal_activate().connect(  sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  1,  0,  0,  0));
	menuitemBoxDecreaseRight->signal_activate().connect( sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  0, -1,  0,  0));
	menuitemBoxDecreaseTop->signal_activate().connect(   sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  0,  0,  1,  0));
	menuitemBoxDecreaseBottom->signal_activate().connect(sigc::bind<int, int, int, int> ( sigc::mem_fun(treeviewBoxes, &BoxTreeView::on_menuBoxResize),  0,  0,  0, -1));

	menuitemTextFromBoxes->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuTextFromBoxes_activate));
	
	menuitemEditAliases->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuEditAliases_activate));
	menuitemCreateFont->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuCreateFont_activate));
	menuitemReadjustBoxes->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuReadjustBoxes_activate));
	menuitemReconsiderBoxes->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuReconsiderBoxes_activate));
	menuitemOCR->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuOCR_activate));
	menuitemMapText->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuMapText_activate));
	menuitemSegmentate->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuSegment_activate));
	menuitemClusterBoxes->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuClusterBoxes_activate));
	menuitemBatch->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuBatch_activate));
	menuitemBatch2->signal_activate().connect(sigc::mem_fun(*this, &Terese::on_menuBatch2_activate));

	treeviewPages->signal_setActivePage().connect(sigc::mem_fun(*this, &Terese::showPage) );
	treeviewBoxes->signal_centerBox().connect(sigc::mem_fun(drawingArea, &CustomDrawingArea::on_centerBox) );
	treeviewBoxes->signal_boxChanged().connect(sigc::mem_fun(drawingArea, &CustomDrawingArea::queue_draw) );
	treeviewBoxes->signal_boxChanged().connect(sigc::mem_fun(iconviewBoxes, &Gtk::IconView::queue_draw) );
	drawingArea->signal_boxselect().connect(sigc::mem_fun(*this, &Terese::selectBox) );
	drawingArea->signal_boxrelocate().connect(sigc::mem_fun(*this, &Terese::relocateBox) );

	comboboxClasses->signal_changed().connect( sigc::mem_fun(*this, &Terese::showClassBoxes) );
	comboboxSorting->signal_changed().connect( sigc::mem_fun(*this, &Terese::showClassBoxes) );

#if GTKMM_MAJOR_VERSION>3 || GTKMM_MAJOR_VERSION==3 && GTKMM_MINOR_VERSION>=8
	iconviewBoxes->set_activate_on_single_click(true);
#endif
	iconviewBoxes->signal_item_activated().connect(sigc::mem_fun(*this, &Terese::on_boxicon_activated) );
	iconviewBoxes->signal_selection_changed().connect(sigc::mem_fun(*this, &Terese::on_iconselection_changed) );
	
	buttonReclassify->signal_clicked().connect(sigc::mem_fun(*this, &Terese::on_buttonReclassify_clicked) );

	createNewProject("");

}

void Terese::createNewProject(const std::string& filename) {

	project = new Project();

	// Connect progress signal, so we see that loading is going on.
	project->signal_progress().connect(sigc::mem_fun(*this, &Terese::updateProgress));

	// Now we can open the desired file
	project->open(filename);

	// Connect the loaded project to the GUI
	buildFormatMenu(project->stylesListStore());
	treeviewPages->set_model(project->pagesListStore());

	// Select the page in the treeviewPages which the project considers active.
	// Since this changes the selection, it will trigger
	//    PageTreeView::on_selection_changed, which in turn emits signal_setActivePage, which is connected to
	//    Terese::showPage, which calls Project::setActivePage again...
	Page* page = project->getActivePage();
	Glib::RefPtr<Gtk::TreeSelection> refTreeSelection = treeviewPages->get_selection();
	Gtk::TreeModel::Children::iterator rowit;
	for (rowit=project->pagesListStore()->children().begin();
	     rowit != project->pagesListStore()->children().end(); ++rowit)
	{
		if ((*rowit)[pagesColumns.page] == page) {
			refTreeSelection->select(*rowit);
			break;
		}
	}
	if (rowit == project->pagesListStore()->children().end()) {
		showPage(NULL);
	}
	
	// While loading, the project marks itself as modified. But we don't want to show that,
	// so we postpone connecting the "modified" signal.
	project->signal_modified().connect(sigc::mem_fun(*this, &Terese::updateWindowTitle));
	project->setModified(false);
	updateProgress(0,"");
}

/*void Terese::setModified(bool status) {
	project->setModified(status);
}*/

void Terese::showPage(Page* page) {
	project->setActivePage(page);
	treeviewBoxes->set_model(project->currentBoxList(), project->currentPixbuf());
	listClasses(project->currentBoxList());
	textView->set_buffer(project->currentTextBuffer());
	drawingArea->on_showPageImage(project->currentPixbuf());
}

void Terese::buildFormatMenu(Glib::RefPtr<Gtk::ListStore> styles) {
	Gtk::Menu* newStylesMenu = Gtk::manage(new Gtk::Menu());
	newStylesMenu->set_accel_group(this->get_accel_group());
   Gtk::TreeModel::Children::iterator rowit;
	for (rowit = styles->children().begin();
	     rowit != styles->children().end(); ++rowit)
	{
		const int id = (*rowit)[styleColumns.id];
		const Glib::ustring name = (*rowit)[styleColumns.name];
		const Glib::ustring prefix = (*rowit)[styleColumns.prefix];
		const Glib::ustring htmltag = (*rowit)[styleColumns.htmltag];
		const Glib::ustring font = (*rowit)[styleColumns.font];
		const Glib::ustring background = (*rowit)[styleColumns.background];
		const Glib::ustring foreground = (*rowit)[styleColumns.foreground];
		const Glib::ustring shortcut = (*rowit)[styleColumns.shortcut];
		const Glib::RefPtr<Gtk::TextBuffer::Tag> texttag = (*rowit)[styleColumns.texttag];
		if (id == 0) {
			if (font != "")
				textView->override_font(Pango::FontDescription(font));
			if (foreground != "")
				textView->override_color(Gdk::RGBA(foreground));
			if (background != "")
				textView->override_background_color(Gdk::RGBA(background));
		} else {
			Gtk::MenuItem* newMenuItem = Gtk::manage(new Gtk::MenuItem(name)); 
			newMenuItem->set_accel_path("<Terese>/Format/"+name);
			guint shortcutcharacter;
			Gdk::ModifierType shortcutmodifier;
			Gtk::AccelGroup::parse(shortcut, shortcutcharacter, shortcutmodifier);
			Gtk::AccelMap::change_entry("<Terese>/Format/"+name, shortcutcharacter, shortcutmodifier, true);
			newMenuItem->signal_activate().connect( sigc::bind<int, Glib::RefPtr<Gtk::TextBuffer::Tag> > ( sigc::mem_fun(*this, &Terese::toggle_tag), id, texttag) );
			newStylesMenu->add(*newMenuItem);
		}
	}
	newStylesMenu->show_all();
	menuFormat->set_submenu(*newStylesMenu);
}

void Terese::updateWindowTitle() {
	Glib::ustring title="";
	if (project->isModified()) {
		title="*";
	}
	if (project->isNamed()) {
		title+=project->filename();
	} else {
		title+="Unsaved project";
	}
   title+=" - Terese";
   set_title(title);
}

void Terese::updateProgress(float progress, Glib::ustring message) {
	if (progress<0) {
		progressbar->pulse();
	} else {
		progressbar->set_fraction(progress);
	}
	progressbar->set_text(message);
	get_toplevel()->queue_draw();
	get_toplevel()->get_window()->process_updates(true);
	get_toplevel()->queue_draw();
	get_toplevel()->get_window()->process_updates(true);
}

bool Terese::mayDiscard() {
	// Not the most user friendly...
	if (project->isModified()) {
		 Gtk::MessageDialog dialog(*this, "You have unsaved changes!", false, Gtk::MESSAGE_QUESTION, Gtk::BUTTONS_YES_NO);
		 dialog.set_secondary_text("Do you want to proceed? Clicking yes will destroy your unsaved changes.");
		 if (dialog.run()==Gtk::RESPONSE_NO) {
			 return false;
		}
	}
	return true;
}

void Terese::on_menuNew_activate() {

	if (!mayDiscard()) {
		return;
	}

	delete project;
	createNewProject("");

}

void Terese::on_menuOpen_activate() {

	if (!mayDiscard()) {
		return;
	}

	Gtk::FileChooserDialog dialog("Open Terese project", Gtk::FILE_CHOOSER_ACTION_OPEN);
	dialog.set_transient_for(*this);
	dialog.add_button(Gtk::Stock::CANCEL, Gtk::RESPONSE_CANCEL);
	dialog.add_button(Gtk::Stock::OPEN, Gtk::RESPONSE_OK);

	Glib::RefPtr<Gtk::FileFilter> filter_terese = Gtk::FileFilter::create();
	filter_terese->set_name("Terese projects");
	filter_terese->add_pattern("*.terese");
	dialog.add_filter(filter_terese);

	Glib::RefPtr<Gtk::FileFilter> filter_any = Gtk::FileFilter::create();
	filter_any->set_name("Any files");
	filter_any->add_pattern("*");
	dialog.add_filter(filter_any);
	
	int result = dialog.run();
	dialog.hide();
	
	if (result==Gtk::RESPONSE_OK) {

		delete project;
		createNewProject(dialog.get_filename());

	}
	
}

void Terese::on_menuSave_activate() {
	if (project->isNamed()) {
		project->save();
	} else {
      on_menuSaveAs_activate();
	}
}

void Terese::on_menuSaveAs_activate() {
	std::string filename;
	Gtk::FileChooserDialog dialog("Save Terese project", Gtk::FILE_CHOOSER_ACTION_SAVE);
	dialog.set_transient_for(*this);
	dialog.add_button(Gtk::Stock::CANCEL, Gtk::RESPONSE_CANCEL);
	dialog.add_button(Gtk::Stock::SAVE, Gtk::RESPONSE_OK);
	Glib::RefPtr<Gtk::FileFilter> filter_terese = Gtk::FileFilter::create();
	filter_terese->set_name("Terese projects");
	filter_terese->add_pattern("*.terese");
	dialog.add_filter(filter_terese);

	if (dialog.run()==Gtk::RESPONSE_OK) {
		filename = dialog.get_filename();
		// Maybe a bit clumsy?
		if (filename.substr(filename.length()-7,filename.length()-1) != ".terese") {
			filename+=".terese";
		}
		project->save(filename);
	}
	
}

void Terese::on_menuAddPages_activate() {

	Gtk::FileChooserDialog dialog("Add pages (images)", Gtk::FILE_CHOOSER_ACTION_OPEN);
	dialog.set_transient_for(*this);
	dialog.add_button(Gtk::Stock::CANCEL, Gtk::RESPONSE_CANCEL);
	dialog.add_button(Gtk::Stock::OPEN, Gtk::RESPONSE_OK);
	dialog.set_select_multiple(true);

	Glib::RefPtr<Gtk::FileFilter> filter_terese = Gtk::FileFilter::create();
	filter_terese->set_name("Tiff images");
	filter_terese->add_pattern("*.tif");
	filter_terese->add_pattern("*.tiff");
	dialog.add_filter(filter_terese);

	Glib::RefPtr<Gtk::FileFilter> filter_any = Gtk::FileFilter::create();
	filter_any->set_name("Any files");
	filter_any->add_pattern("*");
	dialog.add_filter(filter_any);
	
	int result = dialog.run();
	dialog.hide();
	
	if (result==Gtk::RESPONSE_OK) { // Open

		std::vector<std::string> filenames = dialog.get_filenames();
		int i=0;
		for(std::vector<std::string>::iterator it = filenames.begin(); it != filenames.end(); ++it) {

			std::string filename = *it;
			updateProgress(++i/(float)filenames.size(), "Opening "+filename);
			
			Page* page = project->appendPage(filename);
			
			// Maybe we can also import boxes?
			project->importBoxFile(page, filename);
			// And an RTML-file?
			project->importRTMLFile(page, filename);
			
			page->decachePixbuf();
		}
		updateProgress(0,"");
	}
}

void Terese::on_menuExportBox_activate() {
	project->exportBoxFiles();
}

void Terese::on_menuExportOCRopusLines_activate() {
	project->exportOCRopusLines();
}

void Terese::on_menuExportOverlays_activate() {
	Glib::RefPtr<Gtk::TreeModel> pagelist = treeviewPages->get_model();
	int c = 0;
	for (Gtk::TreeModel::Children::iterator rowit = pagelist->children().begin();
	     rowit != pagelist->children().end(); ++rowit)
	{
		updateProgress(c/float(pagelist->children().size()),"Exporting overlays");
		Page *thepage = (*rowit)[pagesColumns.page];
		showPage(thepage);
		Image* img = project->currentImage();
		if (!img) {
			continue;
		}
		Image maskImg = Terese::getMask(img);
		Glib::ustring fullname = (*rowit)[pagesColumns.fullname];
		std::string overlayfilename = fullname.substr(0,fullname.find_last_of("."))+"_overlay.png";
		maskImg.savepng(overlayfilename);	
		c++;
	}
	updateProgress(0,"");
}

bool Terese::on_delete_event(GdkEventAny* event) {
  on_menuQuit_activate();
  return true;
}

void Terese::on_menuQuit_activate() {
	if (mayDiscard()) {
		hide();
	}
}

void Terese::on_menuEditAliases_activate() {
	dialogAliases->populateList(project->allBoxUnigrams(), project->theFont()->getAliasMap());
	int result = dialogAliases->run();
	dialogAliases->hide();
	if (result==Gtk::RESPONSE_OK) {
		project->theFont()->setAliasMap( dialogAliases->getAliasMap() );
		project->setModified(true);
	}
}


void Terese::toggle_tag(int style, Glib::RefPtr<Gtk::TextBuffer::Tag> refTag) {
	bool shallremove=true;

	if (textView->has_focus()) {
		
		Gtk::TextBuffer::iterator startit;
		Gtk::TextBuffer::iterator endit;
		if (textView->get_buffer()->get_selection_bounds(startit, endit)) {
			for (Gtk::TextBuffer::iterator it=startit; it!=endit; it++) {
				if (!it.has_tag(refTag))
					shallremove=false;
			}
			if (shallremove)
				textView->get_buffer()->remove_tag(refTag, startit, endit);
			else
				textView->get_buffer()->apply_tag(refTag, startit, endit);
		}
		textView->get_buffer()->set_modified(true);
		
	} else if (treeviewBoxes->has_focus() || iconviewBoxes->has_focus()) {
		
		std::vector<Gtk::TreeModel::Path> paths = treeviewBoxes->get_selection()->get_selected_rows();
		for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
			Gtk::TreeModel::iterator iter = treeviewBoxes->get_model()->get_iter(*pathit);
			const int oldstyle=(*iter)[boxColumns.style];
			if (!((*iter)[boxColumns.style] & style))
				shallremove=false;
		}
		for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {
			Gtk::TreeModel::iterator iter = treeviewBoxes->get_model()->get_iter(*pathit);
			//const Glib::ustring character = (*iter)[boxColumns.character];
			//if (character != " " && character != "\\n") {
			const int oldstyle=(*iter)[boxColumns.style];
			if (shallremove)
				(*iter)[boxColumns.style] = oldstyle & ~style;
			else
				(*iter)[boxColumns.style] = oldstyle | style;
			//}
		}
		listClasses(project->currentBoxList());

	}
		
}

/* Select the first box that occupies the coordinates.
	Also select the corresponding location in the text, if possible. */ 
void Terese::selectBox(int xpos, int ypos) {
	bool textviewhadfocus = textView->has_focus();
	Glib::RefPtr<Gtk::TreeModel> refBoxesListStore = treeviewBoxes->get_model();
	Glib::RefPtr<Gtk::TextBuffer> refTextBuffer = textView->get_buffer();
	if (!refBoxesListStore) {
		return;
	}
	Gtk::TextBuffer::iterator textpos, textit = refTextBuffer->begin();
	Gtk::TreeModel::Children::iterator rowit;
	bool textagree = true;
	for (rowit = refBoxesListStore->children().begin();
	     rowit != refBoxesListStore->children().end(); ++rowit)
	{
		if (textagree) {
			textpos = textit;
			Glib::ustring rowchr = (*rowit)[boxColumns.character];
			if (rowchr == "\\n") {
				rowchr = "\n";
			}
			for (Glib::ustring::iterator stringit = rowchr.begin();
			     stringit != rowchr.end(); ++stringit, ++textit)
			{
				if ((*stringit) != (*textit)) {
					textagree = false;
					break;
				}
			}
		}
		if ((*rowit)[boxColumns.left] < xpos && (*rowit)[boxColumns.top] < ypos &&
		    (*rowit)[boxColumns.right] > xpos && (*rowit)[boxColumns.bottom] > ypos) {
			// Changing the selection will call BoxTreeView::on_selection_changed()
			// which in turn will call CustomDrawingArea::on_centerBox
			treeviewBoxes->set_cursor(refBoxesListStore->get_path(rowit), *treeviewBoxes->get_column(1), true);
			if (textagree) {
				refTextBuffer->select_range(textpos, textit);
				textView->scroll_to(textpos);
				if (textviewhadfocus) {
					textView->grab_focus();
				}
			}
			break;
		}
	}
}

// Populates the class combobox
void Terese::listClasses(Glib::RefPtr<Gtk::ListStore> boxlist) {
	std::cout << "Class-list updated!" << std::endl;
	if (boxlist) {
		
		// Note: We want to retain the current selection of class
		int active_row_number = comboboxClasses->get_active_row_number();
		Glib::ustring character;
		int style = -1, var;
		Gtk::TreeModel::iterator iter = comboboxClasses->get_active();
		if (iter) {
			Gtk::TreeModel::Row row = *iter;
			if (row) {
				character = row[boxColumns.character];
				style = row[boxColumns.style];
				var = row[boxColumns.variant];
			}
		}

		// Then create new list
		Glib::RefPtr<Gtk::ListStore> classlist = Gtk::ListStore::create(boxColumns);

		Gtk::TreeModel::Children::iterator boxrowit;
		for (boxrowit=boxlist->children().begin();
		     boxrowit != boxlist->children().end(); ++boxrowit)
		{
			Glib::ustring character = (*boxrowit)[boxColumns.character];
			if (character !=" " && character !="\\n") {
				int style = (*boxrowit)[boxColumns.style];
				int var = (*boxrowit)[boxColumns.variant];
				Gtk::TreeModel::Children::iterator classrowit;
				bool isinlist = false;
				for (classrowit=classlist->children().begin();
				     classrowit != classlist->children().end(); ++classrowit)
				{
					Glib::ustring rowchar = (*classrowit)[boxColumns.character];
					// Use strcmp to avoid locale collation (where e.g. "longs s" = "s")
					if ( strcmp(rowchar.c_str(), character.c_str()) == 0 &&
					    (*classrowit)[boxColumns.style] == style &&
					    (*classrowit)[boxColumns.variant] == var ) {
						isinlist = true;
						break;
					}
				}
				if (!isinlist) {
					Gtk::TreeModel::Row row = *(classlist->append());
					row[boxColumns.character] = character;
					row[boxColumns.style] = style;
					row[boxColumns.variant] = var;
				}
			}
		}

		classlist->set_sort_column(boxColumns.variant, Gtk::SORT_ASCENDING);
		classlist->set_sort_column(boxColumns.character, Gtk::SORT_ASCENDING);
		classlist->set_sort_column(boxColumns.style, Gtk::SORT_ASCENDING);
		comboboxClasses->set_model(classlist);

		// Reselect the current character and class:
		if (style!=-1) {
			Gtk::TreeModel::Children::iterator classrowit;
			for (classrowit=classlist->children().begin();
			     classrowit != classlist->children().end(); ++classrowit)
			{
				if ((*classrowit)[boxColumns.character] == character &&
				    (*classrowit)[boxColumns.style] == style &&
				    (*classrowit)[boxColumns.variant] == var) {
					comboboxClasses->set_active(classrowit);
					break;
				}
			}
			if (classrowit == classlist->children().end()) {
				// The exact same character and style is not found in the new list.
				// So select the row with the same number as the previous. Close enough?
				comboboxClasses->set_active(active_row_number);
			}
		} else {
			comboboxClasses->set_active(0);
		}
	}
}

void Terese::showClassBoxes() {
	Glib::ustring character;
	int style, var;
	Gtk::TreeModel::iterator iter = comboboxClasses->get_active();
	if (iter) {
		character = (*iter)[boxColumns.character];
		style = (*iter)[boxColumns.style];
		var = (*iter)[boxColumns.variant];
	} else {
		character = "";
		style = 0;
		var = 0;
	}
	modelFilter = Gtk::TreeModelFilter::create(treeviewBoxes->get_model());
	modelFilter->set_visible_func(sigc::bind<Glib::ustring,int> ( sigc::mem_fun(*this, &Terese::filterBoxes), character, style, var) );

	modelFilterSorted = Gtk::TreeModelSort::create(modelFilter);
	if (comboboxSorting->get_active_text() == "Correlation") {
		modelFilterSorted->set_sort_column(boxColumns.correlation, Gtk::SORT_DESCENDING);
	}
	
	iconviewBoxes->set_model(modelFilterSorted);
	iconviewBoxes->set_pixbuf_column(boxColumns.icon);
}

bool Terese::filterBoxes(const Gtk::TreeModel::const_iterator& iter, Glib::ustring character, int style, int var) {
	if (iter) {
		Glib::ustring rowchar = (*iter)[boxColumns.character];
		return (strcmp(rowchar.c_str(), character.c_str())==0 &&
		        (*iter)[boxColumns.style]==style &&
		        (*iter)[boxColumns.variant]==var);
	}
	return true;
}

void Terese::on_boxicon_activated(const Gtk::TreeModel::Path& path) {

	//Gtk::TreeModel::iterator filter_iter = modelFilter->get_iter(const_cast<Gtk::TreePath&>(path));
	
	Gtk::TreeModel::iterator filtersorted_iter = modelFilterSorted->get_iter(const_cast<Gtk::TreePath&>(path));
	Gtk::TreeModel::iterator filter_iter = modelFilterSorted->convert_iter_to_child_iter(filtersorted_iter);
	Gtk::TreeModel::iterator iter = modelFilter->convert_iter_to_child_iter(filter_iter);

	Gtk::TreePath newpath; newpath = iter;

	// Changing the selection will call BoxTreeView::on_selection_changed()
	// which in turn will call CustomDrawingArea::on_centerBox
	Gtk::TreeViewColumn *column = treeviewBoxes->get_column(1);
	treeviewBoxes->set_cursor(newpath, *column, true);

}

void Terese::on_buttonReclassify_clicked() {
	Glib::ustring newstyle = entryNewStyle->get_text();
	Glib::ustring newchar = entryNewChar->get_text();
	Glib::ustring newvar = entryNewVariant->get_text();
	std::vector<Gtk::TreeModel::Path> paths = treeviewBoxes->get_selection()->get_selected_rows();
   for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {

		Gtk::TreeModel::iterator iter = treeviewBoxes->get_model()->get_iter(*pathit);
		Glib::ustring character = (*iter)[boxColumns.character];
		if (newstyle.length() > 0) {
			(*iter)[boxColumns.style] = ustringToInt(newstyle);
		}
		if (newchar.length() > 0) {
			(*iter)[boxColumns.character] = newchar;
		}
		if (newvar.length() > 0) {
			(*iter)[boxColumns.variant] = ustringToInt(newvar);
		}
	}
	entryNewStyle->set_text("");
	entryNewChar->set_text("");
	entryNewVariant->set_text("0");
	
	listClasses(project->currentBoxList());

}

void Terese::on_iconselection_changed() {
	std::vector<Gtk::TreeModel::Path> paths = iconviewBoxes->get_selected_items();
	//if (paths.size()>0) {
		treeviewBoxes->get_selection()->unselect_all();
		for (std::vector<Gtk::TreePath>::const_iterator pathit = paths.begin(); pathit!=paths.end(); ++pathit) {

			Gtk::TreeModel::iterator filtersorted_iter = modelFilterSorted->get_iter(*pathit);
			Gtk::TreeModel::iterator filter_iter = modelFilterSorted->convert_iter_to_child_iter(filtersorted_iter);
			Gtk::TreeModel::iterator iter = modelFilter->convert_iter_to_child_iter(filter_iter);

			treeviewBoxes->get_selection()->select(iter);
		}
	//}
}

void Terese::on_menuTextFromBoxes_activate() {
	Glib::RefPtr<Gtk::ListStore> styles = project->stylesListStore();
	Glib::RefPtr<Gtk::TreeModel> boxlist = treeviewBoxes->get_model();
	Glib::RefPtr<Gtk::TextBuffer> textbuffer = textView->get_buffer();
	textbuffer->set_text("");
	Gtk::TextBuffer::iterator textit = textbuffer->begin();
	Gtk::TreeModel::Children::iterator boxrowit;

 
	int lastleft = 0;
	float lastrbear = 0.0;


	
	for (boxrowit=boxlist->children().begin();
	     boxrowit != boxlist->children().end(); ++boxrowit)
	{

		
		const int style = (*boxrowit)[boxColumns.style];
		Glib::ustring character = (*boxrowit)[boxColumns.character];
		if (character == "\\n") {
			character="\n";
		}




		
/*
		const Unigram currentUnigram(boxrowit);
		FontBox *fontBox = project->theFont()->getBox(currentUnigram);
		if (fontBox) {
				int left = (*boxrowit)[boxColumns.left];
				float lbear = fontBox->getLbear();
				int corr;
				if (lastleft != 0) {
					corr = left - (lastleft + lastrbear + lbear);
				} else {
					corr = 0;
				}
				if (corr > 3) {
					for (int i = 3; i < corr; ++i) {
						character = "}" + character;
					}
				} else if (corr < -3) {
					for (int i = -3; i > corr; --i) {
						character = "{" + character;
					}
				}
				(*boxrowit)[boxColumns.correlation] = corr;
				lastrbear = fontBox->getRbear();
				lastleft = left;
		} else {
				lastleft = 0;
		}
*/


		
		
		textit=textbuffer->insert(textit, character);

		Gtk::TextBuffer::iterator startit=textit;
		for (int i=0; i<character.length(); i++)
			startit--;
		Gtk::TreeModel::Children::iterator styleit;
		for (styleit=styles->children().begin();
		     styleit != styles->children().end(); ++styleit)
		{
			if (style & (*styleit)[styleColumns.id]) {
				const Glib::RefPtr<Gtk::TextBuffer::Tag> texttag = (*styleit)[styleColumns.texttag];
				textView->get_buffer()->apply_tag(texttag, startit, textit);
			}
		}
		
	}
}

void Terese::on_menuCreateFont_activate() {
	project->createFont();
}

/* Relocate the (single) selected box to a different place in the image. */ 
void Terese::relocateBox(int xpos, int ypos) {
	std::vector< Gtk::TreeModel::Path > selectedRows = treeviewBoxes->get_selection()->get_selected_rows();
	if (selectedRows.size() != 1) {
		return;
	}
	Gtk::TreeModel::iterator rowit = treeviewBoxes->get_model()->get_iter(selectedRows[0]);
	// Change size to that of the corresponding box in the font (if existing)
	// and move the center of the box to the given coordinates.
	const int style = (*rowit)[boxColumns.style];
	const int var = (*rowit)[boxColumns.variant];
	const Glib::ustring character = (*rowit)[boxColumns.character];
	Box *fontBox = project->theFont()->getBox(character, style, var);
	int width, height;
	if (fontBox) {
		width = fontBox->width();
		height = fontBox->height();
	} else {
		width = (*rowit)[boxColumns.right] - (*rowit)[boxColumns.left];
		height = (*rowit)[boxColumns.bottom] - (*rowit)[boxColumns.top];
	}
	(*rowit)[boxColumns.left] = xpos - width/2;
	(*rowit)[boxColumns.top] = ypos - height/2;
	(*rowit)[boxColumns.right] = (*rowit)[boxColumns.left] + width;
	(*rowit)[boxColumns.bottom] = (*rowit)[boxColumns.top] + height;
	(*rowit)[boxColumns.ishelped] = true;
	// Then nudge it into the exact location (compared to the fontbox)
	if (fontBox) {
		readjustBoxes(true);
	}
	drawingArea->queue_draw();
	project->setModified(true);
}

void Terese::on_menuReadjustBoxes_activate() {
	readjustBoxes(false);
}

void Terese::readjustBoxes(bool onlyselected) {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}
		
	int lasttop = 0, lastbot = 0, lastleft = 0, lastright = 0;
	Glib::RefPtr<Gtk::TreeModel> boxlist = treeviewBoxes->get_model();
	Gtk::TreeModel::Children::iterator prevspaceit = boxlist->children().end();
	for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	     rowit != boxlist->children().end(); ++rowit)
	{
		if (onlyselected && !treeviewBoxes->get_selection()->is_selected(rowit)) {
			lastbot = 0;
			continue;
		}
		const Unigram currentUnigram(rowit);
		const int style = currentUnigram.style;
		const int var = currentUnigram.var;
		const Glib::ustring character = currentUnigram.chr;
		if (character == "\\n" || character == " ") {
			if (lastbot != 0) {
				(*rowit)[boxColumns.left] = lastright;
				(*rowit)[boxColumns.right] = lastright + 10;
				(*rowit)[boxColumns.top] = lasttop;
				(*rowit)[boxColumns.bottom] = lastbot;
				lastright = (*rowit)[boxColumns.right];
			}
			if (character == " ") {
				prevspaceit = rowit;
			}
		} else {

			float xdisp, ydisp, corr;
			float bestxdisp, bestydisp, bestcorr = -1;
			int bestvar = 0;
			Box theBox(rowit, img);
			for (int altvar = 0; altvar < 20; altvar++) {
				// int altvar = var;
				Box *fontBox = project->theFont()->getBox(character, style, altvar);
				if (fontBox) {
					corr = fontBox->finddisplacement(&theBox, xdisp, ydisp);
					if (corr > bestcorr) {
						bestcorr = corr;
						bestvar = altvar;
						bestxdisp = xdisp;
						bestydisp = ydisp;
					}
				}
			}

			(*rowit)[boxColumns.correlation] = 100 * bestcorr;
			// If reasonable correlation, snap the box into the correct position.
			if (bestcorr > 0.6) {
				Box *fontBox = project->theFont()->getBox(character, style, bestvar);
				lastleft = (*rowit)[boxColumns.left];
				lasttop = (*rowit)[boxColumns.top];
				lastbot = (*rowit)[boxColumns.top];
				(*rowit)[boxColumns.variant] = bestvar;
				(*rowit)[boxColumns.left] = lastleft + round(bestxdisp);
				(*rowit)[boxColumns.top] = lasttop = lasttop + round(bestydisp);
				(*rowit)[boxColumns.right] = (*rowit)[boxColumns.left] + fontBox->width();
				(*rowit)[boxColumns.bottom] = lastbot = (*rowit)[boxColumns.top] + fontBox->height();
				// The correlation calculated before is not correct,
				// now that the box has moved. So recalculate it.
				theBox = Box(rowit, img);
				corr = fontBox->finddisplacement(&theBox, xdisp, ydisp);
				(*rowit)[boxColumns.correlation] = 100 * corr;
			}
			
			lastleft = (*rowit)[boxColumns.left];
			lasttop = (*rowit)[boxColumns.top];
			lastbot = (*rowit)[boxColumns.bottom];
			lastright = (*rowit)[boxColumns.right];
			if (prevspaceit != boxlist->children().end()) {
				(*prevspaceit)[boxColumns.right] = lastleft;
				int top = (*prevspaceit)[boxColumns.top];
				int bot = (*prevspaceit)[boxColumns.bottom];
				(*prevspaceit)[boxColumns.top] = std::max(lasttop, top);
				(*prevspaceit)[boxColumns.bottom] = std::min(lastbot, bot);
				prevspaceit = boxlist->children().end();
			}
		
		}
	}
	// It would be nice to always show the mask, but it's too slow.
	if (onlyselected) {
		on_menuShowOriginal_activate();
	} else {
		on_menuShowMask_activate(true);
	}
}

void Terese::on_menuReconsiderBoxes_activate() {
	reconsiderBoxes();
}

// The median top amongst the aligned boxes with the highest correlation in the current line.
int linemedboxtop(Gtk::TreeModel::Children::iterator startrowit, Gtk::TreeModel::Children::iterator endrowit) { //, Image* img, Font* font) {
	BoxColumns boxColumns;
	//std::vector<std::pair<float, int> > corrsandtops;
	std::vector<std::pair<int, int> > corrsandtops;
	for (Gtk::TreeModel::Children::iterator rowit = startrowit; rowit != endrowit; ++rowit) {
		const Unigram currentUnigram(rowit);
		const int style = currentUnigram.style;
		const int var = currentUnigram.var;
		const Glib::ustring character = currentUnigram.chr;
		if (character == "\\n") {
			break;
		}
		if (character != " ") {
			const int corr = (*rowit)[boxColumns.correlation];
			const int top = (*rowit)[boxColumns.top];
			corrsandtops.push_back(std::make_pair(corr, top));
			/*
			Box *fontBox = font->getBox(currentUnigram);
			if (fontBox) {
				Box theBox(rowit, img);
				float xdisp, ydisp;
				float corr = fontBox->finddisplacement(&theBox, xdisp, ydisp);
				int top = theBox.top() + round(ydisp);
				corrsandtops.push_back(std::make_pair(corr, top));
			}
			*/
		}
	}
	std::sort(corrsandtops.begin(), corrsandtops.end());
	std::vector<int> tops;
	for (int i = corrsandtops.size() / 2; i < corrsandtops.size(); ++i) {
		tops.push_back(corrsandtops[i].second);
	}
	return median(tops);
}



// The likely top of a box at horizontal position leftpos, compare to surrounding good boxes.
int interpolateboxtop(int leftpos, Gtk::TreeModel::Children::iterator startrowit, Gtk::TreeModel::Children::iterator endrowit) {
	BoxColumns boxColumns;
	////std::vector<std::pair<float, int> > corrsandtops;
	//std::vector<std::pair<int, int> > corrsandtops;
	float weightsum = 0.0;
	float sum = 0.0;
	int top = 0;
	for (Gtk::TreeModel::Children::iterator rowit = startrowit; rowit != endrowit; ++rowit) {
		const Unigram currentUnigram(rowit);
		//const int style = currentUnigram.style;
		//const int var = currentUnigram.var;
		const Glib::ustring character = currentUnigram.chr;
		if (character == "\\n") {
			break;
		}
		top = (*rowit)[boxColumns.top];
		const int corr = (*rowit)[boxColumns.correlation];
		if (character != " " && corr > 60) {
			const int left = (*rowit)[boxColumns.left];
			const int xdist = left - leftpos;
			float weight = (float(corr)/100.0) * std::min(1.0, 10.0 / float(xdist*xdist));
			weightsum += weight;
			sum += top * weight;
		}
	}
	if (weightsum > 0.0)
		return int(sum / weightsum);
	else
		return top;
}


void Terese::reconsiderBoxes() {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}

	std::vector<std::pair<Unigram, Unigram> > confusables;
	std::set<Unigram> allUnigrams = project->theFont()->getAllUnigrams();
	for (std::set<Unigram>::iterator it = allUnigrams.begin(); it != allUnigrams.end(); ++it) {
		confusables.push_back(std::make_pair(*it,*it));
	}
	Glib::RefPtr<Gio::DataInputStream> textstream;
	try {
		Glib::RefPtr<Gio::File> textfile = Gio::File::create_for_path("confusables.txt");
		if (textfile && textfile->query_exists()) {
			textstream = Gio::DataInputStream::create(textfile->read());
		}
	} catch (Glib::Exception &except) {
		throw std::string(except.what());
	} catch (...) {
		throw std::string("Unknown exception!");
	}
	if (textstream) {
		std::string line;
		int sourcestyle, sourcevar, targetstyle, targetvar;
		std::string sourcechr, targetchr;
		while (textstream->read_line(line)) {
			std::stringstream strstream(line);
			strstream >> sourcestyle >> sourcechr >> sourcevar >> targetstyle >> targetchr >> targetvar;
			Glib::ustring usourcechr(sourcechr);
			Glib::ustring utargetchr(targetchr);
			confusables.push_back(std::make_pair(Unigram(usourcechr,sourcestyle,sourcevar),Unigram(utargetchr,targetstyle,targetvar)));
		}
	}

	int fontboxheight = project->theFont()->getBoxHeight();
	//Box lasttypesetbox;
	//Glib::RefPtr<Gtk::TreeModel> = treeviewBoxes->get_model();
	Glib::RefPtr<Gtk::ListStore> boxlist = project->currentBoxList();
	//Glib::RefPtr<Gtk::ListStore> newboxlist = Gtk::ListStore::create(boxColumns);
	int xpos = 0, lastrdev = 0;
	//int currentlinemedboxtop = linemedboxtop(boxlist->children().begin(), boxlist->children().end()); // , img, project->theFont());
	Gtk::TreeModel::Children::iterator firstinlineit = boxlist->children().begin();
	float prevcorr = 0;
	for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	     rowit != boxlist->children().end(); ++rowit)
	{
		int savetop = (*rowit)[boxColumns.top];
		int savebottom = (*rowit)[boxColumns.bottom];
		int saveleft = (*rowit)[boxColumns.left];
		int saveright = (*rowit)[boxColumns.right];
		const int origcorr = (*rowit)[boxColumns.correlation];
		//std::cout << origcorr << std::endl;
		if (origcorr <= 60) {
			//(*rowit)[boxColumns.top] = currentlinemedboxtop;
			(*rowit)[boxColumns.top] = interpolateboxtop(saveleft, firstinlineit, boxlist->children().end());
			(*rowit)[boxColumns.bottom] = (*rowit)[boxColumns.top] + fontboxheight;
		}
		const Unigram currentUnigram(rowit);
		const int style = currentUnigram.style;
		const int var = currentUnigram.var;
		const Glib::ustring character = currentUnigram.chr;
		if (character == "\\n" || character == " ") {
			if (character == "\\n") {
				xpos = 0;
				//Gtk::TreeModel::Children::iterator nextrow = rowit;
				//currentlinemedboxtop = linemedboxtop(++nextrow, boxlist->children().end());
				firstinlineit = rowit;
				firstinlineit++;
			} else {
				rowit = boxlist->erase(rowit);
				rowit--;
			}
		} else {
			float bestcorr = -1.0;
			Box theBox(rowit, img);
			int origwidth = theBox.width();
			int confusablemaxwidth = origwidth;
			for (std::vector<std::pair<Unigram, Unigram> >::iterator it = confusables.begin();
			     it != confusables.end(); ++it) {
				if (it->first.equals(currentUnigram)) {
					Box *fontBox = project->theFont()->getBox(it->second);
					if (fontBox) {
						confusablemaxwidth = std::max(confusablemaxwidth, fontBox->width());
					}
				}
			}
			theBox.setwidth(confusablemaxwidth);
			FontBox *bestFontBox = NULL;
			for (std::vector<std::pair<Unigram, Unigram> >::iterator it = confusables.begin();
			     it != confusables.end(); ++it) {
				if (it->first.equals(currentUnigram)) {
					FontBox *fontBox = project->theFont()->getBox(it->second);
					if (fontBox) {
						float xdisp, ydisp;
						float corr = fontBox->finddisplacement(&theBox, xdisp, ydisp, -10, 10, -5, 5);
						float widthquota = fontBox->width() / float(origwidth);
						//std::cout << it->first.print() << "  " << it->second.print() << "  " << widthquota << " " << corr << std::endl;
						//corr += 0.1 * (widthquota-1); // Ugly hack...
						if (corr > bestcorr) {
							bestcorr = corr;
							bestFontBox = fontBox;
						}
					}
				}
			}
			if (bestFontBox) {
				//std::cout << bestFontBox->unigram().print() << " ";
				(*rowit)[boxColumns.variant] = bestFontBox->unigram().var;
				(*rowit)[boxColumns.style] = bestFontBox->unigram().style;
				(*rowit)[boxColumns.character] = bestFontBox->unigram().chr;


				float xdisp, ydisp, corr;
				Box theBox = Box(rowit, img);
				corr = bestFontBox->finddisplacement(&theBox, xdisp, ydisp, -10, 10, -5, 5);
				//if (lasttypesetbox.img()) {
				//std::cout << bestFontBox->unigram().print() << std::endl;
				//}
				//(*rowit)[boxColumns.correlation] = 100 * corr;

				saveleft = (*rowit)[boxColumns.left] = (*rowit)[boxColumns.left] + int(round(xdisp));
				savetop = (*rowit)[boxColumns.top] = (*rowit)[boxColumns.top] + int(round(ydisp));
				saveright = (*rowit)[boxColumns.right] = (*rowit)[boxColumns.left] + bestFontBox->width();
				savebottom = (*rowit)[boxColumns.bottom] = (*rowit)[boxColumns.top] + bestFontBox->height();
				// The correlation calculated before is not correct,
				// now that the box has moved. So recalculate it.
				theBox = Box(rowit, img);
				corr = bestFontBox->finddisplacement(&theBox, xdisp, ydisp, -10, 10, -5, 5);
				(*rowit)[boxColumns.correlation] = 100 * corr;

				if (xpos > 0) {
					float xdiff = (*rowit)[boxColumns.left] - (xpos + bestFontBox->getLbear());
					float dev = lastrdev + bestFontBox->getLdev();
					//std::cout << bestFontBox->unigram().print() << " " << xdiff << " " << dev << std::endl;
					/*
					if (xdiff < -2 && xdiff < -4*dev && (xdiff/-dev)/(corr+1) > 5) {
						if (corr < prevcorr) {
							rowit = boxlist->erase(rowit);
							rowit--;
							continue;
						} else {
							rowit--;
							rowit = boxlist->erase(rowit);
						}
						//(*rowit)[boxColumns.right] = saveright;
						//std::cout << bestFontBox->unigram().print() << " " << prevcorr << " " << corr << std::endl;
						//std::cout << bestFontBox->unigram().print() << " " << corr << " " << (*rowit)[boxColumns.left] - (xpos + bestFontBox->getLbear())  << " " << lastrdev + bestFontBox->getLdev() << std::endl;
					}
					*/
					if ((xdiff > 3 && xdiff > 10*dev || xdiff > 15) && (saveleft-xpos) > 8) {
						//std::cout << bestFontBox->unigram().print() << " " << xdiff << " " << dev << std::endl;
						rowit = boxlist->insert(rowit);
						(*rowit)[boxColumns.character] = " ";
						(*rowit)[boxColumns.style] = 0;
						(*rowit)[boxColumns.variant] = 0;
						(*rowit)[boxColumns.correlation] = 0;
						(*rowit)[boxColumns.degenerate] = false;
						(*rowit)[boxColumns.left] = xpos;
						(*rowit)[boxColumns.right] = saveleft;
						(*rowit)[boxColumns.top] = savetop;
						(*rowit)[boxColumns.bottom] = savebottom;
						rowit++;
					}
				}
				
				xpos = (*rowit)[boxColumns.left] + bestFontBox->getRbear();
				lastrdev = bestFontBox->getRdev();
				prevcorr = corr;
				//std::cout << std::endl;
				
			} else {
				xpos = 0;
				prevcorr = 0;
			}
		}
		//(*rowit)[boxColumns.top] = savetop;
		//(*rowit)[boxColumns.bottom] = savebottom;
		//(*rowit)[boxColumns.left] = saveleft;
		//(*rowit)[boxColumns.right] = saveright;
	}
	project->resolveStyleAmbiguities(project->getActivePage());
	//on_menuShowMask_activate(true);
}

void Terese::on_menuBatch_activate() {
	Glib::RefPtr<Gtk::TreeModel> pagelist = treeviewPages->get_model();
	int c = 0;
	for (Gtk::TreeModel::Children::iterator rowit = pagelist->children().begin();
	     rowit != pagelist->children().end(); ++rowit)
	{
		updateProgress(c/float(pagelist->children().size()),"Batch processing...");
		Page *thepage = (*rowit)[pagesColumns.page];
		showPage(thepage);

		readjustBoxes(false);
		reconsiderBoxes();

		/* Delete overlapping boxes */
		
		Glib::RefPtr<Gtk::ListStore> boxlist = project->currentBoxList();
		for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	  	      rowit != boxlist->children().end(); )
		{
			//std::cout << (*rowit)[boxColumns.character] << std::endl;

			bool haserased = false;
			while (rowit != boxlist->children().end() &&
			       (*rowit)[boxColumns.character] != "\\n" && (*rowit)[boxColumns.character] != " " &&
			       (*rowit)[boxColumns.correlation] < 0) {
				rowit = boxlist->erase(rowit);
				haserased = true;
			}
			if (!haserased && rowit != boxlist->children().end()) {
				++rowit;
			}
		}

		for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	  	      rowit != boxlist->children().end(); )
		{
			bool haserased = false;
			Gtk::TreeModel::Children::iterator peekit = rowit;
			++peekit;
			if (peekit != boxlist->children().end() &&
			    (*rowit)[boxColumns.character] != "\\n" && (*rowit)[boxColumns.character] != " " &&
			    (*peekit)[boxColumns.character] != "\\n" && (*peekit)[boxColumns.character] != " ") {

				const Unigram thisUnigram(rowit);
				const Unigram nextUnigram(peekit);
				FontBox *thisFontBox = project->theFont()->getBox(thisUnigram);
				FontBox *nextFontBox = project->theFont()->getBox(nextUnigram);
				if (thisFontBox && nextFontBox) {
					int thisleft = (*rowit)[boxColumns.left];
					float thisrbear = thisFontBox->getRbear();
					float thisrdev = thisFontBox->getRdev();
					int nextleft = (*peekit)[boxColumns.left];
					float nextlbear = nextFontBox->getLbear();
					float nextldev = nextFontBox->getLdev();
					float err = nextleft - (thisleft + thisrbear + nextlbear) + thisrdev + nextldev;
					if (err < -10) {
						Glib::ustring thischar = (*rowit)[boxColumns.character];
						Glib::ustring peekchar = (*peekit)[boxColumns.character];
						if ( (*rowit)[boxColumns.correlation] >= (*peekit)[boxColumns.correlation] ||
						    thischar.length() > 1 && peekchar.length() == 1 && thischar.at(thischar.length() - 1) == peekchar.at(0) ||
						    thischar == "—" && peekchar == "-"
						    ) {
							rowit = boxlist->erase(peekit);
							haserased = true;							
						} else {
							rowit = boxlist->erase(rowit);
							haserased = true;
						}
					} else if (err < -5 || err < -2 && (*rowit)[boxColumns.character] != "-" && (*peekit)[boxColumns.character] != "-" && (*peekit)[boxColumns.character] != "," ) {
					   //std::cout << err << " " << (*rowit)[boxColumns.character] << (*rowit)[boxColumns.correlation] << " " << (*peekit)[boxColumns.character] << (*peekit)[boxColumns.correlation] << std::endl;
						if ( (*rowit)[boxColumns.correlation] > 85 && (*peekit)[boxColumns.correlation] < 80 ) {
							rowit = boxlist->erase(peekit);
							haserased = true;							
						} else if ( (*rowit)[boxColumns.correlation] < 80 && (*peekit)[boxColumns.correlation] > 85 ) {
							rowit = boxlist->erase(rowit);
							haserased = true;
						}
					}
					if (!haserased && err < -15 && thisUnigram.equals(nextUnigram)) {
						rowit = boxlist->erase(peekit);
						haserased = true;							
					}
				}
			
			}
			if (!haserased && rowit != boxlist->children().end()) {
				++rowit;
			}
		}


		for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	  	      rowit != boxlist->children().end(); )
		{
			bool haserased = false;
			while (rowit != boxlist->children().end() &&
			       (*rowit)[boxColumns.character] != "\\n" && (*rowit)[boxColumns.character] != " " && (*rowit)[boxColumns.correlation] < 20 ||
			       (*rowit)[boxColumns.correlation] < 40 && ( (*rowit)[boxColumns.character] == "," || (*rowit)[boxColumns.character] == "." ) ) {
				rowit = boxlist->erase(rowit);
				haserased = true;
			}
			if (!haserased && rowit != boxlist->children().end()) {
				++rowit;
			}
		}


		readjustBoxes(false);
		//reconsiderBoxes();
		
		project->resolveStyleAmbiguities(project->getActivePage());
		on_menuTextFromBoxes_activate();
		c++;
	}
	updateProgress(0,"");
}

void Terese::on_menuBatch2_activate() {
	Glib::RefPtr<Gtk::TreeModel> pagelist = treeviewPages->get_model();
	int c = 0;
	for (Gtk::TreeModel::Children::iterator rowit = pagelist->children().begin();
	     rowit != pagelist->children().end(); ++rowit)
	{
		updateProgress(c/float(pagelist->children().size()),"Batch processing step 2...");
		Page *thepage = (*rowit)[pagesColumns.page];
		showPage(thepage);

		//reconsiderBoxes();
		//on_menuTextFromBoxes_activate();
		
		//on_menuSegment_activate();
			
		//straightenLines();
		//on_menuMapText_activate();
		//readjustBoxes(false);
		//on_menuMapText_activate();
		//reconsiderBoxes();
		//readjustBoxes(false);
		project->resolveStyleAmbiguities(project->getActivePage());
		on_menuTextFromBoxes_activate();

/*
		int lastleft = 0;
		float lastrbear = 0.0;
		Glib::RefPtr<Gtk::ListStore> boxlist = project->currentBoxList();
		for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	  	      rowit != boxlist->children().end(); ++rowit)
		{
			const Unigram currentUnigram(rowit);
			FontBox *fontBox = project->theFont()->getBox(currentUnigram);
			if (fontBox) {
				int left = (*rowit)[boxColumns.left];
				float lbear = fontBox->getLbear();
				if (lastleft != 0) {
					(*rowit)[boxColumns.correlation] = left - (lastleft + lastrbear + lbear);
				} else {
					(*rowit)[boxColumns.correlation] = 0;
				}
				lastrbear = fontBox->getRbear();
				lastleft = left;
			} else {
				lastleft = 0;
			}
		}
*/

		//project->resolveStyleAmbiguities(project->getActivePage());
		//on_menuTextFromBoxes_activate();
		c++;
	}
	updateProgress(0,"");
}

/*
void Terese::on_menuBatch2_activate() {
	Glib::RefPtr<Gtk::TreeModel> pagelist = treeviewPages->get_model();
	int c = 0;
	for (Gtk::TreeModel::Children::iterator rowit = pagelist->children().begin();
	     rowit != pagelist->children().end(); ++rowit)
	{
		updateProgress(c/float(pagelist->children().size()),"Batch processing step 2...");
		Page *thepage = (*rowit)[pagesColumns.page];
		showPage(thepage);

		double prevpos = 0;
		double prevrdev = 0;
		Unigram prevunigram;
		Glib::RefPtr<Gtk::ListStore> boxlist = project->currentBoxList();
		for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	  	      rowit != boxlist->children().end(); rowit++ )
		{
			if ( (*rowit)[boxColumns.right] <= (*rowit)[boxColumns.left] ) {
				(*rowit)[boxColumns.right] = (*rowit)[boxColumns.left] + 10;
			}
			if ( (*rowit)[boxColumns.bottom] <= (*rowit)[boxColumns.top] ) {
				(*rowit)[boxColumns.bottom] = (*rowit)[boxColumns.top] + 50;
			}
			if ( (*rowit)[boxColumns.bottom] - (*rowit)[boxColumns.top] > 150 ) {
				(*rowit)[boxColumns.bottom] = (*rowit)[boxColumns.top] + 100;
			}

			const Unigram currentUnigram(rowit);
			FontBox *fontBox = project->theFont()->getBox(currentUnigram);
			if ( !(*rowit)[boxColumns.degenerate] && (*rowit)[boxColumns.correlation] > 50 && fontBox) {
				if (prevpos > 0) {
					double deviation = std::max(1.0, prevrdev + fontBox->getRdev());
					double diff = std::abs((*rowit)[boxColumns.left] - (prevpos + fontBox->getLbear())) / deviation;
					if (diff > 5) {
						//std::cout << prevunigram.print() << " " << currentUnigram.print() << " " << diff << std::endl;
						int style = (*rowit)[boxColumns.style];
						int left = (*rowit)[boxColumns.left];
						int top = (*rowit)[boxColumns.top];
						int bottom = (*rowit)[boxColumns.bottom];
						rowit = boxlist->insert(rowit);
						(*rowit)[boxColumns.character] = " ";
						(*rowit)[boxColumns.style] = style;
						(*rowit)[boxColumns.variant] = 0;
						(*rowit)[boxColumns.correlation] = 0;
						(*rowit)[boxColumns.degenerate] = false;
						(*rowit)[boxColumns.left] = prevpos;
						(*rowit)[boxColumns.right] = left;
						(*rowit)[boxColumns.top] = top;
						(*rowit)[boxColumns.bottom] = bottom;
						rowit++;
						
					}
				}
				prevpos = (*rowit)[boxColumns.left] + fontBox->getRbear();
				prevrdev = fontBox->getRdev();
			} else {
				prevpos = 0;
			}
			prevunigram = currentUnigram;
		}
		on_menuTextFromBoxes_activate();
		
		c++;
	}
	updateProgress(0,"");
}
*/

void Terese::on_menuShowOriginal_activate() {
	drawingArea->on_showPageImage(project->currentPixbuf());
}

Image Terese::getMask(Image* img) {
	Image maskImg(img->width(),img->height());
	Glib::RefPtr<Gtk::TreeModel> boxlist = treeviewBoxes->get_model();
	for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	     rowit != boxlist->children().end(); ++rowit)
	{
		const int left = (*rowit)[boxColumns.left];
		const int top = (*rowit)[boxColumns.top];
		const int style = (*rowit)[boxColumns.style];
		const int var = (*rowit)[boxColumns.variant];
		const Glib::ustring chr = (*rowit)[boxColumns.character];
		Box *fontBox = project->theFont()->getBox(chr, style, var);
		if (fontBox) {
			maskImg.addbox(fontBox, left, top);
		}
	}
	return maskImg;
}

void Terese::on_menuShowMask_activate(bool overlay) {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}
	Image maskImg = Terese::getMask(img);
	if (overlay) {
		drawingArea->on_showPageImage(img->toPixbuf(&maskImg));
	} else {
		drawingArea->on_showPageImage(maskImg.toPixbuf(NULL));
	}
}

void Terese::on_menuMapText_activate() {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}
	Image maskImg(img->width(),img->height());
	Glib::RefPtr<Gtk::ListStore> boxlist = project->currentBoxList();//treeviewBoxes->get_model();
	Glib::RefPtr<Gtk::TextBuffer> textbuffer = textView->get_buffer();
   Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin(), rowpeek;
   Gtk::TextBuffer::iterator textit = textbuffer->begin(), textpeek;
	Glib::ustring::iterator stringit;

	const int paragraphindent = 93;
	
	bool issynced = true;
	int xpos = 0, ypos = 0;
	double prevrightdev, ydev;
	int boxwidth, boxheight;
	Unigram currentunigram;
	bool firstinline = true;
	int prevlinestartx = 0, prevlinestarty = 0;

	while (textit != textbuffer->end()) {
		
		if (issynced) {
			// We are under the impression that the list and the text say the same thing.
			// But that can change! Does the current row (if any!) correspond to the text at its current location?
			if (rowit != boxlist->children().end()) {
				textpeek = textit;
				Glib::ustring chr = unescapeSpace((*rowit)[boxColumns.character]);
				const int style = (*rowit)[boxColumns.style];
				for (Glib::ustring::iterator stringit = chr.begin();
				     stringit != chr.end(); ++stringit, ++textpeek) {
					if ( textpeek == textbuffer->end() ||
					     (*stringit) != (*textpeek) ||
					     style != project->styleOfText(textpeek) ) {
						issynced = false;
						break;
					}
				}
			} else {
				issynced = false;
			}
		}
		
		// If the text has changed at the current position, we have to fix the list.
		if (!issynced) {
			Glib::ustring chr = Glib::ustring(1,*textit);
			float bestcorr = -1;
			if (chr == " ") {
				currentunigram = Unigram(chr, project->styleOfText(textit), 0);
				boxwidth = 10;
				boxheight = 20;
				bestcorr = 0;
			} else if (chr == "\n") {
				currentunigram = Unigram("\\n", project->styleOfText(textit), 0);
				boxwidth = 10;
				boxheight = 20;
				bestcorr = 0;
			} else {
				std::set<Unigram> possibleunigrams = project->unigramCandidates(textit);
				if (possibleunigrams.size() == 0) {
					currentunigram = Unigram(chr, project->styleOfText(textit), 0);
					boxwidth = 30;
					boxheight = 40;
					bestcorr = 0;
				} else {
					int newxpos, newypos;
					for (std::set<Unigram>::iterator it = possibleunigrams.begin();
					     it != possibleunigrams.end(); ++it) {
						FontBox *fontbox = project->theFont()->getBox(*it);
						double xdev = prevrightdev + fontbox->getLdev();
						Box windowbox(Unigram(), xpos + fontbox->getLbear() - xdev, ypos - ydev, 2*xdev + fontbox->width(), 2*ydev + fontbox->height(), img);
/*
				// Temp for debugging		
				rowit = boxlist->insert(rowit);
				(*rowit)[boxColumns.character] = "?"+it->chr;
				(*rowit)[boxColumns.style] = it->style;
				(*rowit)[boxColumns.variant] = it->var;
				(*rowit)[boxColumns.correlation] = 100*bestcorr;
				(*rowit)[boxColumns.degenerate] = false;
				(*rowit)[boxColumns.left] = windowbox.left();
				(*rowit)[boxColumns.right] = windowbox.right();
				(*rowit)[boxColumns.top] = windowbox.top();
				(*rowit)[boxColumns.bottom] = windowbox.bot();
				return;
	*/
						float xdisp, ydisp;
						float corr = fontbox->finddisplacement(&windowbox, xdisp, ydisp, -fontbox->width(), 2*xdev + fontbox->width(), 0, 2*ydev, 0.7);
						//float corr = fontbox->finddisplacement(&windowbox, xdisp, ydisp);

						if (corr > bestcorr) {
							bestcorr = corr;
							newxpos = round(xdisp) + xpos + fontbox->getLbear() - xdev;
							newypos = round(ydisp) + ypos - ydev;
							currentunigram = *it;
							boxwidth = fontbox->width();
							boxheight = fontbox->height();
						}
					}
					xpos = newxpos;
					ypos = newypos;
				}
			}
			// Great, we now have a character that should be added to the list!
			// But maybe it already exists? In that case, we better find it,
			// so that we can reuse the following list rows, (if unchanged!)
			// and not have to redo all that work.
			for (rowpeek = rowit; rowpeek != boxlist->children().end(); ++rowpeek) {
				if ((*rowpeek)[boxColumns.character] == currentunigram.chr &&
				    (*rowpeek)[boxColumns.style] == currentunigram.style &&
				    (*rowpeek)[boxColumns.variant] == currentunigram.var &&
				    (*rowpeek)[boxColumns.left] == xpos &&
				    (*rowpeek)[boxColumns.top] == ypos
				    /* xpos + boxwidth/2 > (*rowpeek)[boxColumns.left] &&
				    xpos + boxwidth/2 < (*rowpeek)[boxColumns.right] &&
				    ypos + boxheight/2 > (*rowpeek)[boxColumns.top] &&
				    ypos + boxheight/2 < (*rowpeek)[boxColumns.bottom]*/ ) {
					break;
				}
			}
			if (rowpeek == boxlist->children().end()) {
				// Nope. Add it at the current location.
				rowit = boxlist->insert(rowit);
				(*rowit)[boxColumns.character] = currentunigram.chr;
				(*rowit)[boxColumns.style] = currentunigram.style;
				(*rowit)[boxColumns.variant] = currentunigram.var;
				(*rowit)[boxColumns.correlation] = 100*bestcorr;
				(*rowit)[boxColumns.degenerate] = false;
				(*rowit)[boxColumns.left] = xpos;
				(*rowit)[boxColumns.right] = xpos + boxwidth;
				(*rowit)[boxColumns.top] = ypos;
				(*rowit)[boxColumns.bottom] = ypos + boxheight;

				// Tillagdt 2018-09:
				if ((*rowit)[boxColumns.correlation] < 15 && chr != " " && chr != "\n") {
					drawingArea->on_showPageImage(img->toPixbuf(&maskImg));
					return;
				}
				
			} else {
				// Yep! Remove the invalid intermediate rows.
				while (rowit != rowpeek) {
					rowit = boxlist->erase(rowit);
				}
				// We now presume that we have resynced, and that the following
				// list rows are correct.
				issynced = true;
			}
			
		} else {
			// Text has not changed. Read from the list instead:
			currentunigram = Unigram(rowit);
			xpos = (*rowit)[boxColumns.left];
			ypos = (*rowit)[boxColumns.top];
		}

		if (firstinline && currentunigram.chr != "\\n") {
			prevlinestartx = xpos;
			prevlinestarty = ypos;
			firstinline = false;
		}

		if (prevlinestartx == 0 && prevlinestarty == 0 && currentunigram.chr != "\\n" && currentunigram.chr != " ") {
			prevlinestartx = xpos - paragraphindent;
			prevlinestarty = ypos;
		}

		if ((*rowit)[boxColumns.ishelped]) {
			(*rowit)[boxColumns.ishelped] = false;
			issynced = false;
		}
		
		// Prepare for the next row:
		if (currentunigram.chr == " ") {
			prevrightdev = (project->theFont()->getMaxSpace() - project->theFont()->getMinSpace()) / 2;
			xpos = xpos + project->theFont()->getMinSpace() + prevrightdev;
			//issynced = true; // TILLAGDT NU 2017!!!!!!
		} else if (currentunigram.chr == "\\n") {
			if (firstinline && prevlinestartx == xpos) { // (prevlinestartx == xpos && ypos == prevlinestarty) {
				xpos = xpos + paragraphindent;
				//ypos = ypos + 100;
				firstinline = false;
				prevlinestarty = ypos;
			} else {
				ypos = prevlinestarty + project->theFont()->getLineSpacing();
				ydev = 20;
				xpos = prevlinestartx;
				prevrightdev = 50;
				firstinline = true;
			}
		} else {
			FontBox *fontbox = project->theFont()->getBox(currentunigram);
			if (fontbox) {
				maskImg.addbox(fontbox, xpos, ypos);
				xpos = xpos + fontbox->getRbear();
				prevrightdev = fontbox->getRdev();
				ypos = ypos;
				ydev = 5;
			} else {
				xpos = xpos + 30;
				prevrightdev = 30;
			}
		}
		
		++rowit;
		currentunigram.chr = unescapeSpace(currentunigram.chr);
		for (Glib::ustring::iterator stringit = currentunigram.chr.begin();
		     stringit != currentunigram.chr.end(); ++stringit) {
			textit++;
		}
	}

	// Clean up the end of the list.
	while (rowit != boxlist->children().end()) {
		rowit = boxlist->erase(rowit);
	}
	drawingArea->on_showPageImage(img->toPixbuf(&maskImg));
	//project->theFont()->typeset(boxlist);
}


void Terese::on_menuOCR_activate() {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}
	Image maskImg(img->width(),img->height());

	updateProgress(0, "Calculating fourier transform of page image.");
		
	int width = img->width();
	int height = img->height();
	double scale = 1.0 / (width * height);

	double *pageImg, *boxImg, *corrImg;
	fftw_complex *fourPage, *fourBox, *fourCorr;

	pageImg = fftw_alloc_real(width * height);
	boxImg = fftw_alloc_real(width * height);
	corrImg = fftw_alloc_real(width * height);

	fourPage = fftw_alloc_complex(width * (height/2+1));
	fourBox = fftw_alloc_complex(width * (height/2+1));
	fourCorr = fftw_alloc_complex(width * (height/2+1));

	fftw_plan pagePlan, boxPlan, invPlan;

	pagePlan = fftw_plan_dft_r2c_2d(width, height, pageImg, fourPage, FFTW_ESTIMATE);
	boxPlan = fftw_plan_dft_r2c_2d(width, height, boxImg, fourBox, FFTW_ESTIMATE);
	invPlan = fftw_plan_dft_c2r_2d(width, height, fourCorr, corrImg, FFTW_ESTIMATE);

	for (int x = 0; x < width; ++x) {
		for (int y = 0; y < height; ++y) {
			pageImg[y+height*x] = img->pixel(x,y);
			boxImg[y+height*x] = 0;
		}
	}

	fftw_execute(pagePlan);

	std::vector<DataPoint*> candidates;
	std::vector<DataPoint*> foundchars;
	std::vector<FontBox> FontBoxes = project->theFont()->getFontBoxes();
	for (std::vector<FontBox>::iterator fontBox = FontBoxes.begin(); fontBox != FontBoxes.end(); ++fontBox) {
		updateProgress((std::distance(FontBoxes.begin(), fontBox)+1) / float(FontBoxes.size()),
		    "Finding correlations for glyph " + fontBox->unigram().chr);

		float blackness = 0;
		for (int x = 0; x < fontBox->width(); ++x) {
			for (int y = 0; y < fontBox->height(); ++y) {
				double pix = fontBox->pixel(x,y) * 2 - 1;
				boxImg[(height-y)+height*(width-x)] = pix;
				if (pix > 0) {
					blackness += pix;
				}
			}
		}

		fftw_execute(boxPlan);

		for (int x = 0; x < fontBox->width(); ++x) {
			for (int y = 0; y < fontBox->height(); ++y) {
				boxImg[(height-y)+height*(width-x)] = 0;
			}
		}

		for (int i = 0; i < width; ++i) {
			for (int j = 0; j < height/2+1; ++j) {
				int ij = i*(height/2+1) + j;
				fourCorr[ij][0] = (fourPage[ij][0] * fourBox[ij][0] - fourPage[ij][1] * fourBox[ij][1]) * scale;
				fourCorr[ij][1] = (fourPage[ij][0] * fourBox[ij][1] + fourPage[ij][1] * fourBox[ij][0]) * scale;
			}
		}

		fftw_execute(invPlan);

		std::vector<DataPoint*> coords;

		//Image convolution(width, height);
		for (int x = 0; x < width; ++x) {
			for (int y = 0; y < height; ++y) {
				float correlation = corrImg[y+height*x];
				if (correlation/blackness > 0.7) { // Change to 0.5 or even lower for fuzzy images, or up towards 0.85 for really good scans.
					coords.push_back(new DataPoint(Box(fontBox->unigram(), x, y, fontBox->width(), fontBox->height(), img), correlation/blackness));
				}
				//convolution(x,y) = correlation; //std::max(float(0.0), correlation);
			}
		}
		/*
		convolution.normalize();
		for (int x = 0; x < fontBox->width(); ++x) {
			for (int y = 0; y < fontBox->height(); ++y) {
				convolution(x,y)=fontBox->pixel(x,y);
			}
		}
		convolution.savepng("convolution.png");
		*/

		std::sort(coords.begin(), coords.end(), DataPoint::SortFallingCorr);

		// Save only the peaks (clean the data by removing high correlating coordinates around the peaks)
		for (std::vector<DataPoint*>::iterator coordIt = coords.begin();
		     coordIt != coords.end(); ++coordIt) {
			if ((*coordIt)->corr != 0.0) {
				candidates.push_back(*coordIt);
				for (std::vector<DataPoint*>::iterator otherIt = coordIt+1;
				    otherIt != coords.end(); ++otherIt) {
					if (std::abs((*coordIt)->box.left() - (*otherIt)->box.left()) < 10 && // The size of the neighbourhood may have to be adjusted...
					    std::abs((*coordIt)->box.top() - (*otherIt)->box.top()) < 10) {
						(*otherIt)->corr = 0.0;
					}
				}
			}
		}

	}
	
	fftw_destroy_plan(pagePlan);
	fftw_destroy_plan(boxPlan);
	fftw_destroy_plan(invPlan);
	fftw_free(pageImg);
	fftw_free(boxImg);
	fftw_free(corrImg);
	fftw_free(fourPage);
	fftw_free(fourBox);
	fftw_free(fourCorr);

	// Remove the worst of overlapping boxes and save the remaining to foundchars
	std::sort(candidates.begin(), candidates.end(), DataPoint::SortFallingCorr);
	for (std::vector<DataPoint*>::iterator it = candidates.begin(); it != candidates.end(); ++it) {
		if ((*it)->corr > 0) {
			foundchars.push_back(*it);
			const int l1 = (*it)->box.left();
			const int w1 = (*it)->box.width();
			const int r1 = (*it)->box.right();
			const int t1 = (*it)->box.top();
			const int h1 = (*it)->box.height();
			const int b1 = (*it)->box.bot();
			for (std::vector<DataPoint*>::iterator jt = it+1; jt != candidates.end(); ++jt) {
				const int l2 = (*jt)->box.left();
				const int w2 = (*jt)->box.width();
				const int r2 = (*jt)->box.right();
				const int t2 = (*jt)->box.top();
				const int h2 = (*jt)->box.height();
				const int b2 = (*jt)->box.bot();
				const int xoverlap = std::max(0, std::min(r1,r2) - std::max(l1,l2));
				const int yoverlap = std::max(0, std::min(b1,b2) - std::max(t1,t2));
				if (xoverlap*yoverlap > std::min(w1*h1, w2*h2) / 4) {
					// But some boxes legitimely overlap, e.g. italics, so perhaps we should check for that.
					// But we do that some other day...
					(*jt)->corr = 0;
				}
			}
		}
	}
		
	// Cluster the lines
	int numLines = DataPoint::RunDBScan(foundchars);

	std::sort(foundchars.begin(), foundchars.end(), DataPoint::SortOnPage);

	project->currentBoxList()->clear();
	for (std::vector<DataPoint*>::iterator it = foundchars.begin();
	     it != foundchars.end(); ++it) {
		if ((*it)->cluster > 0) {
			Gtk::TreeModel::Row boxrow = *(project->currentBoxList()->append());
			boxrow[boxColumns.character] = (*it)->box.unigram().chr;
			boxrow[boxColumns.style] = (*it)->box.unigram().style;
			boxrow[boxColumns.variant] = (*it)->box.unigram().var;
			boxrow[boxColumns.correlation] = (*it)->corr * 100;
			boxrow[boxColumns.degenerate] = false;
			boxrow[boxColumns.left] = (*it)->box.left();
			boxrow[boxColumns.right] = (*it)->box.left() + (*it)->box.width();
			boxrow[boxColumns.top] = (*it)->box.top();
			boxrow[boxColumns.bottom] = (*it)->box.top() + (*it)->box.height();

			if (it+1 != foundchars.end()) {
				if ((*(it+1))->cluster != (*it)->cluster) {
					Gtk::TreeModel::Row boxrow = *(project->currentBoxList()->append());
					boxrow[boxColumns.character] = "\\n";
					boxrow[boxColumns.style] = 0;
					boxrow[boxColumns.variant] = 0;
					boxrow[boxColumns.correlation] = 100;
					boxrow[boxColumns.degenerate] = false;
					boxrow[boxColumns.left] = (*it)->box.right();
					boxrow[boxColumns.right] = (*it)->box.right() + 10;
					boxrow[boxColumns.top] = (*it)->box.top();
					boxrow[boxColumns.bottom] = (*it)->box.top() + (*it)->box.height();
				} else {
					const float secondLbear = project->theFont()->getBox((*(it+1))->box.unigram())->getLbear();
					const float firstRbear = project->theFont()->getBox((*it)->box.unigram())->getRbear();
					const float secondLdev = project->theFont()->getBox((*(it+1))->box.unigram())->getLdev();
					const float firstRdev = project->theFont()->getBox((*it)->box.unigram())->getRdev();
					const int firstXpos = (*it)->box.left();
					const int secondXpos = (*(it+1))->box.left();
					if ( (secondXpos - secondLbear) - (firstXpos + firstRbear) > 1.5*(firstRdev + secondLdev) ) {
						Gtk::TreeModel::Row boxrow = *(project->currentBoxList()->append());
						boxrow[boxColumns.character] = " ";
						boxrow[boxColumns.style] = 0;
						boxrow[boxColumns.variant] = 0;
						boxrow[boxColumns.correlation] = 100;
						boxrow[boxColumns.degenerate] = false;
						boxrow[boxColumns.left] = (*it)->box.right();
						boxrow[boxColumns.right] = (*(it+1))->box.left();
						boxrow[boxColumns.top] = (*it)->box.top();
						boxrow[boxColumns.bottom] = (*it)->box.top() + (*it)->box.height();
					}
				}
			}
		}
	}
	project->resolveStyleAmbiguities(project->getActivePage());
	on_menuTextFromBoxes_activate();
	treeviewBoxes->set_model(project->currentBoxList(), project->currentPixbuf());
	updateProgress(0,"");
}

bool markSegment(int startx, int y, int segnum, Image* img, Matrix<int>& belonging) {
	/*
	int x = startx;
	if (img->pixel(x,y) > 0.5 && belonging(x,y) == 0) {
		belonging(x,y) = segnum;
		markSegment(x-1, y, segnum, img, belonging);
		markSegment(x, y-1, segnum, img, belonging);
		markSegment(x+1, y, segnum, img, belonging);
		markSegment(x, y+1, segnum, img, belonging);
		markSegment(x-1, y-1, segnum, img, belonging);
		markSegment(x-1, y+1, segnum, img, belonging);
		markSegment(x+1, y-1, segnum, img, belonging);
		markSegment(x+1, y+1, segnum, img, belonging);
		return true;
	}
	return false;
	*/
	if (!(img->pixel(startx, y) > 0.5 && belonging(startx, y) == 0)) {
		return false;
	}
	int minx = startx;
	while (img->pixel(minx, y) > 0.5 && belonging(minx, y) == 0) {
		belonging(minx, y) = segnum;
		minx--;
	}
	int maxx = startx+1;
	while (img->pixel(maxx, y) > 0.5 && belonging(maxx, y) == 0) {
		belonging(maxx, y) = segnum;
		maxx++;
	}
	markSegment(minx, y-1, segnum, img, belonging);
	markSegment(minx, y+1, segnum, img, belonging);
	markSegment(maxx, y-1, segnum, img, belonging);
	markSegment(maxx, y+1, segnum, img, belonging);
	for (int x = minx+1; x < maxx; x++) {
		markSegment(x, y-1, segnum, img, belonging);
		markSegment(x, y+1, segnum, img, belonging);
	}
	return true;
}

void Terese::appendNewBox(int left, int right, int top, int bot, Glib::ustring chr, int style, int var, bool deg) {
	Gtk::TreeModel::Row boxrow = *(project->currentBoxList()->append());
	boxrow[boxColumns.character] = chr;
	boxrow[boxColumns.style] = style;
	boxrow[boxColumns.variant] = var;
	boxrow[boxColumns.correlation] = 0;
	boxrow[boxColumns.degenerate] = deg;
	boxrow[boxColumns.left] = left;
	boxrow[boxColumns.right] = right;
	boxrow[boxColumns.top] = top;
	boxrow[boxColumns.bottom] = bot;
}

void Terese::on_menuSegment_activate() {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}
	const int pagewidth = img->width();
	const int pageheight = img->height();
	Matrix<int> belonging(pagewidth, pageheight);
	belonging.reset();
	int numsegments = 0;
	for (int y = 0; y < pageheight; ++y) {
		for (int x = 0; x < pagewidth; ++x) {
			if (markSegment(x, y, numsegments+1, img, belonging)) {
				++numsegments;
			}
		}
	}
	int maxx[numsegments], maxy[numsegments], minx[numsegments], miny[numsegments];
	for (int i = 0; i < numsegments; ++i) {
		maxx[i] = 0;
		maxy[i] = 0;
		minx[i] = pagewidth;
		miny[i] = pageheight;
	}
	for (int y = 0; y < pageheight; ++y) {
		for (int x = 0; x < pagewidth; ++x) {
			const int seg = belonging(x,y) - 1;
			if (seg >= 0) {
				if (x > maxx[seg]) maxx[seg] = x;
				if (x < minx[seg]) minx[seg] = x;
				if (y > maxy[seg]) maxy[seg] = y;
				if (y < miny[seg]) miny[seg] = y;
			}
		}
	}
	std::vector<int> boxwidths;
	std::vector<DataPoint*> segments;
	for (int i = 0; i < numsegments; ++i) {
		const int width = maxx[i]-minx[i];
		const int height = maxy[i]-miny[i];
		if (width*height > 8 && !(width > pagewidth/2 || height > pageheight/2)) { // Clean specks and too large stuff
			//appendNewBox(minx[i], maxx[i], miny[i], maxy[i]);
			segments.push_back(new DataPoint(Box(Unigram(), minx[i], miny[i], width, height, NULL), 0));
			boxwidths.push_back(width);
		}
	}

	const int spaceestimate = median(boxwidths, 0.1); // Wild guess.
	int numclusters = DataPoint::clusterLines(segments);
	std::sort(segments.begin(), segments.end(), DataPoint::SortOnPage);
	segments.push_back(new DataPoint()); // A dummy element.
	segments.back()->cluster = numclusters;
	
	project->currentBoxList()->clear();
	std::vector<DataPoint*>::iterator it = segments.begin();
	int prevcluster = (*it)->cluster;
	int prevleft = (*it)->box.left();
	int prevright = (*it)->box.right();
	int prevtop = (*it)->box.top();
	int prevbot = (*it)->box.bot();
	it++;
	for ( ; it != segments.end(); ++it) {
		if ((*it)->cluster != prevcluster) {
			appendNewBox(prevleft, prevright, prevtop, prevbot);
			appendNewBox(prevright, prevright+10, prevtop, prevbot, "\\n");
			prevcluster = (*it)->cluster;
			prevleft = (*it)->box.left();
			prevright = (*it)->box.right();
			prevtop = (*it)->box.top();
			prevbot = (*it)->box.bot();
		} else {
			// Merge horizontally overlapping boxes
			const int firstmid = (prevleft + prevright)/2;
			const int secondmid = ((*it)->box.left()+(*it)->box.right())/2;
			if (firstmid > (*it)->box.left() || secondmid < prevright) {
				prevleft = std::min(prevleft, (*it)->box.left());
				prevright = std::max(prevright, (*it)->box.right());
				prevtop = std::min(prevtop, (*it)->box.top());
				prevbot = std::max(prevbot, (*it)->box.bot());
			} else {
				appendNewBox(prevleft, prevright, prevtop, prevbot);
				if ((*it)->box.left() - prevright > spaceestimate) {
					appendNewBox(prevright+1, (*it)->box.left()-1, std::min(prevtop,(*it)->box.top()), std::max(prevbot,(*it)->box.bot()), " ");
				}
				prevcluster = (*it)->cluster;
				prevleft = (*it)->box.left();
				prevright = (*it)->box.right();
				prevtop = (*it)->box.top();
				prevbot = (*it)->box.bot();
			}
		}
	}
}

void Terese::on_menuClusterBoxes_activate() {
	Image* img = project->currentImage();
	if (!img) {
		return;
	}
	std::vector<DataPoint*> segments;
	Glib::RefPtr<Gtk::TreeModel> boxlist = treeviewBoxes->get_model();
	for (Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	     rowit != boxlist->children().end(); ++rowit)
	{
		if ((*rowit)[boxColumns.character] == "??") {
			segments.push_back(new DataPoint(Box(rowit, img), 0));
			segments.back()->setFeaturesBoxAppearance();
			segments.back()->rowit = rowit;
		}
	}
	//int dummy = DataPoint::RunDBScan(segments, 0.01, 2);
	int dummy = DataPoint::RunDBScan(segments, 0.01, 2);
	for (std::vector<DataPoint*>::iterator it = segments.begin(); it != segments.end(); ++it) {
		(*((*it)->rowit))[boxColumns.variant] = (*it)->cluster;
	}
}

void Terese::straightenLines() {
	Glib::RefPtr<Gtk::TreeModel> boxlist = treeviewBoxes->get_model();
	Gtk::TreeModel::Children::iterator rowit = boxlist->children().begin();
	while (rowit != boxlist->children().end()) {
		Gtk::TreeModel::Children::iterator lineit = rowit;
		while (rowit != boxlist->children().end() && (*rowit)[boxColumns.character] != "\\n") {
			rowit++;
		}
		const int currentlinemedboxtop = linemedboxtop(lineit, rowit);
		while (lineit != boxlist->children().end() && lineit != rowit) {
			(*lineit)[boxColumns.top] = currentlinemedboxtop;
			lineit++;
		}
		while (rowit != boxlist->children().end() && (*rowit)[boxColumns.character] == "\\n") {
			rowit++;
		}
	}
}

