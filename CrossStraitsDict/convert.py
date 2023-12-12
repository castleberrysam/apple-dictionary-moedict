#!/usr/bin/env python3

import csv
import xml.etree.ElementTree as xml
import re

class DictEntry:
    def __init__(self, id: str, titleTrad: str, titleSimp: str,
                 pronIdx: int, specialWord: str, specialPron: str,
                 twZhuyin: str, twPinyin: str, cnZhuyin: str, cnPinyin: str,
                 defs: list[str]):
        self.id = id
        self.titleTrad = titleTrad or titleSimp
        self.titleSimp = titleSimp or titleTrad
        self.pronIdx = pronIdx[:-1]
        self.specialWord = specialWord
        self.specialPron = specialPron
        self.twZhuyin = twZhuyin or cnZhuyin
        self.twPinyin = twPinyin or cnPinyin
        self.cnZhuyin = cnZhuyin or twZhuyin
        self.cnPinyin = cnPinyin or twPinyin
        self.defs = defs
    def toXML(self, id: str) -> xml.Element:
        # unique id and title (headword)
        entry = xml.Element('d:entry', id=id)
        entry.set('d:title', self.titleTrad)
        # index (used for dict searching)
        tradIndex = xml.SubElement(entry, 'd:index')
        tradIndex.set('d:value', self.titleTrad)
        if self.titleSimp and self.titleSimp != self.titleTrad:
            simpIndex = xml.SubElement(entry, 'd:index')
            simpIndex.set('d:value', self.titleSimp)
        if self.twZhuyin:
            twZhuyinIndex = xml.SubElement(entry, 'd:index')
            twZhuyinIndex.set('d:value', self.twZhuyin)
        if self.twPinyin:
            twPinyinIndex = xml.SubElement(entry, 'd:index')
            twPinyinIndex.set('d:value', self.twPinyin)
        if self.cnZhuyin and self.cnZhuyin != self.twZhuyin:
            cnZhuyinIndex = xml.SubElement(entry, 'd:index')
            cnZhuyinIndex.set('d:value', self.cnZhuyin)
        if self.cnPinyin and self.cnPinyin != self.twPinyin:
            cnPinyinIndex = xml.SubElement(entry, 'd:index')
            cnPinyinIndex.set('d:value', self.cnPinyin)
        # display headword
        titleDiv = xml.SubElement(entry, 'div')
        titleText = xml.SubElement(titleDiv, 'h1')
        titleText.text = self.titleTrad
        # display pronounciations
        pronSpan = xml.SubElement(entry, 'span')
        pronSpan.set('class', 'syntax')
        for pronLabel,pronValue in [('TW_ZY',self.twZhuyin),
                                    ('TW_PY',self.twPinyin),
                                    ('CN_ZY',self.cnZhuyin),
                                    ('CN_PY',self.cnPinyin)]:
            if pronValue:
                pronItem = xml.SubElement(pronSpan, 'span')
                pronItem.text = f'| {pronValue} |'
                pronItem.set('d:pr', pronLabel)
        # display definitions
        defsDiv = xml.SubElement(entry, 'div')
        defsList = xml.SubElement(defsDiv, 'ol')
        for definition in self.defs:
            defsItem = xml.SubElement(defsList, 'li')
            defsItem.text = definition
        return entry

class DictCsvParser:
    FIELD_NAMES = {
        'id': '字詞流水序',
        'titleTrad': '正體字形',
        'titleSimp': '簡化字形',
        'pronIdx': '音序',
        'specialWord': '臺／陸特有詞',
        'specialPron': '臺／陸特有音',
        'twZhuyin': '臺灣音讀',
        'twPinyin': '臺灣漢拼',
        'cnZhuyin': '大陸音讀',
        'cnPinyin': '大陸漢拼',
        'defsStart': '釋義１'
    }
    def __init__(self, csvFilename: str):
        self.csvFilename = csvFilename
        self.csvHandle = open(csvFilename, newline='')
        self.csvReader = csv.reader(self.csvHandle)
        columnNames = next(self.csvReader)
        self.fieldIndices = {}
        for fieldName,columnName in self.FIELD_NAMES.items():
            self.fieldIndices[fieldName] = columnNames.index(columnName)
        self.xmlRoot = xml.Element('d:dictionary', xmlns='http://www.w3.org/1999/xhtml')
        self.xmlRoot.set('xmlns:d', 'http://www.apple.com/DTDs/DictionaryService-1.0.rng')
    def parseRow(self, csvRow: str) -> DictEntry:
        fieldValues = {}
        # defs require special processing due to being a variable-length list
        for fieldName,fieldIndex in self.fieldIndices.items():
            if fieldName == 'defsStart':
                continue
            fieldValues[fieldName] = csvRow[fieldIndex]
        defs = []
        for index in range(self.fieldIndices['defsStart'], len(csvRow)):
            if csvRow[index] == '':
                break
            defStr = csvRow[index]
            # remove leading numbers (html <ol> will provide this)
            m = re.match(r'[0-9]+\. *(.*)', defStr)
            if m:
                defStr = m[1]
            defs.append(defStr)
        fieldValues['defs'] = defs
        return DictEntry(**fieldValues)
    def parse(self):
        rowId = 0
        for row in self.csvReader:
            self.xmlRoot.append(self.parseRow(row).toXML(str(rowId)))
            rowId += 1
    def write(self, xmlFilename: str):
        tree = xml.ElementTree(self.xmlRoot)
        xml.indent(tree)
        tree.write(xmlFilename, encoding='UTF-8', xml_declaration=True)

if __name__ == "__main__":
    csvParser = DictCsvParser('兩岸詞典.csv')
    csvParser.parse()
    csvParser.write('CrossStraitsDict.xml')
