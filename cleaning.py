# -*- coding: utf-8 -*-
"""
Created on Tue Jan 23 10:54:24 2018

@author: kinga
"""

import re
import lxml.etree as ET
import csv
import codecs
import pprint
import schema

OSM_FILE = "budapest_inner.osm"

# Clean street names
def clean_streetname(streetname):
    if streetname in ['Fény', 'Dohány']:
        new_streetname = streetname + ' utca'
    elif streetname == 'Victor Hugo utcaa':
        new_streetname = 'Victor Hugo utca'
    elif streetname == 'Nádor Utca':
        new_streetname = 'Nádor utca'
    elif streetname == 'Magyar Jakobinusok tere':
        new_streetname = 'Magyar jakobinusok tere'
    elif streetname == 'Vigadó Square':
        new_streetname = 'Vigadó tér'
    elif streetname == 'Apaczai Csere Janos utca 4':
        new_streetname = 'Apáczai Csere János utca'
    elif streetname == 'Városmajor utca 5. fsz. 3.':
        new_streetname = 'Városmajor utca'
    elif streetname == 'Táncsics Mihály utca 5':
        new_streetname = 'Táncsics Mihály utca'
    elif streetname == 'Váci út 1-3.':
        new_streetname = 'Váci út'
    else:
        new_streetname = streetname
    return new_streetname

# Clean postal codes
def clean_postcode(postcode):
    postcode_string = str(postcode)
    if postcode_string == '95':
        return '1024'
    else:
        return int(postcode)

# Clean e-mail
def clean_email(email):
    if email in ['mailto:andi@corvindance.hu']:
        email == email.replace('andi@corvindance.hu')
        return email
    else:
        return email

# Clean phone numbers to +36 1 xxx xxxx or +36 xx xxx xxxx format
def clean_phone_numbers(phone_number):
    preferred_format = '\+36\s[1-9]0?\s[0-9]{3}\s[0-9]{4}$'
    match = re.match(preferred_format, phone_number)
    # Return if the phone number is in preferred pattern
    if bool(match):
        return phone_number
    # Remove special characters and whitespaces
    stripped = re.sub('[/()-]', '', phone_number).replace(' ', '')
    # Replace the country code with the expected format
    replaced = re.sub('^0036|^06|^006|^036', '+36', stripped)
    # Insert country code
    if replaced[:3] != '+36' and re.match('^[0-9]{8,9}$', replaced):
        replaced = '+36' + replaced
    # Budapest and non-budapest phones or mobiles
    if len(replaced) == 11 and replaced[:3] == '+36' and replaced[3:4] == '1':
        formatted = replaced[:3] + ' ' + replaced[3:4] + ' ' + replaced[4:7] + ' ' + replaced[7:]
    elif len(replaced) == 12 and replaced[:3] == '+36':
        formatted = replaced[:3] + ' ' + replaced[3:5] + ' ' + replaced[5:8] + ' ' + replaced[8:]
    # If it doesn't fit into any categories above log the error
    else:
        return phone_number
    return formatted


# validate the XML OSM file using the provided schema                     
def validator(filename, schema):
    xmlschema_doc = ET.parse(schema)
    xmlschema = ET.XMLSchema(xmlschema_doc)
    for event, element in ET.iterparse(filename, events=("end", )):
        if not xmlschema.validate(element):
            print xmlschema.error_log

# Make sure the fields order in the csvs matches the column order in the SQL table schema
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the SQL table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']



def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    # Clean and shape node or way XML element to Python dict
    node_attribs = {} 
    way_attribs = {}
    way_nodes = []
    tags = []

    if element.tag == 'node':
        for i in NODE_FIELDS:
            node_attribs[i] = element.attrib[i]
        for tag in element.iter("tag"):  
            problem = PROBLEMCHARS.search(tag.attrib['k'])
            if not problem:
                node_tag = {} 
                node_tag['id'] = element.attrib['id'] 
                node_tag['value'] = tag.attrib['v']  

                match = LOWER_COLON.search(tag.attrib['k'])
                if not match:
                    node_tag['type'] = 'regular'
                    node_tag['key'] = tag.attrib['k']
                else:
                    bef_colon = re.findall('^(.+):', tag.attrib['k'])
                    aft_colon = re.findall('^[a-z|_]+:(.+)', tag.attrib['k'])
                    node_tag['type'] = bef_colon[0]
                    node_tag['key'] = aft_colon[0]
                    if node_tag['type'] == "addr" and node_tag['key'] == "street":
                        # update street name
                        node_tag['value'] = clean_streetname(tag.attrib['v']) 
                    elif node_tag['type'] == "addr" and node_tag['key'] == "postcode":
                        # update post code
                        node_tag['value'] = clean_postcode(tag.attrib['v']) 
            tags.append(node_tag)
        
        return {'node': node_attribs, 'node_tags': tags}
    
    elif element.tag == 'way':
        for i in WAY_FIELDS:
            way_attribs[i] = element.attrib[i]
        for tag in element.iter("tag"):
            problem = PROBLEMCHARS.search(tag.attrib['k'])
            if not problem:
                way_tag = {}
                way_tag['id'] = element.attrib['id'] 
                way_tag['value'] = tag.attrib['v']
                match = LOWER_COLON.search(tag.attrib['k'])
                if not match:
                    way_tag['type'] = 'regular'
                    way_tag['key'] = tag.attrib['k']
                else:
                    bef_colon = re.findall('^(.+?):+[a-z]', tag.attrib['k'])
                    aft_colon = re.findall('^[a-z|_]+:(.+)', tag.attrib['k'])

                    way_tag['type'] = bef_colon[0]
                    way_tag['key'] = aft_colon[0]
                    if way_tag['type'] == "addr" and way_tag['key'] == "street":
                        way_tag['value'] = clean_streetname(tag.attrib['v']) 
                    elif way_tag['type'] == "addr" and way_tag['key'] == "postcode":
                        way_tag['value'] = clean_postcode(tag.attrib['v']) 
            tags.append(way_tag)
        position = 0
        for tag in element.iter("nd"):  
            nd = {}
            nd['id'] = element.attrib['id'] 
            nd['node_id'] = tag.attrib['ref'] 
            nd['position'] = position  
            position += 1
            
            way_nodes.append(nd)
    
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}



# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    # Yield element if it is the right type of tag

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    # Raise ValidationError if element does not match schema
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    # Extend csv.DictWriter to handle Unicode input

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    # Iteratively process each XML element and write to csv(s)

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()



        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    process_map(OSM_FILE, validate=False)
