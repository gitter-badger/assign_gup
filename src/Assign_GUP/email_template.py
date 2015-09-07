
'''
Create email notices to each Reviewer describing specific assignments
'''

# TODO: needs an associated MVC editor

from lxml import etree
import os

import agup_data
import plainTextEdit
import resources
import xml_utility


DEFAULT_PROJECT_FILE = os.path.abspath('project/agup_project.xml')
DEFAULT_TEMPLATE_FILE = os.path.abspath('resources/email_template.txt')
DEFAULT_TEMPLATE_FIELDS = dict(
    # these are example values
    PANEL_CHAIR = 'Pete Jemian',
    REVIEW_CYCLE = '2015-2',
    PRP_DATE = '2015-03-24',
    OTHER_COMMENTS = '''
    This time there are two project proposals:
       GUP-11111 at 5-ID
       GUP-22222 at 12ID
       
       We've discussed the responsibilities for reviewing project proposals.
       If you have any questions, call or write me.

    This is no PUP to review this cycle.
    ''',
)
REVIEWER_FIELDS = dict(     # to be filled with data from an instance of Reviewer
    FULL_NAME = 'Ima Reviewer',
    EMAIL = 'reviewer@institution.net',
    ASSIGNED_PRIMARY_PROPOSALS = '11111 22222 33333',
    ASSIGNED_SECONDARY_PROPOSALS = '44444 55555 66666',
)



class EmailTemplate(object):
    '''
    Support the creation of custom emails to each Reviewer from template and fields
    
    It is possible to create and use custom fields.
    Be sure that the custom fields are *uniquely identifiable* to avoid replacing the wrong text.
    '''
    
    def __init__(self):
        filename = resources.resource_file(DEFAULT_TEMPLATE_FILE)
        self.email_template = open(filename).read()
        self.keyword_dict = DEFAULT_TEMPLATE_FIELDS
    
    def mass_merge(self, reviewers, **kw):
        '''
        create emails for all Reviewers, return as a dictionary by sort_name
        
        :param obj reviewers: instance of revu_mvc_data.AGUP_Reviewers_List
        '''
        book = {}
        for rvwr in reviewers:
            sort_name = rvwr.getSortName()
            fields = {}
            fields['FULL_NAME'] = rvwr.getFullName()
            fields['EMAIL'] = rvwr.getEmail()
            fields['ASSIGNED_PRIMARY_PROPOSALS'] = 'list of primaries'      # TODO:
            fields['ASSIGNED_SECONDARY_PROPOSALS'] = 'list of secondaries'  # TODO:
            fields.update(kw)       # any other substitutions
            book[sort_name] = self.mail_merge(**fields)
        return book
    
    def mail_merge(self, **kw_dict):
        '''
        create one email with a mail merge of self.keyword_dict and kw_dict into self.email_template
        
        suggest defining at least these four keywords, to be applied for each reviewer 
        during mail merge step (values filled in programmatically)::

            FULL_NAME = 'Ima Reviewer',
            EMAIL = 'reviewer@institution.net',
            ASSIGNED_PRIMARY_PROPOSALS = '11111 22222 33333',
            ASSIGNED_SECONDARY_PROPOSALS = '44444 55555 66666',
        
        '''
        kw = self.keyword_dict.copy()   # start with this keyword dictionary
        kw.update(kw_dict)              # add/replace with supplied kw_dict
        email = self.email_template     # grab the current template
        for k, v in kw.items():
            email = email.replace(k, v)
        return email

    def importXml(self, filename):
        '''
        :param str filename: name of XML file with email template and keywords
        '''
        doc = xml_utility.readValidXmlDoc(filename, 
                                          agup_data.AGUP_MASTER_ROOT_TAG, 
                                          agup_data.AGUP_XML_SCHEMA_FILE
                                          )

        root = doc.getroot()
        email_node = root.find('notification_email')
        if email_node is not None:
            text = xml_utility.getXmlText(email_node, 'email_template')
            self.email_template = text or self.email_template
            self.keyword_dict = {}
            for node in email_node.findall('Key'):
                k = node.attrib['name']
                v = node.text.strip()
                self.keyword_dict[k] = v
    
    def writeXmlNode(self, root_node):
        '''
        write email template data to the XML document

        :param obj root_node: XML node to contain this data
        '''
        node = etree.SubElement(root_node, 'notification_email')
        etree.SubElement(node, 'email_template').text = self.email_template
        for k, v in self.keyword_dict.items():
            key_node = etree.SubElement(node, 'Key')
            key_node.attrib['name'] = k
            key_node.text = v.strip()


class EmailTextEdit(plainTextEdit.TextWindow):
    '''
    plainTextEdit window that can remember its geometry, based on title
    '''

    def __init__(self, title, text, settings, parent=None):
        plainTextEdit.TextWindow.__init__(self, title, text, parent)
        self.settings = settings
        self.restoreWindowGeometry()
    
    def settingsGroupName(self):
        '''
        need a group name in the settings file to save the window geometry, based on window title
        '''
        group = str(self.windowTitle()).strip()
        #group = group.lstrip('email: ')
        pattern_list = [' ', ':', ';', '(', ')', '[', ']', '.', ',', "'", '"']
        for pattern in pattern_list:
            group = group.replace(pattern, '_')
        return group

    def closeEvent(self, event):
        self.saveWindowGeometry()
        event.accept()
        self.close()
    
    def saveWindowGeometry(self):
        '''
        remember where the window was
        '''
        if self.settings is not None:
            group = self.settingsGroupName()
            self.settings.saveWindowGeometry(self, group)

    def restoreWindowGeometry(self):
        '''
        put the window back where it was
        '''
        if self.settings is not None:
            group = self.settingsGroupName()
            self.settings.restoreWindowGeometry(self, group)


if __name__ == '__main__':
    et = EmailTemplate()
    print et.mail_merge(**REVIEWER_FIELDS)
    