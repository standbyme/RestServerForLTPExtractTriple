#!/usr/bin/env python
# coding=utf-8
"""
文本中事实三元组抽取
import LTPExtractTriple
MODELDIR = "ltp-data-v3.3.1/ltp_data/"
LTPExtractTripleInstance = LTPExtractTriple(MODELDIR)
result = LTPExtractTripleInstance.pack(["中共中央政治局12月8日下午就实施国家大数据战略进行第二次集体学习。","我们应该审时度势、精心谋划、超前布局、力争主动，深入了解大数据发展现状和趋势及其对经济社会发展的影响"])
"""

import traceback
import os
import sys
import re
import tempfile
from pyltp import Segmentor, Postagger, Parser, NamedEntityRecognizer

__author__ = "tianwen jiang"

# Set your own model path


class LTPExtractTriple:
    def __init__(self,MODELDIR):
        self.MODELDIR = MODELDIR

        print "正在加载LTP模型... ..."

        self.segmentor = Segmentor()
        self.segmentor.load(os.path.join(self.MODELDIR, "cws.model"))
        self.postagger = Postagger()
        self.postagger.load(os.path.join(self.MODELDIR, "pos.model"))
        self.parser = Parser()
        self.parser.load(os.path.join(self.MODELDIR, "parser.model"))
        self.recognizer = NamedEntityRecognizer()
        self.recognizer.load(os.path.join(self.MODELDIR, "ner.model"))

        print "加载模型完毕。"

        out_dir = tempfile.mkdtemp()

        self.inaf_file_name = os.path.join(out_dir, "inputaf.txt")
        self.out_file_name = os.path.join(out_dir, "output_jiang.txt")

        self.begin_line = 1
        self.end_line = 0

    def extraction_start(self,in_file_name, out_file_name, begin_line, end_line):
        """
        事实三元组抽取的总控程序
        Args:
            in_file_name: 输入文件的名称
            #out_file_name: 输出文件的名称
            begin_line: 读文件的起始行
            end_line: 读文件的结束行
        """
        in_file = open(in_file_name, 'r')
        out_file = open(out_file_name, 'w')
        total = 0
        type1 = 0
        type2 = 0
        type3 = 0
        type4 = 0
        line_index = 1
        sentence_number = 0
        text_line = in_file.readline()
        while text_line:
            if line_index < begin_line:
                text_line = in_file.readline()
                line_index += 1
                continue
            if end_line != 0 and line_index > end_line:
                break
            sentence = text_line.strip()
            if sentence == "" or len(sentence) > 1000:
                text_line = in_file.readline()
                line_index += 1
                continue
            try:
                flag, t1, t2, t3, t4 = self.fact_triple_extract(sentence, out_file)
                total += flag
                type1 += t1
                type2 += t2
                type3 += t3
                type4 += t4
            except:
                pass
            sentence_number += 1
            if sentence_number % 50 == 0:
                print "%d done" % (sentence_number)
            text_line = in_file.readline()
            line_index += 1
        in_file.close()
        out_file.close()

        print "总共有" + str(line_index - 1) + "句"
        return total, type1, type2, type3, type4


    def fact_triple_extract(self,sentence, out_file):
        total = 0
        type1 = 0
        type2 = 0
        type3 = 0
        type4 = 0
        """
        对于给定的句子进行事实三元组抽取
        Args:
            sentence: 要处理的语句
        """
        # print sentence
        words = self.segmentor.segment(sentence)
        # print "word is "
        wordsStr = "\t".join(words)
        # print wordsStr
        postags = self.postagger.postag(words)
        netags = self.recognizer.recognize(words, postags)
        # print "netags is "
        netagsStr = "\t".join(netags)
        # print netagsStr
        arcs = self.parser.parse(words, postags)
        # print "arc.head:arc.relation is "
        arcsStr = "\t".join("%d:%s" % (arc.head, arc.relation) for arc in arcs)
        # print arcsStr

        NE_list = set()
        for i in range(len(netags)):
            # netags is vectorOfString
            # S是一个名词
            # B表示开始
            if netags[i][0] == 'S' or netags[i][0] == 'B':
                j = i
                if netags[j][0] == 'B':
                    while netags[j][0] != 'E':
                        j += 1
                    e = ''.join(words[i:j + 1])
                    NE_list.add(e)
                else:
                    e = words[j]
                    NE_list.add(e)

        # 至此名词全部收集在NE_list
        child_dict_list = self.build_parse_child_dict(words, postags, arcs)

        # print "postags is"
        postagsStr = "\t".join(postags)
        # print postagsStr

        for index in range(len(postags)):
            # 抽取以谓词为中心的事实三元组
            if postags[index] == 'v':
                child_dict = child_dict_list[index]
                # 主谓宾
                if child_dict.has_key('SBV') and child_dict.has_key('VOB'):
                    e1 = self.complete_e(words, postags, child_dict_list,
                                    child_dict['SBV'][0])
                    r = words[index]
                    e2 = self.complete_e(words, postags, child_dict_list,
                                    child_dict['VOB'][0])
                    # if e1 in NE_list or e2 in NE_list:
                    if self.is_good(e1, NE_list, sentence) and self.is_good(e2, NE_list, sentence):
                        out_file.write("主语谓语宾语关系\t(%s,%s,%s)\t%s\t%s\n" %
                                       (e1, r, e2, sentence, 0))
                        out_file.flush()

                        type1 += 1
                        total += 1
                # 定语后置，动宾关系
                if arcs[index].relation == 'ATT':
                    if child_dict.has_key('VOB'):
                        e1 = self.complete_e(
                            words, postags, child_dict_list, arcs[index].head - 1)
                        r = words[index]
                        e2 = self.complete_e(
                            words, postags, child_dict_list, child_dict['VOB'][0])
                        temp_string = r + e2
                        if temp_string == e1[:len(temp_string)]:
                            e1 = e1[len(temp_string):]
                        # if temp_string not in e1 and (e1 in NE_list or e2 in NE_list):
                        if temp_string not in e1 and self.is_good(e1, NE_list, sentence) and self.is_good(e2, NE_list, sentence):
                            out_file.write("定语后置动宾关系\t(%s,%s,%s)\t%s\t%s\n" % (
                                e1, r, e2, sentence, 0))
                            out_file.flush()
                            type2 += 1
                            total += 1
                # 含有介宾关系的主谓动补关系
                if child_dict.has_key('SBV') and child_dict.has_key('CMP'):
                    # e1 = words[child_dict['SBV'][0]]
                    e1 = self.complete_e(words, postags, child_dict_list,
                                    child_dict['SBV'][0])
                    cmp_index = child_dict['CMP'][0]
                    r = words[index] + words[cmp_index]
                    if child_dict_list[cmp_index].has_key('POB'):
                        e2 = self.complete_e(words, postags, child_dict_list,
                                        child_dict_list[cmp_index]['POB'][0])
                        # if e1 in NE_list or e2 in NE_list:
                        if self.is_good(e1, NE_list, sentence) and self.is_good(e2, NE_list, sentence):
                            out_file.write("介宾关系主谓动补\t(%s,%s,%s)\t%s\t%s\n" % (
                                e1, r, e2, sentence, 0))
                            out_file.flush()
                            type3 += 1
                            total += 1

            # 尝试抽取命名实体有关的三元组
            if netags[index][0] == 'S' or netags[index][0] == 'B':
                ni = index
                if netags[ni][0] == 'B':
                    while ni < len(netags) and netags[ni][0] != 'E':
                        ni += 1
                    e1 = ''.join(words[index:ni + 1])
                else:
                    e1 = words[ni]
                if ni >= len(netags):
                    continue

                # ni是最后一个命名实体的下标
                if arcs[ni].relation == 'ATT' and postags[arcs[ni].head - 1] == 'n' and netags[arcs[ni].head - 1] == 'O':
                    r = self.complete_e(words, postags, child_dict_list,
                                   arcs[ni].head - 1)
                    if e1 in r:
                        r = r[(r.index(e1) + len(e1)):]
                    if arcs[arcs[ni].head - 1].relation == 'ATT' and netags[arcs[arcs[ni].head - 1].head - 1] != 'O':
                        e2 = self.complete_e(words, postags, child_dict_list,
                                        arcs[arcs[ni].head - 1].head - 1)
                        mi = arcs[arcs[ni].head - 1].head - 1
                        li = mi
                        if netags[mi][0] == 'B':
                            while netags[mi][0] != 'E':
                                mi += 1
                            e = ''.join(words[li + 1:mi + 1])
                            e2 += e
                        if r in e2:
                            e2 = e2[(e2.index(r) + len(r)):]
                        if self.is_good(e1, NE_list, sentence) and self.is_good(e2, NE_list, sentence):
                            out_file.write(
                                "(人名/地名/机构,职务/关系,命名实体)\t(%s,%s,%s)\t%s\t%s\n" % (e1, r, e2, sentence, 1))
                            out_file.flush()
                            type4 += 1
                            total += 1
        return total, type1, type2, type3, type4


    def build_parse_child_dict(self,words, postags, arcs):
        """
        为句子中的每个词语维护一个保存句法依存儿子节点的字典
        Args:
            words: 分词列表
            postags: 词性列表
            arcs: 句法依存列表
        """
        child_dict_list = []
        for index in range(len(words)):
            child_dict = dict()
            for arc_index in range(len(arcs)):
                if arcs[arc_index].head == index + 1:
                    if child_dict.has_key(arcs[arc_index].relation):
                        child_dict[arcs[arc_index].relation].append(arc_index)
                    else:
                        child_dict[arcs[arc_index].relation] = []
                        child_dict[arcs[arc_index].relation].append(arc_index)
            # if child_dict.has_key('SBV'):
            #    print words[index],child_dict['SBV']
            child_dict_list.append(child_dict)
        return child_dict_list


    def complete_e(self,words, postags, child_dict_list, word_index):
        """
        完善识别的部分实体
        """
        # 美国，总统，奥巴马 word_index对应总统
        # 台湾 属于 中国 word_index对应台湾与中国
        child_dict = child_dict_list[word_index]
        prefix = ''
        if child_dict.has_key('ATT'):
            for i in range(len(child_dict['ATT'])):
                prefix += self.complete_e(words, postags,
                                     child_dict_list, child_dict['ATT'][i])

                # todo
                # 中国驻俄罗斯大使，想办法改一改
        postfix = ''
        if postags[word_index] == 'v':
            if child_dict.has_key('VOB'):
                postfix += self.complete_e(words, postags,
                                      child_dict_list, child_dict['VOB'][0])
            if child_dict.has_key('SBV'):
                prefix = self.complete_e(words, postags, child_dict_list,
                                    child_dict['SBV'][0]) + prefix

        return prefix + words[word_index] + postfix


    def is_good(self,e, NE_list, sentence):
        """
        判断e是否为命名实体
        """
        if e not in sentence:
            return False

        words_e = self.segmentor.segment(e)
        postags_e = self.postagger.postag(words_e)
        if e in NE_list:
            return True
        else:
            NE_count = 0
            for i in range(len(words_e)):
                if words_e[i] in NE_list:
                    NE_count += 1
                if postags_e[i] == 'v':
                    return False
            if NE_count >= len(words_e) - NE_count:
                return True
        return False


    def process_sentence(self,raw_str):
        x = raw_str.replace('，', '\n').replace(',', '\n')
        x = x.replace('。', '\n').replace('.', '\n')
        x = x.replace('\t', '')
        x = x.replace('[', '')
        x = x.replace(']', '')
        x = x.replace(';', '')
        x = x.replace('；', '')
        x = x.replace('　', '').replace(' ', '')
        x = re.sub(r'\n+', "\n", x)

        return x


    def handleInput(self,raw_str_list):
        with open(self.inaf_file_name, 'w') as outFile:
            for x in raw_str_list:
                x = self.process_sentence(x)
                if x != '\n':
                    outFile.write(x)





    def handleOutFileStr(self,s):
        temp = s.split('\t')
        SentenceStructure = temp[0]
        HeadEntity, Relation, TailEntity = temp[1].lstrip(
            '(').rstrip(')').split(',')
        SSID = temp[3]
        return {"Triple":{"HeadEntity": HeadEntity, "Relation": Relation, "TailEntity": TailEntity}, "SentenceStructure": SentenceStructure,"SSID":SSID}


    def pack(self,raw_str_list):
        self.handleInput(raw_str_list)
        self.extraction_start(self.inaf_file_name, self.out_file_name, self.begin_line, self.end_line)
        with open(self.out_file_name) as inFile:
            fileStrs = inFile.readlines()
        return list(map(self.handleOutFileStr, fileStrs))