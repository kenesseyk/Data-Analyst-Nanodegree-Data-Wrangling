# -*- coding: utf-8 -*-
"""
Created on Mon Jan 22 13:56:11 2018

@author: kinga
"""

import re
import lxml.etree as ET
import pprint as pp

osm_file = 'budapest_inner.osm'

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
expected_street_types = set()
street_names = {}
unexpected_street_names = set()

# Check if street names are in the defined expected street types
def is_valid_street_name(street_name):
    match  = re.match('.*\s(.*)$', street_name)
    if match:
        street_type = match.group(1)
        return street_type in expected_street_types
    else:
        return False

# Check if postal codes are in the expected 1xxx format
unexpected_postcodes = {}
def is_valid_postcode(postcode):
    expected_format = '1([0-2][0-9])[0-9]'
    match = re.match(expected_format, postcode)
    if match:
        inner_digits = int(match.group(1))
        if inner_digits <= 23:
            return True
    return False

# Check e-mail addresses
unexpected_emails = []
def is_valid_email(email):
    email_format = '[0-9, a-z, ., -]+@[0-9, a-z, ., -]+\.[a-z]{2,5}'
    match = re.match(email_format, email.lower())
    return bool(match)

# Check if phone numbers are in the expected format: +36 1 xxx xxxx or +36 xx xxx xxxx
odd_phone_numbers = []
def is_valid_format(phone_number):
    pref_format = '\+36\s[1-9]0?\s[0-9]{3}\s[0-9]{4}$'
    match = re.match(pref_format, phone_number)
    return bool(match)

# Count tags and attributes
tag_attributes = {}
def count_tags(tag, attributes):
    if tag not in tag_attributes:
        tag_attributes[tag] = {}
        tag_attributes[tag]['attributes'] = {}
        tag_attributes[tag]['count'] = 0

    tag_attributes[tag]['count'] += 1

    for attrib in attributes:
        if attrib not in tag_attributes[tag]['attributes']:
            tag_attributes[tag]['attributes'][attrib] = 0

        tag_attributes[tag]['attributes'][attrib] += 1

# Check for <tag> elements in <way> and <node> elements and validate them based on course examples
def audit():
    for event, elem in ET.iterparse(osm_file, events=('start',)):
        tag = elem.tag
        attributes = elem.attrib

        count_tags(tag, attributes)

        for tag in elem.iter('tag'):
            if tag.attrib['k'] == 'phone':
                phone_number = tag.attrib['v']

                if not is_valid_format(phone_number):
                    odd_phone_numbers.append(phone_number)

            if tag.attrib['k'] == 'email':
                email = tag.attrib['v']

                if not is_valid_email(email):
                    unexpected_emails.append(email)

            if tag.attrib['k'] == 'addr:street':
                street = tag.attrib['v']

                if not is_valid_street_name(street):
                    unexpected_street_names.add(street)

                if street not in street_names:
                    street_names[street] = 0
                street_names[street] += 1

            if tag.attrib['k'] == 'addr:postcode':
                postcode = tag.attrib['v']

                if not is_valid_postcode(postcode):
                    if postcode not in unexpected_postcodes:
                        unexpected_postcodes[postcode] = {'count': 0}
                    unexpected_postcodes[postcode]['count'] += 1

                    # Get the parent element's child tag with k = addr:street attribute and extract the value
                    try:
                        street_address = [item.attrib['v'] for item in elem.getchildren() if item.tag == 'tag' and item.attrib['k'] == 'addr:street'][0]
                    except IndexError:
                        # No addr:street tags on parent, skip
                        pass
                    else:
                        unexpected_postcodes[postcode]

# Use the hungarian_public_places_list for comparison
if __name__ == '__main__':
    with open('hungarian_public_places.txt', 'r') as file:
        for line in file:
            match = re.match('(.*)\:.*', line)
            expected_street_types.add(match.group(1))

    audit()

# Print out the results of the audit
print('\nTAG AND ATTRIBUTE COUNTS:\n')
pp.pprint(tag_attributes)

print('\nNUMBER OF STREET NAMES: {}'.format(len(street_names)))

for street_names in unexpected_street_names:
    print street_names

print('\nNUMBER OF UNEXPECTED STREET NAMES: {}'.format(len(unexpected_street_names)))

print('\nUNEXPECTED POSTCODES:\n')
pp.pprint(unexpected_postcodes)

print('\nUNEXPECTED EMAIL ADDRESSES:\n')
pp.pprint(unexpected_emails)

print('\nNUMBER OF UNEXPECTEDLY FORMATTED PHONE NUMBERS: {}'.format(len(odd_phone_numbers)))
#print('\nODD PHONE NUMBERS:\n')
#pp.pprint(odd_phone_numbers)



