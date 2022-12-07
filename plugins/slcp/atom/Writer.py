import logging
import os
import os.path
import urllib.request, urllib.parse, urllib.error
import json

from edge.writer.solrtemplateresponsewriter import SolrTemplateResponseWriter
from edge.opensearch.solrtemplateresponse import SolrTemplateResponse

class Writer(SolrTemplateResponseWriter):
    def __init__(self, configFilePath):
        super(Writer, self).__init__(configFilePath)

        templatePath = os.path.dirname(configFilePath) + os.sep
        templatePath += self._configuration.get('service', 'template')
        self.template = self._readTemplate(templatePath)

    def _generateOpenSearchResponse(self, solrResponse, searchText, searchUrl, searchParams, pretty):
        response = SolrTemplateResponse(self._configuration, searchUrl, searchParams)
        response.setTemplate(self.template)
        response.variables['serviceUrl'] = self._configuration.get('service', 'url')

        return response.generate(solrResponse, pretty=pretty)

    def _constructSolrQuery(self, startIndex, entriesPerPage, parameters, facets):
        sortKeys = json.loads(self._configuration.get('solr', 'sortKeys'))

        queries = []
        filterQueries = []
        sort = None
        sortDir = 'asc'
        start = '*'
        end = '*'

        for key, value in parameters.items():
            if value != "":
                if key == 'keyword':
                    queries.append(urllib.parse.quote(value))
                elif key == 'startTime':
                    start = value
                elif key == 'endTime':
                    end = value
                elif key == 'bbox':
                    coordinates = value.split(",")
                    filterQueries.append('Spatial-Geometry:[' + coordinates[1] + ',' + coordinates[0] + '%20TO%20' + coordinates[3] + ',' + coordinates[2] + ']')
                elif key == 'concept_id':
                    queries.append('concept-id:' + self._urlEncodeSolrQueryValue(value))
                elif key == 'sortKey':
                    if value in list(sortKeys.keys()):
                        sort = sortKeys[value]
                elif key == 'sortDir':
                    sortDir = value
                elif key == 'inDAT':
                    filterQueries.append('InDAT:%s' % value)
        queries.append('(BeginningEndingDateTime:['+start+'%20TO%20' + end + ']+OR+(*:*%20NOT%20BeginningEndingDateTime:*))')

        for key, value in facets.items():
            if type(value) is list:
                if (len(value) == 1):
                    filterQueries.append(key + ':' + self._urlEncodeSolrQueryValue(value[0]))
                else:
                    filterQueries.append(key + ':(' + '+OR+'.join([ self._urlEncodeSolrQueryValue(x) for x in value ]) + ")")
            else:    
                filterQueries.append(key + ':' + self._urlEncodeSolrQueryValue(value))

        if len(queries) == 0:
            queries.append('*:*')

        query = 'q='+'+AND+'.join(queries)+'&version=2.2&indent=on&wt=json'

        if len(filterQueries) > 0:
            query += '&fq='+'+AND+'.join(filterQueries)
        
        if self.facet:
            query += '&rows=0&facet=true&facet.limit=-1&facet.mincount=1&'
            query += '&'.join(['facet.field=' + facet for facet in list(self.facetDefs.values())])
        else:
            query += '&start='+str(startIndex)+'&rows='+str(entriesPerPage)
            if sort is not None:
                query += '&sort=' + urllib.parse.quote(sort + ' ' + sortDir + ",InternalVersion desc")
            else:
                query += '&sort=' + urllib.parse.quote("score desc,InternalVersion desc")

        logging.debug('solr query: '+query)

        return query
