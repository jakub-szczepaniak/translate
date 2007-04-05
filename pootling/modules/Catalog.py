#!/usr/bin/python
# -*- coding: utf8 -*-
#
# Pootling
# Copyright 2006 WordForge Foundation
#
# Version 0.1 (29 December 2006)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# See the LICENSE file for more details. 
#
# Developed by:
#       Hok Kakada (hokkakada@khmeros.info)
#       Keo Sophon (keosophon@khmeros.info)
#       San Titvirak (titvirak@khmeros.info)
#       Seth Chanratha (sethchanratha@khmeros.info)
#
# This module is working on Catalog Manager of translation files

from PyQt4 import QtCore, QtGui
from pootling.ui.Ui_Catalog import Ui_Catalog
from pootling.modules.CatalogSetting import CatalogSetting
from pootling.modules import tmSetting
from pootling.modules.AboutEditor import AboutEditor
from translate.storage import factory
from Pootle import versioncontrol
import pootling.modules.World as World
from pootling.modules.FindInCatalog import FindInCatalog
from pootling.ui.Ui_tmSetting import Ui_tmsetting
import os

class Catalog(QtGui.QMainWindow):
    """
    The Catalog Manager which holds the toolviews.
    """
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self, parent)
        self.ui = None
    
    def lazyInit(self):
        """
        Initialize only at time of calling Catalog.
        """
        if (self.ui):
            return
        
        self.ui = Ui_Catalog()
        self.ui.setupUi(self)
        self.resize(720,400)
        self.autoRefresh = True
        self.ui.actionStatistics.setEnabled(False)

        self.ui.toolBar.toggleViewAction()
        self.ui.toolBar.setWindowTitle("ToolBar View")
        self.ui.toolBar.setStatusTip("Toggle ToolBar View")
        
        self.folderIcon = QtGui.QIcon("../images/folder.png")
        
        # set up table appearance and behavior
        self.headerLabels = [self.tr("Name"),
                            self.tr("Fuzzy"),
                            self.tr("Untranslated"),
                            self.tr("Total"),
                            self.tr("CVS/SVN Status"),
                            self.tr("Last Revision"),
                            self.tr("Last Translator"),
                            self.tr("Translated")]
        self.ui.treeCatalog.setColumnCount(len(self.headerLabels))
        self.ui.treeCatalog.setHeaderLabels(self.headerLabels)
        self.ui.treeCatalog.header().setResizeMode(QtGui.QHeaderView.Interactive)
        self.ui.treeCatalog.setWhatsThis("The catalog manager merges all files and folders enter one treewidget and displays all po, xlf... files. the way you can easily see if a template has been added or removed. Also some information about the files is displayed.")
        
        # File menu action
        self.connect(self.ui.actionQuit, QtCore.SIGNAL("triggered()"), QtCore.SLOT("close()"))
        self.ui.actionQuit.setWhatsThis("<h3>Quit</h3>Quit Catalog")
        self.ui.actionQuit.setStatusTip("Quit application")

        # Edit menu action
        self.ui.actionReload.setEnabled(True)
        self.connect(self.ui.actionReload, QtCore.SIGNAL("triggered()"), self.refresh)
        self.ui.actionReload.setWhatsThis("<h3>Reload</h3>Set the current files or folders to get the most up-to-date version.")
        self.ui.actionReload.setStatusTip("Reload the current files")

        # create statistics action
        self.connect(self.ui.actionStatistics, QtCore.SIGNAL("triggered()"), self.showStatistic)
        self.ui.actionStatistics.setStatusTip("Show status of files")

        # Catalog setting's checkboxes action.
        self.catSetting = CatalogSetting(self)
        self.connect(self.ui.actionConfigure, QtCore.SIGNAL("triggered()"), self.catSetting.show)
        self.connect(self.ui.actionBuildTM, QtCore.SIGNAL("triggered()"), self.buildTM)
        self.ui.actionConfigure.setWhatsThis("<h3>Configure...</h3>Set the configuration items with your prefered values.")
        self.ui.actionConfigure.setStatusTip("Set the prefered configuration")
        self.connect(self.catSetting.ui.chbname, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chbfuzzy, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chblastrevision, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chbtranslator, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chbuntranslated, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chbtotal, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chbSVN, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)
        self.connect(self.catSetting.ui.chbtranslated, QtCore.SIGNAL("stateChanged(int)"), self.toggleHeaderItem)

        # Create Find String in Catalog
        self.findBar = FindInCatalog(self)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.findBar)
        self.findBar.setHidden(True)

        self.connect(self.ui.actionFind_in_Files, QtCore.SIGNAL("triggered()"), self.findBar.showFind)
        self.ui.actionFind_in_Files.setWhatsThis("<h3>Find</h3>You can find string ever you want in Catalog")
        self.ui.actionFind_in_Files.setStatusTip("Search for a text")
        # emit findfiles signal from FindInCatalog file
        self.connect(self.findBar, QtCore.SIGNAL("initSearch"), self.find)

        # progress bar
        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setEnabled(True)
        self.progressBar.setProperty("value",QtCore.QVariant(0))
        self.progressBar.setOrientation(QtCore.Qt.Horizontal)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setVisible(False)
        self.ui.statusbar.addPermanentWidget(self.progressBar)

        # Help menu of aboutQt
        self.ui.menuHelp.addSeparator()
        action = QtGui.QWhatsThis.createAction(self)
        self.ui.menuHelp.addAction(action)
        self.aboutDialog = AboutEditor(self)
        self.connect(self.ui.actionAbout, QtCore.SIGNAL("triggered()"), self.aboutDialog.showDialog)
        self.connect(self.ui.actionAboutQt, QtCore.SIGNAL("triggered()"), QtGui.qApp, QtCore.SLOT("aboutQt()"))
        
        self.connect(self.catSetting, QtCore.SIGNAL("updateCatalog"), self.updateCatalog)
        self.connect(self.ui.treeCatalog, QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"), self.emitOpenFile)
        self.setupCheckbox()

        self.lastFound = None
        
        # timer..
        self.timer = QtCore.QTimer()
        self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.updateStatistic)
        self.fileItems = []
        self.itemNumber = 0
    
    def find(self, searchString, searchOptions):
            if (not (searchString and searchOptions)):
                return
                
            # start find in the top level..
            for i in range(self.ui.treeCatalog.topLevelItemCount()):
                topItem = self.ui.treeCatalog.topLevelItem(i)
                for j in range(topItem.childCount()):
                      item = topItem.child(j)
                      filename = self.getFilename(item)
                      
                      # continue from resume item
                      if (self.lastFound == None) or (self.lastFound == item):
                      
                      
                          found = self.searchInString(searchString, filename, searchOptions)
                          self.lastFound = item
                          break
                      else:
                          found = False
                
                if found:
                      print "found in", filename, "at position", found
                      self.emit(QtCore.SIGNAL("openFile"), filename)
                      self.emit(QtCore.SIGNAL("goto"), found)
                      break
            else:
                msg = self.tr("' was not found")
                self.lastFound = None
                
                QtGui.QMessageBox.information(self, self.tr("Find"), "'" + str(searchString) + msg + '\n\n' + "Please try again !")
                
