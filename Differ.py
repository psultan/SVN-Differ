'''
Quickly diff incremental SVN commits.
'''

import sys
import os
from pprint import pprint
import subprocess
import re
import xml.etree.ElementTree as xml
from cStringIO import StringIO

from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools
import pyside2uic

SVN_V  = "1.6.17"
SVN_CL = os.path.join(r"\\Bluearc\GFX\CHARLEX\personal\paul\Apps\svn\svn-win32-{0}\bin\svn.exe".format(SVN_V))
SVN_UI = os.path.join(r"\\Bluearc\GFX\CHARLEX\personal\paul\Apps\svn\TortoiseSVN-{0}\bin".format(SVN_V))

def loadUiType(uiFile):
    """
    Pyside lacks the "loadUiType" command, so we have to convert the ui file to py code in-memory first
    and then execute it in a special frame to retrieve the form_class.
    """
    parsed = xml.parse(uiFile)
    widget_class = parsed.find('widget').get('class')
    form_class = parsed.find('class').text

    with open(uiFile, 'r') as f:
        o = StringIO()
        frame = {}

        pyside2uic.compileUi(f, o, indent=0)
        pyc = compile(o.getvalue(), '<string>', 'exec')
        exec pyc in frame

        #Fetch the base_class and form class based on their type in the xml from designer
        form_class = frame['Ui_%s'%form_class]
        base_class = getattr(QtWidgets, widget_class)
    return form_class, base_class
    
Custom, Base = loadUiType(os.path.join(os.path.dirname(__file__), "Differ.ui"))
class Differ(Custom, Base):
    def __init__(self):
        super(Differ, self).__init__()
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint);
        
        self.processes=[]
        
        self.show()
                      
    def open(self, _file):
        self._file=_file
        
        ext=os.path.splitext(self._file)[-1]
        cmd=[SVN_CL, "log", self._file]
        print cmd
        revisions = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].splitlines()
        revisions=[re.match("r\d+", r).group()[1:] for r in revisions if re.match("r\d+", r)]
        self.a.clear()
        self.b.clear()
        self.a.addItems(revisions)
        self.a.setCurrentIndex(len(revisions)-1)
        self.b.addItems(revisions)
        self.b.setCurrentIndex(len(revisions)-2)
        self.setWindowTitle(self._file)
    
    def merge(self): 
        ext=os.path.splitext(self._file)[-1]
        a=os.path.join(os.environ["tmp"], "a"+ext)
        cmd=[SVN_CL, "cat", "-r%s"%self.a.currentText(), self._file, ">", a]
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0].splitlines()
        
        b=os.path.join(os.environ["tmp"], "b"+ext)
        cmd=[SVN_CL, "cat", "-r%s"%self.b.currentText(), self._file, ">", b]
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0].splitlines()
        
        cmd=" ".join([os.path.join(SVN_UI, "TortoiseMerge.exe"),
             r'/base:"{0}"'.format(a),
             r'/mine:"{0}"'.format(b), 
             r'/basename:"{0} r{1}"'.format(os.path.basename(self._file), self.a.currentText()), 
             r'/minename:"{0} r{1}"'.format(os.path.basename(self._file), self.b.currentText())])
        self.processes.append(subprocess.Popen(cmd))
        
    @QtCore.Slot()
    def on_aPrev_clicked(self):
        self.a.setCurrentIndex(min(self.a.currentIndex()+1, self.a.count()-1))
        self.merge()
    @QtCore.Slot()
    def on_aNext_clicked(self):
        self.a.setCurrentIndex(max(self.a.currentIndex()-1, 0, self.b.currentIndex()+1))
        self.merge()
    @QtCore.Slot()
    def on_bPrev_clicked(self):
        self.b.setCurrentIndex(min(self.b.currentIndex()+1, self.a.count()-1, self.a.currentIndex()-1))
        self.merge()
    @QtCore.Slot()
    def on_bNext_clicked(self):
        self.b.setCurrentIndex(max(self.b.currentIndex()-1, 0))
        self.merge()
    @QtCore.Slot()
    def on_prev_clicked(self):
        if self.a.currentIndex()<self.a.count()-1:
            self.a.setCurrentIndex(min(self.a.currentIndex()+1, self.a.count()-1))
            self.b.setCurrentIndex(min(self.b.currentIndex()+1, self.a.count()-1))
            self.merge()
    @QtCore.Slot()
    def on_next_clicked(self):
        if self.b.currentIndex()>0:
            self.b.setCurrentIndex(max(self.b.currentIndex()-1, 0))
            self.a.setCurrentIndex(max(self.a.currentIndex()-1, 0))
            self.merge()
    @QtCore.Slot()
    def on_diff_clicked(self):
        self.merge()
    @QtCore.Slot()
    def on_a_currentIndexChanged(self):
        if self.b.currentIndex()!=-1 and self.a.currentIndex()!=-1:
            if self.b.currentIndex()>=self.a.currentIndex():
                self.b.setCurrentIndex(self.a.currentIndex()-1)
            if self.a.currentIndex()<=self.b.currentIndex():
                self.a.setCurrentIndex(self.b.currentIndex()+1)
        self.aPrev.setEnabled(True)
        self.bNext.setEnabled(True)
        self.prev.setEnabled(True)
        self.next.setEnabled(True)
        self.bPrev.setEnabled(True)
        self.aNext.setEnabled(True)
        if self.a.currentIndex()==self.a.count()-1:
            self.aPrev.setEnabled(False)
            self.prev.setEnabled(False)
        if self.b.currentIndex()==0:
            self.bNext.setEnabled(False)
            self.next.setEnabled(False)
        if self.b.currentIndex()==self.a.currentIndex()-1:
            self.bPrev.setEnabled(False)
            self.aNext.setEnabled(False)
        self.getLog()
    @QtCore.Slot()
    def on_b_currentIndexChanged(self):
        self.on_a_currentIndexChanged()

    @QtCore.Slot()
    def on_blame_clicked(self):
        cmd=" ".join([os.path.join(SVN_UI, "TortoiseProc.exe"),
             r'/command:blame',
             r'/startrev:{0}'.format(self.a.currentText()), 
             r'/endrev:{0}'.format(self.b.currentText()), 
             r'/path:"{0}"'.format(self._file)])
        self.processes.append(subprocess.Popen(cmd))
    @QtCore.Slot()
    def on_blameAll_clicked(self):
        cmd=" ".join([os.path.join(SVN_UI, "TortoiseProc.exe"),
             r'/command:blame',
             r'/startrev:1', 
             r'/endrev:-1', 
             r'/path:"{0}"'.format(self._file)])
        self.processes.append(subprocess.Popen(cmd))                
        
    def getLog(self):
        if self.a.currentText() and  self.b.currentText():
            cmd=[SVN_CL, "log", "-r{0}:{1}".format(int(self.a.currentText())+1, self.b.currentText()), '"{0}"'.format(self._file)]
            log = subprocess.Popen(" ".join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
            self.log.setText(log)
    
    @QtCore.Slot()
    def on_actionOpen_triggered(self):
        fname = QtWidgets.QFileDialog.getOpenFileName()
        if fname[0]:
            self.open(fname[0])
    
    
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()
    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()
    def dropEvent(self, e):
        if e.mimeData().hasUrls:
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()
            for url in e.mimeData().urls():
                SVN_CL=None
                fname = str(url.toLocalFile())
                self.open(fname)
        else:
            e.ignore()
    
    def closeEvent(self, event):
        for p in self.processes:
            p.kill()
def main():
    app = QtWidgets.QApplication(sys.argv)
    differ = Differ()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()