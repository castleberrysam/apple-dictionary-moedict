#!/usr/bin/env python3

import sys
import csv
import xml.etree.ElementTree as xml
import re

TOCFL_LEVELS = ['Novice', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2']

class DictEntry:
    def __init__(self, id: str, title: str,
                 pronIdx: int, twZhuyin: str, twPinyin: str,
                 defs: str):
        self.id = id
        self.title = title
        self.pronIdx = pronIdx[:-1]
        self.twZhuyin = twZhuyin
        self.twPinyin = twPinyin
        self.defs = defs
    def toXML(self, id: str, hskList: dict[str,int], tocflList: dict[str,int], tradSimpTable) -> xml.Element:
        # unique id and title (headword)
        entry = xml.Element('d:entry', id=id)
        entry.set('d:title', self.title)
        # index (used for dict searching)
        index = xml.SubElement(entry, 'd:index')
        index.set('d:value', self.title)
        if self.twZhuyin:
            twZhuyinIndex = xml.SubElement(entry, 'd:index')
            twZhuyinIndex.set('d:value', self.twZhuyin)
        if self.twPinyin:
            twPinyinIndex = xml.SubElement(entry, 'd:index')
            twPinyinIndex.set('d:value', self.twPinyin)
        # display headword, pronounciations, HSK level, TOCFL level
        titleDiv = xml.SubElement(entry, 'div')
        titleText = xml.SubElement(titleDiv, 'h1')
        titleText.set('class', 'headword')
        titleText.text = self.title
        pronSpan = xml.SubElement(titleDiv, 'span')
        pronSpan.set('class', 'syntax')
        for pronLabel,pronValue in [('TW_ZY',self.twZhuyin),
                                    ('TW_PY',self.twPinyin)]:
            if pronValue:
                pronItem = xml.SubElement(pronSpan, 'span')
                pronItem.text = f'| {pronValue} |'
                pronItem.set('d:pr', pronLabel)
        titleSimp = self.title.translate(tradSimpTable)
        if titleSimp in hskList:
            hskLevelSpan = xml.SubElement(titleDiv, 'span')
            hskLevelSpan.set('class', 'syntax')
            hskLevelSpan.text = 'HSK-' + str(hskList[titleSimp])
        if self.title in tocflList:
            tocflLevelSpan = xml.SubElement(titleDiv, 'span')
            tocflLevelSpan.set('class', 'syntax')
            tocflLevelSpan.text = 'TOCFL-' + TOCFL_LEVELS[tocflList[self.title]-1]
        # convert definition string into structured XML
        # there may be multiple sections delimited by headers of the form [...] (e.g. "[名]")
        # then within each section there may be a numbered list
        defsDiv = xml.SubElement(entry, 'div')
        defsLines = self.defs.splitlines(True)
        curList = None
        curListLen = None
        curP = None
        for line in defsLines:
            # check for new section
            m = re.match(r'\[([^\]]+)\]$', line.strip())
            if m:
                xml.SubElement(defsDiv, 'h2').text = m[1]
                curList = None
                curListLen = None
                if curP is not None and curP.text[-1] == '\n':
                    curP.text = curP.text[:-1]
                curP = None
                continue
            # check for numbered list item
            m = re.match(r'([1-9][0-9]*)\. *(.*)', line.strip())
            if m:
                listIndex = int(m[1])
                if curList is None:
                    curList = xml.SubElement(defsDiv, 'ol')
                    curListLen = 0
                curListLen += 1
                if listIndex != curListLen:
                    print("Warning: bad numbering in numbered list: " + self.title)
                xml.SubElement(curList, 'li').text = m[2]
                if curP is not None and curP.text[-1] == '\n':
                    curP.text = curP.text[:-1]
                curP = None
                continue
            # treat as normal text
            if curP is None:
                curP = xml.SubElement(defsDiv, 'p')
            if curP.text:
                curP.text += line
            else:
                curP.text = line
            curList = None
            curListLen = None
        return entry

class DictCsvParser:
    FIELD_NAMES = {
        'id': '字詞號',
        'title': '字詞名',
        'pronIdx': '多音排序',
        'twZhuyin': '注音一式',
        'twPinyin': '漢語拼音',
        'defs': '釋義'
    }
    def __init__(self, csvFilename: str, hskListFilename: str, tocflListFilename: str, tradSimpListFilename: str):
        self.csvFilename = csvFilename
        self.hskListFilename = hskListFilename
        self.tocflListFilename = tocflListFilename
        self.tradSimpListFilename = tradSimpListFilename
        # open dict csv and locate needed columns based on names
        self.csvHandle = open(csvFilename, newline='')
        self.csvReader = csv.reader(self.csvHandle)
        columnNames = next(self.csvReader)
        self.fieldIndices = {}
        for fieldName,columnName in self.FIELD_NAMES.items():
            self.fieldIndices[fieldName] = columnNames.index(columnName)
        # parse HSK list
        self.hskListHandle = open(hskListFilename, newline='')
        self.hskListReader = csv.reader(self.hskListHandle)
        self.hskList = {}
        next(self.hskListReader) # skip column names
        for row in self.hskListReader:
            if row[1] in self.hskList:
                continue
            self.hskList[row[1]] = int(row[0])
        # parse TOCFL list
        self.tocflListHandle = open(tocflListFilename, newline='')
        self.tocflListReader = csv.reader(self.tocflListHandle)
        self.tocflList = {}
        next(self.tocflListReader) # skip column names
        for row in self.tocflListReader:
            if row[0] in self.tocflList:
                continue
            self.tocflList[row[0]] = int(row[3])
        # parse traditional -> simplified translation list
        tradSimpTable = {}
        with open(tradSimpListFilename, newline='') as tradSimpListHandle:
            for line in tradSimpListHandle:
                fields = line.split()
                # there may be multiple potential simplified characters
                # but we'll just pick the first one, good enough for this application
                tradChar = fields[0]
                simpChar = fields[1]
                tradSimpTable[tradChar] = simpChar
        self.tradSimpTable = str.maketrans(tradSimpTable)
        # setup xml document
        self.xmlRoot = xml.Element('d:dictionary', xmlns='http://www.w3.org/1999/xhtml')
        self.xmlRoot.set('xmlns:d', 'http://www.apple.com/DTDs/DictionaryService-1.0.rng')
    def parseRow(self, csvRow: str) -> DictEntry:
        fieldValues = {}
        for fieldName,fieldIndex in self.fieldIndices.items():
            fieldValues[fieldName] = csvRow[fieldIndex]
        return DictEntry(**fieldValues)
    def parse(self):
        rowId = 0
        for row in self.csvReader:
            self.xmlRoot.append(self.parseRow(row).toXML(str(rowId), self.hskList, self.tocflList, self.tradSimpTable))
            rowId += 1
    def write(self, xmlFilename: str):
        tree = xml.ElementTree(self.xmlRoot)
        xml.indent(tree)
        tree.write(xmlFilename, encoding='UTF-8', xml_declaration=True)

if __name__ == "__main__":
    csvParser = DictCsvParser('dict.csv', 'HSK-2015.csv', 'tocfl.csv', 'TSCharacters.txt')
    csvParser.parse()
    csvParser.write('RevisedDict.xml')
