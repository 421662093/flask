#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, KEYWORD
from whoosh.analysis import Tokenizer, Token,KeywordAnalyzer
from whoosh import qparser
from jieba.analyse import ChineseAnalyzer

import pymongo

analyzer = ChineseAnalyzer()


class WhooshExpert(object):

    def __init__(self):
        """
        Instantiate the whoosh schema and writer and create/open the index.
        """
        self.users_collection = pymongo.Connection().fullteck.users
        #self.webpages_collection = pymongo.Connection().fullteck.webpages_col
        self.indexdir = "index"
        self.indexname = "users"
        self.schema = self.get_schema()
        if not os.path.exists(self.indexdir):
            os.mkdir(self.indexdir)
            create_in(self.indexdir, self.schema, indexname=self.indexname)
        # create an index obj and buffered writer
        self.ix = open_dir(self.indexdir, indexname=self.indexname)

    def get_schema(self):
        return Schema(
            eid=ID(unique=True, stored=True),
            #url=ID(unique=True, stored=True),
            name=TEXT(analyzer=analyzer),#([\u4e00-\u9fa5])|(\w+(\.?\w+)*)
            job=TEXT(analyzer=analyzer),
            label=KEYWORD(commas=True, scorable=True)#lowercase=True, 
            #note=TEXT(analyzer=analyzer),
            #content=TEXT(stored=True, analyzer=analyzer)
        )

    def rebuild_index(self):
        ix = create_in(self.indexdir, self.schema, indexname=self.indexname)
        writer = ix.writer()
        for expert in self.users_collection.find(timeout=False):
            #webpage = self.webpages_collection.find_one({'_id': expert['webpage']})
            #if webpage:
            writer.update_document(
                eid=unicode(expert['_id']),
                #url=expert['url'],
                name=expert['n'],
                label=expert['l'],
                job=expert['j']
                #content=webpage['content']
            )
        writer.commit()

    def commit(self, writer):
        """
        Commit the data to index.
        """
        writer.commit()
        return True

    def update(self, expert, writer=None):#, webpage
        if writer is None:
            writer = self.ix.writer()
        writer.update_document(
            eid=unicode(expert['_id']),
            #url=expert['url'],
            name=expert['n'],
            label=expert['l'],
            job=expert['j'],
            #content=webpage['content']
        )
        writer.commit()

    def parse_query(self, query):
        #parser = qparser.MultifieldParser(
        #    ["url", "title", "tags", "note", "content"], self.ix.schema)
        parser = qparser.MultifieldParser(
            ["name", "job","label"], self.ix.schema)
        return parser.parse(query)

    def search(self, query, page):
        """
        Search the index and return the results list to be processed further.
        """
        PAGE_SIZE=10
        results = []
        with self.ix.searcher() as searcher:
            result_page = searcher.search_page(
                self.parse_query(query), page, pagelen=PAGE_SIZE)
            # create a results list from the search results
            for result in result_page:
            # for result in searcher.search(self.parse_query(query)):
                results.append(dict(result))
        return {'results': results, 'total': result_page.total}

    def delele_by_eid(self, eid):
        writer = self.ix.writer()
        result = writer.delete_by_term('_id', eid)
        writer.commit()
        return result

    def close(self):
        """
        Closes the searcher obj. Must be done manually.
        """
        self.ix.close()