##            for i in range(self.ui.treeCatalog.topLevelItemCount()):
##                item = self.ui.treeCatalog.topLevelItem(i)
##                for j in range(item.childCount()):
##                      childItem = item.child(j)
##                      filename = self.getFilename(childItem)
##                      if (self.lastFound != filename):
##                          found = self.searchInString(searchString, filename, searchOptions)
##                          break
##                      else:
##                          found = False
##
##                if found:
##                      print "found in", filename, "at position", found
##                      self.lastFound = filename
##                      self.emit(QtCore.SIGNAL("openFile"), filename)
##                      self.emit(QtCore.SIGNAL("goto"), found)
##                      break
##            else:
##                msg = self.tr("' was not found")
##                QtGui.QMessageBox.information(self, self.tr("Find"), "'" + str(searchString) + msg + '\n\n' + "Please try again !")

    def searchInString(self, searchString, filename, searchOptions):
          found = False
          if (not os.path.isfile(filename)):
              return False
          store = factory.getobject(filename)
          if (not store):
              return False
          unitIndex = 0
          for unit in store.units:
              searchableText = ""
              if (searchOptions == World.source):
                  searchableText = unit.source
              elif (searchOptions == World.target):
                  searchableText = unit.target
              elif (searchOptions == (World.source + World.target)):
                  searchableText = unit.source + unit.target
              if (searchableText.find(searchString) != -1 ):
                  found = unitIndex
                  break
              unitIndex += 1
          return found

    def showStatistic(self):
          # files is empty of tree Catalog
          itemCount = self.ui.treeCatalog.topLevelItemCount()
          if (itemCount == 0):
              return

          item = self.ui.treeCatalog.currentItem()
          filename = self.getFilename(item)
          if os.path.isfile(filename):
              filename = str(filename)
              store = factory.getobject(filename)

              name = os.path.basename(filename)
              fuzzyUnitCount = store.fuzzy_units()
              translatedUnitCount = store.translated_unitcount()
              untranslatedUnitCount = store.untranslated_unitcount()
              totalUnitCount = fuzzyUnitCount + untranslatedUnitCount + translatedUnitCount
              # round down to number ater decimal points (fuzzy)
              fuzzy = str((float(fuzzyUnitCount) / totalUnitCount) * 100)
              fuzzy = float(fuzzy)
              fuzzy = round(fuzzy , 2)
              # round down to number ater decimal points ( translated)
              translated = str((float(translatedUnitCount) / totalUnitCount) * 100)
              translated = float(translated)
              translated = round(translated , 2)
              # round down to number ater decimal points (untranslated)
              untranslated = str((float(untranslatedUnitCount) / totalUnitCount) * 100)
              untranslated = float(untranslated)
              untranslated = round(untranslated , 2)

              QtGui.QMessageBox.information(self, self.tr("Statistic of files"), 'File Name: ' + str(name) + '\n\nFuzzy: ' + str(fuzzyUnitCount) + ' (' + str(fuzzy) + '%)' + '\n\nTranslated: ' + str(translatedUnitCount) + ' (' + str(translated) + '%)' + '\n\nUntranslated: ' + str(untranslatedUnitCount) + ' (' + str(untranslated) + '%)' + '\n\nTotal of strings: ' + str(totalUnitCount), "OK")

          elif os.path.isdir(filename):
                for i in range(item.childCount()):
                    childItem = item.child(i)
                    i += 1
                QtGui.QMessageBox.information(self, self.tr("Statistic of file"), 'Total of files: ' + str(i) , "OK")
          return

    def toggleHeaderItem(self):
        if (isinstance(self.sender(), QtGui.QCheckBox)):
            text = self.sender().text()
            if text in self.headerLabels:
                if (self.sender().isChecked()):
                    self.ui.treeCatalog.showColumn(self.headerLabels.index(text))
                    World.settings.setValue("Catalog." + text, QtCore.QVariant(False))
                else:
                    self.ui.treeCatalog.hideColumn(self.headerLabels.index(text))
                    World.settings.setValue("Catalog." + text, QtCore.QVariant(True))

    def updateProgress(self, value):
        if (not self.progressBar.isVisible()):
            self.progressBar.setVisible(True)
        elif (value == 100):
            self.progressBar.setVisible(False)
        self.progressBar.setValue(value)
        
    def showDialog(self):
        self.lazyInit()
        self.show()
        
        cats = World.settings.value("CatalogPath").toStringList()
        if (cats) and (self.ui.treeCatalog.topLevelItemCount() == 0):
            self.updateCatalog()
    
    def updateCatalog(self):
        """
        Read data from world's "CatalogPath" and display statistic of files
        in tree view.
        """
        self.ui.actionStatistics.setEnabled(True)
        self.ui.treeCatalog.clear()
        cats = World.settings.value("CatalogPath").toStringList()
        includeSub = World.settings.value("diveIntoSubCatalog").toBool()
        
        # TODO: calculate number of maximum files in directory.
        maxFilesNum = 0.1       # avoid devision by zero.
        currentFileNum = 0.0
        
        for catalogFile in cats:
            catalogFile = unicode(catalogFile)
            self.addCatalogFile(catalogFile, includeSub, None)
        
        self.ui.treeCatalog.resizeColumnToContents(0)
        self.timer.start(1000)
        
            #currentFileNum += 1
            #self.updateProgress(int((currentFileNum / maxFilesNum) * 100))
    
    def addCatalogFile(self, path, includeSub, item):
        """
        add path to catalog tree view if it's file, if it's directory then
        dive into it and add files.
        """
        if (os.path.isfile(path)):
            existedItem = self.getExistedItem(os.path.dirname(path))
            if (existedItem):
                item = existedItem
            elif (item == None):
                item = QtGui.QTreeWidgetItem(item)
                self.ui.treeCatalog.addTopLevelItem(item)
                self.ui.treeCatalog.expandItem(item)
                item.setText(0, os.path.dirname(path))
                item.setIcon(0, self.folderIcon)
                
            # if file is already existed in the item's child... skip.
            if (path.endswith(".po") or path.endswith(".pot") or path.endswith(".xlf") or path.endswith(".xliff")) and (not self.ifFileExisted(path, item)):
                childItem = QtGui.QTreeWidgetItem(item)
                childItem.setText(0, os.path.basename(path))
                self.fileItems.append(childItem)
                
