
'''
Data model for a review session: proposals, reviewers, topics, and analyses
'''

import datetime
from lxml import etree
import os, sys
import history
from PyQt4 import QtCore
import StringIO
import traceback

import analyses
import email_template
import prop_mvc_data
import resources
import revu_mvc_data
import settings
import topics
import xml_utility

UI_FILE = 'main_window.ui'
AGUP_MASTER_ROOT_TAG = 'AGUP_Review_Session'
AGUP_XML_SCHEMA_FILE = resources.resource_file('agup_review_session.xsd')
AGUP_MASTER_VERSION = '1.0'


class AGUP_Data(QtCore.QObject):
    '''
    Complete data for a PRP review session
    '''

    def __init__(self, config = None):
        QtCore.QObject.__init__(self)

        self.settings = config or settings.ApplicationQSettings()
        self.clearAllData()
        self.modified = False
    
    def clearAllData(self):
        '''
        clear all data (except for self.settings)
        '''
        self.analyses = None            # TODO: remove this
        self.proposals = prop_mvc_data.AGUP_Proposals_List()
        self.reviewers = revu_mvc_data.AGUP_Reviewers_List()
        self.topics = topics.Topics()
        self.email = email_template.EmailTemplate()
    
    def openPrpFile(self, filename):
        '''
        '''
        if not os.path.exists(filename):
            history.addLog('PRP File not found: ' + filename)
            return False
        self.clearAllData()
        filename = str(filename)
        self.importTopics(filename)
        self.importReviewers(filename)
        self.importProposals(filename)
        self.importAnalyses(filename)
        self.importEmailTemplate(filename)
        self.modified = False

        return True
    
    def write(self, filename):
        '''
        write this data to an XML file
        '''
        if self.topics is None: return
        if self.proposals is None: return
        if self.reviewers is None: return

        doc = etree.parse( StringIO.StringIO('<' + AGUP_MASTER_ROOT_TAG + '/>') )

        root = doc.getroot()
        root.attrib['cycle'] = self.proposals.cycle
        root.attrib['version'] = AGUP_MASTER_VERSION
        root.attrib['time'] = str(datetime.datetime.now())
        
        self.topics.writeXml(root, False)
        self.reviewers.writeXmlNode(root)
        self.proposals.writeXmlNode(root)

        # provide this data in a second place, in case imported proposals destroy the original
        node = etree.SubElement(root, 'Assignments')
        if self.analyses is not None:
            self.analyses.writeXmlNode(node)
        
        self.email.writeXmlNode(root)

        s = etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        open(filename, 'w').write(s)

    def importAnalyses(self, xmlFile):
        '''
        read analyses, assignments, & assessments from XML file

        apply decision tree:
          if no topics are known
             define new topics names and set values
          else 
             match all topics lists
             only if successful matches all around, set values
        
        simple test if topics are defined for first proposal since others MUST match
        '''
        if self.proposals is None:
            history.addLog('Must define or import proposals before analyses')
            return
        if self.reviewers is None:
            history.addLog('Must define or import reviewers before analyses')
            return

        assignments = analyses.AGUP_Analyses()
        try:
            assignments.importXml(xmlFile)
        except Exception:
            history.addLog(traceback.format_exc())
            return

        self.analyses = assignments
        self.reassignAssignmentsToProposals()
    
    def importProposals(self, xmlFile):
        '''
        import a Proposals XML file as generated by the APS
        '''
        props = prop_mvc_data.AGUP_Proposals_List()
        props.importXml(xmlFile)

        if False:       # old code
            cycle = self.settings.getReviewCycle()
            if cycle in (None, '', props.cycle) or props.cycle in ('',):
                props.addTopics(self.topics.getTopicList())
                self.proposals = props
                self.settings.setReviewCycle(props.cycle or '')
                self.reassignAssignmentsToProposals()      # restore any existing assignments
                # TODO: update self.analyses
                pass
            else:
                msg = 'Cannot import proposals from cycle "' + props.cycle
                msg += '" into PRP session for cycle "' + cycle + '"'
                raise KeyError, msg

        _review_cycle_settings = self.settings.getReviewCycle()
        _review_cycle_proposals = props.cycle or _review_cycle_settings
        if _review_cycle_settings in (None, '', _review_cycle_proposals):
            self.proposals = props
            self.settings.setReviewCycle(_review_cycle_proposals or '')
        else:
            msg = 'Cannot import proposals from cycle "' + _review_cycle_proposals
            msg += '" into PRP session for cycle "' + _review_cycle_settings + '"'
            raise KeyError, msg
    
    def importReviewers(self, xmlFile):
        '''
        import a complete set of reviewers (usually from a previous review cycle's file)
        
        Completely replace the set of reviewers currently in place.
        '''
        rvwrs = revu_mvc_data.AGUP_Reviewers_List()
        rvwrs.importXml(xmlFile)        # pass exceptions straight to the caller 
        
        if self.topics is None or len(self.topics) == 0:
            for reviewer in rvwrs:
                self.topics.addTopics(reviewer.getTopicList())
                break   # got what we need now

        self.reviewers = rvwrs
    
    def importTopics(self, xmlFile):
        '''
        import a complete set of Topics (usually from a previous PRP Project file)
         
        Completely replace the set of Topics currently in place.
        '''
        topics_obj = topics.Topics()
        topics_obj.importXml(xmlFile, False)        # pass exceptions straight to the caller
 
        self.topics = topics_obj
    
    def importEmailTemplate(self, xmlFile):
        '''
        import the email template support
        '''
        self.email.importXml(xmlFile)        # pass exceptions straight to the caller
    
    def reassignAssignmentsToProposals(self):
        '''
        merge assignments with self.proposals and self.reviewers
        '''
#         raise Exception, 'this code is still being developed and is not assigning topic values now'
        # the problem: Topics have zero values for all proposals on the standard test file now
        # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        if self.analyses is None:
            return
        for prop_id, analysis in self.analyses.analyses.items():
            proposal = self.proposals.getProposal(prop_id)      # raises exception if not found
            for topic in analysis.topics:
                value = analysis.getTopic(topic)
                proposal.topics.set(topic, value)     # topic must exist
        
            # TODO: check that 
            #   assigned reviewers in proposal object 
            #   match with proposal analysis finding
    
    def getCycle(self):
        '''the review cycle, as defined by the proposals'''
        if self.proposals is None:
            return ''
        return self.proposals.cycle


def dev_test2():
    agup = AGUP_Data()
    agup.openPrpFile('project/agup_project.xml')
    print agup


if __name__ == '__main__':
#     developer_testing_of_this_module()
    dev_test2()
