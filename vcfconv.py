#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Convert vcf to ldif
"""
import argparse
import base64
import quopri


def get_line(f):
    """Get logically line which separated physically

    Arguments:
        f -- file object

    Returns:
        Yield logically line
    """
    chain_next = False      # QUOTED-PRINTABLE
    chain_now = False       # chain flag
    chain_previous = False  # BASE64
    chain_stop = False      # BASE64

    chanks = []
    for chank in f:
        chank = chank.replace('\n', '').replace('\r', '')
        chain_next = False
        if chank.endswith('='):
            chank = chank[:-1]
            chain_next = True

        chain_previous = False
        if chank.startswith(' '):
            chank = chank[1:]
            chain_previous = True

        chain_stop = False
        if chank is '':
            chain_stop = True

        if chanks and not chain_now and not chain_previous:
            line = ''.join(chanks)
            chanks = []
            yield line

        if chain_next:
            # chain next
            chanks.append(chank)
            chain_now = True
            continue

        if chain_previous:
            # start chain
            chanks.append(chank)
            chain_now = True
            continue

        if chain_stop:
            # stop chain
            line = ''.join(chanks)
            chanks = []
            chain_now = False
            yield line
            continue

        if chanks and chain_now is True:
            # no more chain next
            chanks.append(chank)
            line = ''.join(chanks)
            chanks = []
            chain_now = False
            yield line
            continue

        if chanks:
            # no chain
            line = ''.join(chanks)
            chanks = []
            yield line

        chanks.append(chank)
        continue

    if chanks:
        # no chain
        line = ''.join(chanks)
        chanks = []
        yield line


def parse_tag(tag):
    """parse vCard tag

    Arguments:
        tag -- vCard tag

    Returns:
        Return tag dictonary.
    """
    head = {}
    for (idx, name) in enumerate(tag.split(';')):
        if idx == 0:
            head['name'] = name
            continue
        if '=' in name:
            (tag, val) = name.split('=', maxsplit=1)
            head[tag] = val
            continue
        if 'TYPE' not in head:
            head['TYPE'] = []
        head['TYPE'].append(name)
    return head


def parse_line(line):
    """parse vCard line

    Arguments:
        line  -- vCard line

    Returns:
        Return tuple (tag dictonaly, value).
    """
    (tag, value) = line.split(':', maxsplit=1)
    head = parse_tag(tag)

    if 'ENCODING' in head:
        if head['ENCODING'] == 'QUOTED-PRINTABLE':
            value = quopri.decodestring(value)
        elif head['ENCODING'] == 'BASE64':
            value = base64.b64decode(value)
    if 'CHARSET' in head:
        enc = head['CHARSET']
        value = value.decode(enc)
    return (head, value)


def parse_entry(lines):
    """Make entry from vCard lines

    Arguments:
        lines -- vCard lines

    Returns:
        Yield entry object.
    """
    entry = {'mail': []}
    for line in lines:
        t = line.split(':', maxsplit=1)
        if len(t) != 2:
            continue

        # analyze line
        (head, value) = parse_line(line)
        name = head['name']

        # givenName
        # sn
        if name == 'N':
            (val1, val2, dummy) = value.split(';', maxsplit=2)
            if val1:
                entry['sn'] = val1
            if val2:
                entry['givenName'] = val2
            continue
        # cn
        if name == 'FN':
            entry['cn'] = value
            continue
        # mail
        if name == 'EMAIL':
            entry['mail'].append(value)
            continue
        # description
        if name == 'NOTE':
            entry['description'] = value
            continue
        # tel
        if name == 'TEL':
            if 'CELL'in head['TYPE']:
                entry['mobile'] = value
                continue
            elif 'HOME' in head['TYPE']:
                entry['homePhone'] = value
                continue
            elif 'WORK' in head['TYPE']:
                entry['telephoneNumber'] = value
                continue
            else:
                entry['homePhone'] = value
                continue

        if name == 'ADR':
            if 'HOME' in head['TYPE']:
                entry['homePostalAddress'] = value.replace(';', ' ').strip()
                continue
            elif 'WORK' in head['TYPE']:
                entry['mozillaWorkStreet2'] = value.replace(';', ' ').strip()
                continue
            else:
                entry['homePostalAddress'] = value.replace(';', ' ').strip()
                continue

    return entry


def split_entry(fobj):
    """Read entry and return ldif object

    Arguments:
        fobj -- vcf file object

    Returns:
        Yield vCard entry
    """
    flag = False
    lines = []
    for line in get_line(fobj):
        if 'BEGIN:VCARD' in line:
            flag = True
            lines = []
        if flag:
            lines.append(line)
        if 'END:VCARD' in line:
            flag = False
            yield parse_entry(lines)


def dump_person(entry, base_path):
    """Dump person

    Arguments:
        entry     -- entry
        base_path -- ldap base path

    Returns:
        Nothing.
    """
    lines = []
    for mail in entry['mail']:
        lines.append(f'dn: mail={mail},{base_path}')
        lines.append('objectclass: top')
        lines.append('objectclass: person')
        lines.append('objectclass: organizationalPerson')
        lines.append('objectclass: inetOrgPerson')
        lines.append('objectclass: mozillaAbPersonAlpha')
        lines.append(f'mail: {mail}')
        for tag in ['givenName', 'sn', 'cn',
                    'mobile', 'homePhone', 'telephoneNumber',
                    'homePostalAddress', 'mozillaWorkStreet2']:
            if tag in entry:
                lines.append(f'{tag}: {entry[tag]}')
        lines.append('')
    print('\n'.join(lines))


def convert(fobj, base_path=''):
    """Convert vCard to ldif

    Arguments:
        fobj      -- vcf file object
        base_path -- ldap base path

    Returns:
        Nothing.
    """
    for person in split_entry(fobj):
        if len(person['mail']) > 0:
            dump_person(person, base_path)


def main():
    """Main routine

    Parse arguments and call subroutine
    """
    parser = argparse.ArgumentParser(
        description='Convert Thunderbird address ldif to your LDAP ldif,'
                    ' or the reverse.')
    parser.add_argument('-b',
                        metavar='BASE_PATH',
                        dest='base_path',
                        default='',
                        help='ldap base path')
    parser.add_argument('-f',
                        metavar='FILE',
                        dest='fname',
                        type=argparse.FileType(),
                        required=True,
                        help='VCF file')

    args = parser.parse_args()
    convert(args.fname, args.base_path)


if __name__ == '__main__':
    main()