##            childStats = self.getStats(path)
##            if (childStats):
##                childItem = QtGui.QTreeWidgetItem(item)
##                childItem.setText(0, childStats[0])
##                childItem.setText(1, childStats[1])
##                childItem.setText(2, childStats[2])
##                childItem.setText(3, childStats[3])
##                childItem.setText(4, childStats[4])
##                childItem.setText(5, childStats[5])
##                childItem.setText(6, childStats[6])
##                childItem.setText(7, childStats[7])
        
        if (os.path.isdir(path)) and (not path.endswith(".svn")):
            existedItem = self.getExistedItem(path)
            if (existedItem):
                # it's already existed, so use the existed one
                childItem = existedItem
            else:
                # it does not exist in tree yet, create new one
                if (item == None):
                    childItem = QtGui.QTreeWidgetItem(item)
                    self.ui.treeCatalog.addTopLevelItem(childItem)
                    self.ui.treeCatalog.expandItem(childItem)
                    childItem.setText(0, path)
                # it's existed in tree but it is the sub directory
                elif hasattr(item, "parent"):
                    childItem = QtGui.QTreeWidgetItem()
                    item.insertChild(0, childItem)
                    childItem.setText(0, os.path.basename(path))
                childItem.setIcon(0, self.folderIcon)
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    path = os.path.join(root + os.path.sep + file)
                    self.addCatalogFile(path, includeSub, childItem)
                    
                # whether dive into subfolder
                if (includeSub):
                    for folder in dirs:
                        path = os.path.join(root + os.path.sep + folder)
                        self.addCatalogFile(path, includeSub, childItem)
                
                break
    
    def getExistedItem(self, path):
        """
        Get existed item in the tree's top level. If the item existed, it returns
        the item, otherwise returns False.
        """
        for i in range(self.ui.treeCatalog.topLevelItemCount()):
            item = self.ui.treeCatalog.topLevelItem(i)
            if (hasattr(item, "text")) and (item.text(0) == path):
                return item
        return False
    
    def ifFileExisted(self, path, item):
        """
        Get existed item in the tree's top level. If the item existed, it returns
        the item, otherwise returns False.
        """
        if (not hasattr(item, "childCount")):
            return False
        for i in range(item.childCount()):
            it = item.child(i)
            if (hasattr(it, "text")) and (it.text(0) == os.path.basename(path)):
                return it
        return False
    
    def getStats(self, filename):
        """
        return stats as list of text of current file name or False if error.
        @param filename: path and file name.
        """
        try:
            store = factory.getobject(filename)
        except:
            return False
        
        if (not os.path.isfile(filename)):
            return False
        
        name = os.path.basename(filename)
        fuzzyUnitCount = store.fuzzy_units()
        translated = store.translated_unitcount()
        untranslatedUnitCount = store.untranslated_unitcount()
        totalUnitCount = fuzzyUnitCount + untranslatedUnitCount + translated
        
        cvsSvn = "?"
        
        if hasattr(store, "parseheader"):
            headerDic = store.parseheader()
            try:
                revisionDate = str(headerDic["PO-Revision-Date"])
            except:
                pass
            try:
                lastTranslator = str(headerDic["Last-Translator"])
            except:
                pass
        else:
            revisionDate = ""
            lastTranslator = ""
        
        return [name, str(fuzzyUnitCount), str(untranslatedUnitCount), str(totalUnitCount), cvsSvn, revisionDate, lastTranslator, str(translated)]

    def setupCheckbox(self):
        if not (World.settings.value("Catalog.Name").toBool()):
            self.catSetting.ui.chbname.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbname.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.Fuzzy").toBool()):
            self.catSetting.ui.chbfuzzy.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbfuzzy.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.Untranslated").toBool()):
            self.catSetting.ui.chbuntranslated.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbuntranslated.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.Total").toBool()):
            self.catSetting.ui.chbtotal.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbtotal.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.CVS/SVN Status").toBool()):
            self.catSetting.ui.chbSVN.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbSVN.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.Last Revision").toBool()):
            self.catSetting.ui.chblastrevision.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chblastrevision.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.Last Translator").toBool()):
            self.catSetting.ui.chbtranslator.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbtranslator.setCheckState(QtCore.Qt.Checked)
        
        if not (World.settings.value("Catalog.Translated").toBool()):
            self.catSetting.ui.chbtranslated.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.catSetting.ui.chbtranslated.setCheckState(QtCore.Qt.Checked)

    def emitOpenFile(self, item, col):
        """
        Send "openFile" signal with filename.
        """
        filename = self.getFilename(item)
        if (os.path.isfile(filename)): 
            self.emit(QtCore.SIGNAL("openFile"), filename)
    
    def getFilename(self, item):
        """
        return filename join from item.text(0) to its parent.
        """
        filename = unicode(item.text(0))
        if (item.parent()):
            filename = os.path.join(self.getFilename(item.parent()) + os.path.sep + filename)
        return filename
    
    def refresh(self):
        self.settings = QtCore.QSettings()
        if self.autoRefresh:
            self.updateCatalog()
        else:
            self.settings.sync()

    def buildTM(self):
        """Build Translation Memory"""
        cats = self.ui.treeCatalog.topLevelItem(0)
        if cats:
            catalogPath = cats.text(0)
            self.tmSetting = tmSetting.tmSetting(None)
            self.tmSetting.showDialog()
            self.tmSetting.addLocation(catalogPath)
            self.tmSetting.createTM()
        else:
            return
    
    def updateStatistic(self):
        item = self.fileItems[self.itemNumber]
        path = self.getFilename(item)
        childStats = self.getStats(path)
        
        if (childStats):
            item.setText(1, childStats[1])
            item.setText(2, childStats[2])
            item.setText(3, childStats[3])
            item.setText(4, childStats[4])
            item.setText(5, childStats[5])
            item.setText(6, childStats[6])
            item.setText(7, childStats[7])
        
        self.itemNumber += 1
        if (self.itemNumber == len(self.fileItems)):
            self.timer.stop()
    

##if __name__ == "__main__":
##    import sys, os
##    app = QtGui.QApplication(sys.argv)
##    catalog = Catalog(None)
##    catalog.showDialog()
##    sys.exit(catalog.exec_())
